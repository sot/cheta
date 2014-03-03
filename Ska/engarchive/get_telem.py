#!/usr/bin/env python
"""
Fetch data from the Ska engineering archive

Some documentation and examples here:

Examples
========

  ska_fetch.py --remove-events=manvrs --unit-system=sci TEPHIN AOPCADMD

"""

from __future__ import print_function, division

import argparse

import numpy as np

from Chandra.Time import DateTime
from Ska.engarchive import fetch


def msidset_regrid(msidset, dt):
    """
    Regrid the ``msidset`` in-place to a common time basis, starting at
    ``msidset.tstart`` and stepping by ``dt``.  This assumes an unfiltered MSIDset, and
    returns a filtered MSIDset.
    """
    tstart = (msidset.tstart // dt) * dt
    times = np.arange((msidset.tstop - tstart) // dt) * dt + tstart
    msidset.interpolate(times=times, filter_bad=False)
    common_bads = np.zeros(len(msidset.times), dtype=bool)
    for msid in msidset.values():
        if msid.bads is not None:  # 5min and daily stats have no bad values
            common_bads |= msid.bads

    # Apply the common bads array and filter out these bad values
    for msid in msidset.values():
        msid.bads = common_bads
        msid.filter_bad()
    msidset.times = msidset.times[~common_bads]


def get_queryset(event_names, event_pad):
    from kadi import events

    for event_name in event_names:
        event_queryset = getattr(events, event_name)
        if event_pad is not None:
            event_queryset.interval_pad = event_pad

        try:
            queryset = queryset | event_queryset
        except NameError:
            queryset = event_queryset

    return queryset


def get_telem(msids, start=None, stop=None, sampling=None, unit_system='eng',
              regrid_dt=None, remove_events=None, select_events=None, event_pad=0,
              outfile=None):

    stop = DateTime(stop)
    start = stop - 30 if start is None else DateTime(start)

    print('Fetching data for MSIDS={} from {} to {}'.format(msids, start.date, stop.date))

    fetch.set_units(unit_system)

    # If fetching more than 30 days of data make sure that the projected dataset
    # size is reasonable.  Pre-fetch a 3-day interval and scale.
    fetch_Mb, regrid_Mb = get_fetch_size(msids, start, stop, stat=None, regrid_dt=None, fast=True)
    if sampling is None and stop - start > 30:
        dat = fetch.MSIDset(msids, start, start + 3, )

    dat = fetch.MSIDset(msids, start, stop, stat=sampling,
                        filter_bad=(regrid_dt is None))

    if regrid_dt:
        print('Interpolating at {} second intervals'.format(regrid_dt))
        msidset_regrid(dat, regrid_dt)

    if remove_events:
        event_names = remove_events.split(',')
        print('Removing events: {}'.format(event_names))
        queryset = get_queryset(event_names, event_pad)
        for msid in dat:
            dat[msid].remove_intervals(queryset)

    if select_events:
        event_names = remove_events.split(',')
        print('Selecting events: {}'.format(event_names))
        queryset = get_queryset(event_names, event_pad)
        for msid in dat:
            dat[msid].select_intervals(queryset)

    if outfile is not None:
        print('Writing data to {}'.format(outfile))
        dat.write_zip(outfile)


def get_opt():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--start',
                        type=str,
                        help='Start time for data fetch (default=<stop> - 30 days)')

    parser.add_argument('--stop',
                        type=str,
                        help='Stop time for data fetch (default=NOW)')

    parser.add_argument('--sampling',
                        type=str,
                        default='5min',
                        help='Data sampling (all | 5min | daily) (default=5min)')

    parser.add_argument('--outfile',
                        default='fetch.zip',
                        type=str,
                        help='Output file name (default=fetch.zip)')

    parser.add_argument('--unit-system',
                        type=str,
                        default='eng',
                        help='Unit system for data (eng | sci | cxc) (default=eng)')

    parser.add_argument('--regrid-dt',
                        type=float,
                        help='Regrid to uniform time steps (secs, default=None)')

    parser.add_argument('--remove-events',
                        type=str,
                        help='Remove kadi events (comma-separated list, default=None)')

    parser.add_argument('--select-events',
                        type=str,
                        help='Select kadi events (comma-separated list, default=None)')

    parser.add_argument('--event-pad',
                        type=float,
                        help='Additional pad time around events (secs, default=None)')

    parser.add_argument('msids',
                        metavar='MSID',
                        type=str,
                        nargs='+',
                        help='MSID to fetch')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    opt = get_opt()

    dat = get_telem(**var(opt))
