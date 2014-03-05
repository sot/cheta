"""
Fetch telemetry from the Ska engineering archive.

This bundles many of the common steps of data retrieval into one routine which can be
accessed either through the command line with ``ska_fetch`` or via the ``get_telem()`` function.

Examples ========

  # Get TEPHIN, AOPCADMD for last 30 days, selecting maneuvers during rad zones
  % ska_fetch --select-events="manvrs & rad_zones" --unit-system=sci TEPHIN AOPCADMD

Arguments
=========
"""

from __future__ import print_function, division

import argparse
import re

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


def get_queryset(expr, event_pad):
    """
    Get query set for ``expr`` (a python-like expression).
    """
    from kadi import events

    seps = '()~|&'
    re_seps = '([' + seps + '])'
    expr = re.sub('\s+', '', expr)
    # Split expr by separators and then toss out '' elements
    tokens = [x for x in re.split(re_seps, expr) if x]

    for i, token in enumerate(tokens):
        if token not in seps:
            try:
                query_event = getattr(events, token)
                if not isinstance(query_event, events.query.EventQuery):
                    raise TypeError
                tokens[i] = 'events.{}'.format(token)
                if event_pad is not None:
                    tokens[i] += '(pad={})'.format(event_pad)
            except:
                raise ValueError('Expression token {!r} is not a valid event type'
                                 .format(token))

    queryset_expr = ' '.join(tokens)
    return eval(queryset_expr)


def get_telem(msids, start=None, stop=None, sampling='all', unit_system='eng',
              resample_dt=None, remove_events=None, select_events=None, event_pad=None,
              time_format=None, outfile=None, quiet=False,
              max_fetch_Mb=None, max_output_Mb=None):
    """
    High-level routine to get telemetry for one or more MSIDs and perform
    common post-processing functions.

    This is a non-public version that really does the work.  The public interface
    is fetch.get_telem(), which is a thin wrapper for this.  (Trying to factor code
    out to separate modules and keep import times down).  See get_telem() for param
    docs.
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
    if max_fetch_Mb is not None or max_output_Mb is not None:
        fetch_Mb, output_Mb = utils.get_fetch_size(msids, start, stop, stat=stat,
                                                   resample_dt=resample_dt, fast=True)
        if max_fetch_Mb is not None and fetch_Mb > max_fetch_Mb:
            raise MemoryError('Requested fetch requires {:.2f} Mb vs. limit of {:.2f} Mb'
                              .format(fetch_Mb, max_fetch_Mb))
        if max_output_Mb is not None and output_Mb > max_output_Mb:
            raise MemoryError('Requested fetch (resampled) requires {:.2f} Mb '
                              'vs. limit of {:.2f} Mb'
                              .format(output_Mb, max_output_Mb))

    dat = fetch.MSIDset(msids, start, stop, stat=stat, filter_bad=filter_bad)

    if resample_dt is not None:
        logger.info('Resampling at {} second intervals'.format(resample_dt))
        msidset_resample(dat, resample_dt)

    if remove_events is not None:
        logger.info('Removing events: {}'.format(remove_events))
        queryset = get_queryset(remove_events, event_pad)
        for msid in dat:
            dat[msid].remove_intervals(queryset)

    if select_events is not None:
        logger.info('Selecting events: {}'.format(select_events))
        queryset = get_queryset(select_events, event_pad)
        for msid in dat:
            dat[msid].select_intervals(queryset)

    if time_format not in (None, 'secs'):
        for dat_msid in dat.values():
            dat_msid.times = getattr(DateTime(dat_msid.times, format='secs'), time_format)

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
                        help='Data sampling (all|5min|daily) (default=5min)')

    parser.add_argument('--unit-system',
                        type=str,
                        default='eng',
                        help='Unit system for data (eng|sci|cxc) (default=eng)')

    parser.add_argument('--resample-dt',
                        type=float,
                        help='Resample to uniform time steps (secs, default=None)')

    parser.add_argument('--remove-events',
                        type=str,
                        help='Remove kadi events expression (default=None)')

    parser.add_argument('--select-events',
                        type=str,
                        help='Select kadi events expression (default=None)')

    parser.add_argument('--event-pad',
                        type=float,
                        help='Additional pad time around events (secs, default=None)')

    parser.add_argument('--time-format',
                        type=str,
                        help='Output time format (secs|date|greta|jd|frac_year|...)')

    parser.add_argument('--outfile',
                        default='fetch.zip',
                        type=str,
                        help='Output file name (default=fetch.zip)')

    parser.add_argument('--quiet',
                        action='store_true',
                        help='Suppress run-time logging output')

    parser.add_argument('--max-fetch-Mb',
                        default=100.0,
                        type=float,
                        help='Max allowed memory (Mb) for fetching (default=100)')

    parser.add_argument('--max-output-Mb',
                        default=20.0,
                        type=float,
                        help='Max allowed memory (Mb) for output (default=20)')

    parser.add_argument('msids',
                        metavar='MSID',
                        type=str,
                        nargs='+',
                        help='MSID to fetch')

    opt = parser.parse_args()
    return opt


def main():
    opt = get_opt()
    try:
        get_telem(**vars(opt))
    except MemoryError as err:
        print('\n'.join(['',
                         '*' * 80,
                         'ERROR: {}'.format(err),
                         '*' * 80, '']))
    except Exception as err:
        print('\n'.join(['',
                         '*' * 80,
                         'ERROR: {}'.format(err),
                         'If necessary report the following traceback to aca@head.cfa.harvard.edu',
                         '*' * 80, '']))
        raise