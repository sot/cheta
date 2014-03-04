"""
Fetch telemetry from the Ska engineering archive.  This bundles many of the common steps
of data retrieval into one routine which can be accessed either through the command line
or as a single function ``get_telem()``.

Some documentation and examples here:

Examples
========

  % ska_fetch --remove-events=manvrs --unit-system=sci TEPHIN AOPCADMD

"""

from __future__ import print_function, division

import argparse

import numpy as np

from Chandra.Time import DateTime
from . import fetch, utils


def msidset_resample(msidset, dt):
    """
    Resample the ``msidset`` in-place to a common time basis, starting at
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


def _get_telem(msids, start=None, stop=None, sampling='all', unit_system='eng',
               resample_dt=None, remove_events=None, select_events=None, event_pad=0,
               outfile=None, quiet=False, max_fetch_Mb=None, max_resample_Mb=None):
    """
    High-level routine to get telemetry for one or more MSIDs and perform
    common post-processing functions.

    This is a non-public version that really does the work.  The public interface
    is fetch.get_telem(), which is a thin wrapper for this.  (Trying to factor code
    out to separate modules and keep import times donw).

    :param msids: MSID(s) to fetch (string or list of strings)')
    :param start: Start time for data fetch (default=<stop> - 30 days)
    :param stop: Stop time for data fetch (default=NOW)
    :param sampling: Data sampling (full | 5min | daily) (default=full)')
    :param unit_system: Unit system for data (eng | sci | cxc) (default=eng)
    :param resample_dt: Resample to uniform time steps (secs, default=None)
    :param remove-events: Remove kadi events (comma-separated list, default=None)
    :param select-events: Select kadi events (comma-separated list, default=None)
    :param event-pad: Additional pad time around events (secs, default=None)
    :param outfile: Output file name (default=None)
    :param quiet: Suppress run-time logging output (default=False)
    :param max_fetch_Mb: Max allowed memory for fetching (default=no max)
    :param max_resample_Mb: Max allowed memory for resampled result (default=no max)
    """
    # Set up output logging
    from pyyaks.logger import get_logger
    logger = get_logger(name='Ska.engarchive.get_telem', level=(100 if quiet else -100))

    # Set defaults and translate to fetch keywords
    stop = DateTime(stop)
    start = stop - 30 if start is None else DateTime(start)
    stat = None if sampling == 'full' else sampling
    filter_bad = resample_dt is None

    logger.info('Fetching {}-resolution data for MSIDS={} from {} to {}'
                .format(sampling, msids, start.date, stop.date))

    fetch.set_units(unit_system)

    # Make sure that the dataset being fetched is reasonable (if checking requested)
    if max_fetch_Mb is not None or max_resample_Mb is not None:
        fetch_Mb, resample_Mb = utils.get_fetch_size(msids, start, stop, stat=stat,
                                                     resample_dt=resample_dt, fast=True)
        if max_fetch_Mb is not None and fetch_Mb > max_fetch_Mb:
            raise MemoryError('Requested fetch requires {:.2f} Mb vs. limit of {:.2f} Mb'
                              .format(fetch_Mb, max_fetch_Mb))
        if max_resample_Mb is not None and resample_Mb > max_resample_Mb:
            raise MemoryError('Requested fetch (resampled) requires {:.2f} Mb '
                              'vs. limit of {:.2f} Mb'
                              .format(resample_Mb, max_resample_Mb))

    dat = fetch.MSIDset(msids, start, stop, stat=stat, filter_bad=filter_bad)

    if resample_dt is not None:
        logger.info('Resampling at {} second intervals'.format(resample_dt))
        msidset_resample(dat, resample_dt)

    if remove_events is not None:
        event_names = remove_events.split(',')
        logger.info('Removing events: {}'.format(event_names))
        queryset = get_queryset(event_names, event_pad)
        for msid in dat:
            dat[msid].remove_intervals(queryset)

    if select_events is not None:
        event_names = remove_events.split(',')
        logger.info('Selecting events: {}'.format(event_names))
        queryset = get_queryset(event_names, event_pad)
        for msid in dat:
            dat[msid].select_intervals(queryset)

    if outfile is not None:
        logger.info('Writing data to {}'.format(outfile))
        dat.write_zip(outfile)

    return dat


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

    parser.add_argument('--unit-system',
                        type=str,
                        default='eng',
                        help='Unit system for data (eng | sci | cxc) (default=eng)')

    parser.add_argument('--resample-dt',
                        type=float,
                        help='Resample to uniform time steps (secs, default=None)')

    parser.add_argument('--remove-events',
                        type=str,
                        help='Remove kadi events (comma-separated list, default=None)')

    parser.add_argument('--select-events',
                        type=str,
                        help='Select kadi events (comma-separated list, default=None)')

    parser.add_argument('--event-pad',
                        type=float,
                        help='Additional pad time around events (secs, default=None)')

    parser.add_argument('--outfile',
                        default='fetch.zip',
                        type=str,
                        help='Output file name (default=fetch.zip)')

    parser.add_argument('--quiet',
                        action='store_true',
                        help='Suppress run-time logging output')

    parser.add_argument('msids',
                        metavar='MSID',
                        type=str,
                        nargs='+',
                        help='MSID to fetch')

    opt = parser.parse_args()
    return opt


if __name__ == '__main__':
    opt = get_opt()
    _get_telem(**vars(opt))
