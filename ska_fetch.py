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

    parser.add_argument('--interpolate-dt',
                        type=float,
                        help='Interpolate to uniform time steps (secs, default=None)')

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


def msidset_interpolate(msidset, dt):
    """
    Interpolate the ``msidset`` in-place to a common time basis, starting at
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


if __name__ == '__main__':
    opt = get_opt()

    stop = DateTime(opt.stop)
    start = stop - 30 if opt.start is None else DateTime(opt.start)

    print('Fetching data for MSIDS={} from {} to {}'.format(opt.msids, start.date, stop.date))

    fetch.set_units(opt.unit_system)
    dat = fetch.MSIDset(opt.msids, start, stop, stat=opt.sampling,
                        filter_bad=(opt.interpolate_dt is None))

    if opt.interpolate_dt:
        print('Interpolating at {} second intervals'.format(opt.interpolate_dt))
        msidset_interpolate(dat, opt.interpolate_dt)

    if opt.remove_events:
        event_names = opt.remove_events.split(',')
        print('Removing events: {}'.format(event_names))
        queryset = get_queryset(event_names, opt.event_pad)
        for msid in dat:
            dat[msid].remove_intervals(queryset)

    if opt.select_events:
        event_names = opt.remove_events.split(',')
        print('Selecting events: {}'.format(event_names))
        queryset = get_queryset(event_names, opt.event_pad)
        for msid in dat:
            dat[msid].select_intervals(queryset)

    print('Writing data to {}'.format(opt.outfile))
    dat.write_zip(opt.outfile)
