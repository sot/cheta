# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
Update the repository of sync files on the server which can be used by
clients to maintain a local copy of the cheta telemetry archive.

The basic concept is to bundle about a day of raw telemetry values
(full-resolution, 5-minute stats and daily stats) for each MSID into
compressed data files that are served by the icxc web server and can
be easily downloaded to client machines.

This pairs with the ``cheta_update_client_archive`` script which uses
these sync files to keep a local cheta archive up to date.

The file structure is as follows::

  sync/                                        Top-level, accessible from icxc URL
  sync/msid_contents.pkl.gz                    Dict of all MSID:content key pairs
  sync/acis4eng/                               Content type
  sync/acis4eng/index.ecsv                     Index of bundles
  sync/acis4eng/last_rows_5min.pkl             Last row index for 5min data for each MSID
  sync/acis4eng/last_rows_daily.pkl            Last row index for daily data for each MSID
  sync/acis4eng/2019-07-29T2340z/              One bundle of sync data
  sync/acis4eng/2019-07-29T2340z/full.pkl.gz   Full-resolution data for all acis4eng MSIDs
  sync/acis4eng/2019-07-29T2340z/5min.pkl.gz   5-minute data
  sync/acis4eng/2019-07-29T2340z/daily.pkl.gz  Daily data

This script reads from the cheta telemetry archive and updates the
sync repository to capture newly-available data since the last bundle.
"""


import argparse
import gzip
import pickle
import shutil
from itertools import count
from pathlib import Path

import numpy as np
import pyyaks.context
import pyyaks.logger
import tables
from Chandra.Time import DateTime
from Ska.DBI import DBI
from astropy.table import Table

from . import fetch
from . import file_defs
from .utils import get_date_id, STATS_DT


def get_options(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root",
                        default=".",
                        help="Root directory for sync files (default='.')")
    parser.add_argument("--content",
                        action='append',
                        help="Content type to process [match regex] (default = all)")
    parser.add_argument("--max-days",
                        type=float,
                        default=1.5,
                        help="Max number of days of files per sync directory (default=1.5)")
    parser.add_argument("--max-lookback",
                        type=float,
                        default=45,
                        help="Maximum number of days to look back from --date-stop (default=45)")
    parser.add_argument("--log-level",
                        help="Logging level")
    parser.add_argument("--date-start",
                        help="Start process date (default=NOW - max-lookback)")
    parser.add_argument("--date-stop",
                        help="Stop process date (default=NOW)")
    return parser.parse_args(args)


def update_msid_contents_pkl(sync_files, logger):
    """
    Update the `msid_contents.pkl` file to contain a dict of the msid:content pairs.

    :return: None
    """
    filename = Path(sync_files['msid_contents'].abs)

    # Check if an existing version of the file is the same and do not overwrite
    # in that case.
    if filename.exists():
        with gzip.open(filename, 'rb') as fh:
            msid_contents = pickle.load(fh)
        if msid_contents == fetch.content:
            return

    logger.info(f'Writing contents pickle {filename}')
    with gzip.open(filename, 'wb') as fh:
        pickle.dump(fetch.content, fh, protocol=-1)


def main(args=None):
    # Setup for updating the sync repository
    opt = get_options(args)

    sync_files = pyyaks.context.ContextDict('update_sync_repo.sync_files',
                                            basedir=opt.data_root)
    sync_files.update(file_defs.sync_files)

    # Set up logging
    loglevel = pyyaks.logger.VERBOSE if opt.log_level is None else int(opt.log_level)
    logger = pyyaks.logger.get_logger(name='engarchive_update_sync', level=loglevel,
                                      format="%(asctime)s %(message)s")

    # Also adjust fetch logging if non-default log-level supplied (mostly for debug)
    if opt.log_level is not None:
        fetch.add_logging_handler(level=int(opt.log_level))

    if opt.content:
        contents = opt.content
    else:
        contents = set(fetch.content.values())

    for content in sorted(contents):
        update_sync_repo(opt, sync_files, logger, content)

    # Make the main msid_contents.pkl file
    update_msid_contents_pkl(sync_files, logger)


def remove_outdated_sync_files(opt, sync_files, logger, index_tbl):
    """
    Remove the sync data dirs and index file rows which correspond to data
    that is more than opt.max_lookback days older than opt.date_stop (typically
    NOW).

    :param opt: options
    :param sync_files: sync files context dict
    :param logger: logger
    :param index_tbl: table containing sync repo entries
    :return: mask of rows that were removed
    """
    min_time = (DateTime(opt.date_stop) - opt.max_lookback).secs
    remove_mask = np.zeros(len(index_tbl), dtype=bool)

    for idx, row in enumerate(index_tbl):
        if row['filetime0'] < min_time:
            fetch.ft['date_id'] = row['date_id']
            remove_mask[idx] = True
            data_dir = sync_files['data_dir'].abs
            if Path(data_dir).exists():
                logger.info(f'Removing sync directory {data_dir}')
                shutil.rmtree(data_dir)

    return remove_mask


def update_sync_repo(opt, sync_files, logger, content):
    """

    :param opt: argparse options
    :param sync_files: Sync repo files context dict
    :param logger: logger instance
    :param content: content type
    :return:
    """
    # File types context dict
    ft = fetch.ft
    ft['content'] = content

    index_file = Path(sync_files['index'].abs)
    index_tbl = update_index_file(index_file, opt, logger)

    if index_tbl is None:
        # Index table was not created, nothing more to do here
        logger.warning(f'No index table for {content}')
        return

    for row in index_tbl:
        ft = fetch.ft
        ft['date_id'] = row['date_id']

        update_sync_data_full(content, sync_files, logger, row)
        update_sync_data_stat(content, sync_files, logger, row, '5min')
        update_sync_data_stat(content, sync_files, logger, row, 'daily')

    remove_mask = remove_outdated_sync_files(opt, sync_files, logger, index_tbl)
    if np.any(remove_mask):
        index_tbl = index_tbl[~remove_mask]
        logger.info(f'Writing {len(index_tbl)} row(s) to index file {index_file}')
        index_tbl.write(index_file, format='ascii.ecsv')


def get_row_from_archfiles(archfiles):
    # Make a row that encapsulates info for this setup of data updates. The ``date_id`` key is a
    # date like 2019-02-20T2109z, human-readable and Windows-friendly (no :) for a unique
    # identifier for this set of updates.
    date_id = get_date_id(DateTime(archfiles[0]['filetime']).fits)
    row = {'filetime0': archfiles[0]['filetime'],
           'filetime1': archfiles[-1]['filetime'],
           'date_id': date_id,
           'row0': archfiles[0]['rowstart'],
           'row1': archfiles[-1]['rowstop']}
    return row


def check_index_tbl_consistency(index_tbl):
    """
    Check for consistency of the index table.

    :param index_tbl: index table (astropy Table)
    :return msg: inconsistency message or None
    """
    filetimes = []
    for row in index_tbl:
        filetimes.append(row['filetime0'])
        filetimes.append(row['filetime1'])

    if np.any(np.diff(filetimes) < 0):
        msg = 'filetime values not monotonically increasing'
        return msg

    for idx, row0, row1 in zip(count(), index_tbl[:-1], index_tbl[1:]):
        if row0['row1'] != row1['row0']:
            msg = f'rows not contiguous at table date0={index_tbl["date_id"][idx]}'
            return msg

    # No problems
    return None


def update_index_file(index_file, opt, logger):
    """Update the top-level index file of data available in the sync archive

    :param index_file: Path of index ECSV file
    :param opt: options
    :param logger: output logger
    :return: index table (astropy Table)
    """
    if index_file.exists():
        index_tbl = Table.read(index_file)
        # Start time of last archfile contained in the sync repo, but do not look
        # back more than max_lookback days.  This is relevant for rarely sampled
        # content like cpe1eng.
        filetime0 = max(index_tbl['filetime1'][-1],
                        (DateTime(opt.date_stop) - opt.max_lookback).secs)
    else:
        # For initial index file creation use the --date-start option
        index_tbl = None
        filetime0 = DateTime(opt.date_start).secs

    max_secs = int(opt.max_days * 86400)
    time_stop = DateTime(opt.date_stop).secs

    # Step through the archfile files entries and collect them into groups of up
    # to --max-days based on file time stamp (which is an integer in CXC secs).
    rows = []
    filename = fetch.msid_files['archfiles'].abs
    logger.debug(f'Opening archfiles {filename}')
    with DBI(dbi='sqlite', server=filename) as dbi:
        while True:
            filetime1 = min(filetime0 + max_secs, time_stop)
            logger.verbose(f'select from archfiles '
                           f'filetime > {DateTime(filetime0).fits[:-4]} {filetime0} '
                           f'filetime <= {DateTime(filetime1).fits[:-4]} {filetime1} '
                           )
            archfiles = dbi.fetchall(f'select * from archfiles '
                                     f'where filetime > {filetime0} '
                                     f'and filetime <= {filetime1} '
                                     f'order by filetime ')

            # Found new archfiles?  If so get a new index table row for them.
            if len(archfiles) > 0:
                rows.append(get_row_from_archfiles(archfiles))
                filedates = DateTime(archfiles['filetime']).fits
                logger.verbose(f'Got {len(archfiles)} rows {filedates}')

            filetime0 = filetime1

            # Stop if already queried out to the end of desired time range
            if filetime1 >= time_stop:
                break

    if not rows:
        logger.info(f'No updates available for content {fetch.ft["content"]}')
        return index_tbl

    # Create table from scratch or add new rows.  In normal processing there
    # will just be one row per run.
    if index_tbl is None:
        index_tbl = Table(rows)
    else:
        for row in rows:
            index_tbl.add_row(row)

    if not index_file.parent.exists():
        logger.info(f'Making directory {index_file.parent}')
        index_file.parent.mkdir(exist_ok=True, parents=True)

    msg = check_index_tbl_consistency(index_tbl)
    if msg:
        msg += '\n'
        msg += '\n'.join(index_tbl.pformat(max_lines=-1, max_width=-1))
        logger.error(f'Index table inconsistency: {msg}')
        return None

    logger.info(f'Writing {len(rows)} row(s) to index file {index_file}')
    index_tbl.write(index_file, format='ascii.ecsv')

    return index_tbl


def update_sync_data_full(content, sync_files, logger, row):
    """
    Update full-resolution sync data including archfiles for index table ``row``

    :param content:
    :param sync_files:
    :param logger:
    :param row:
    :return:
    """
    ft = fetch.ft
    ft['interval'] = 'full'

    outfile = Path(sync_files['data'].abs)
    if outfile.exists():
        logger.debug(f'Skipping {outfile}, already exists')
        return

    out = {}
    msids = list(fetch.all_colnames[content]) + ['TIME']

    with DBI(dbi='sqlite', server=fetch.msid_files['archfiles'].abs) as dbi:
        query = (f'select * from archfiles '
                 f'where filetime >= {row["filetime0"]} '
                 f'and filetime <= {row["filetime1"]} '
                 f'order by filetime ')
        archfiles = dbi.fetchall(query)
        out['archfiles'] = archfiles

    for msid in msids:
        ft['msid'] = msid
        filename = fetch.msid_files['msid'].abs
        if not Path(filename).exists():
            logger.debug(f'No MSID file for {msid} - skipping')
            continue

        with tables.open_file(filename, 'r') as h5:
            out[f'{msid}.quality'] = h5.root.quality[row['row0']:row['row1']]
            out[f'{msid}.data'] = h5.root.data[row['row0']:row['row1']]
            out[f'{msid}.row0'] = row['row0']
            out[f'{msid}.row1'] = row['row1']

    n_rows = row['row1'] - row['row0']
    n_msids = len(msids)
    logger.info(f'Writing {outfile} with {n_rows} rows of data and {n_msids} msids')

    outfile.parent.mkdir(exist_ok=True, parents=True)
    # TODO: increase compression to max (gzip?)
    with gzip.open(outfile, 'wb') as fh:
        pickle.dump(out, fh)


def _get_stat_data_from_archive(filename, stat, tstart, tstop, last_row1, logger):
    """
    Return stat table rows in the range tstart <= time < tstop.

    Also returns the corresponding table row indexes.

    :param filename: HDF5 file to read
    :param stat: stat (5min or daily)
    :param tstart: min time
    :param tstop: max time
    :param last_row1: row1 for previous index table entry
    :param logger: logger
    :return:
    """
    dt = STATS_DT[stat]

    with tables.open_file(filename, 'r') as h5:
        # Check if tstart is beyond the end of the table.  If so, return an empty table
        table = h5.root.data
        last_index = table[-1]['index']
        last_time = (last_index + 0.5) * dt
        if tstart > last_time:
            row0 = row1 = len(table)
            table_rows = table[row0:row1]
        else:
            # Compute approx number of rows from the end for tstart.  Normally the index value
            # goes in lock step with row, but it can happen that an index is missed because of
            # missing data.  But if we back up by delta_rows, we are guaranteed to get to at
            # least the row corresponding to tstart.
            delta_rows = int((last_time - tstart) / dt) + 10
            times = (table[-delta_rows:]['index'] + 0.5) * dt

            sub_row0, sub_row1 = np.searchsorted(times, [tstart, tstop])
            sub_row_offset = len(table) - delta_rows

            row0 = sub_row0 + sub_row_offset
            row1 = sub_row1 + sub_row_offset

            # If we have the last value of row1 (from previous sync entry) then use
            # that instead of computed value for row0.  Issue a warning if they are different
            # (not really a problem but maybe useful for finding off-by-one issues).
            if last_row1 is not None:
                if last_row1 != row0:
                    logger.info(f'Warning: last_row1={last_row1} != computed row0={row0} '
                                f'for {filename}')
                row0 = last_row1

            table_rows = table[row0:row1]  # returns np.ndarray (structured array)

    return table_rows, row0, row1


def update_sync_data_stat(content, sync_files, logger, row, stat):
    """
    Update stats (5min, daily) sync data for index table ``row``

    :param content: content name (e.g. acis4eng)
    :param sync_files: sync files context object (for file paths)
    :param logger: logger
    :param row: one row of the full-res index table
    :param stat: stat interval (5min or daily)
    :return:
    """
    ft = fetch.ft
    ft['interval'] = stat

    outfile = Path(sync_files['data'].abs)
    if outfile.exists():
        logger.debug(f'Skipping {outfile}, already exists')
        return

    # First get the times corresponding to row0 and row1 in the full resolution archive
    ft['msid'] = 'TIME'
    with tables.open_file(fetch.msid_files['msid'].abs, 'r') as h5:
        table = h5.root.data
        tstart = table[row['row0']]
        # Ensure that table row1 (for tstop) doesn't fall off the edge since the last
        # index file row will have row1 exactly equal to the table length.
        row1 = min(row['row1'], len(table) - 1)
        tstop = table[row1]

    out = {}
    msids = list(fetch.all_colnames[content] - set(fetch.IGNORE_COLNAMES))

    # Get dict of last sync repo row for each MSID.  This is keyed as {msid: last_row1},
    # where row1 is (as always) the slice row1.
    last_rows_filename = sync_files['last_rows'].abs
    if Path(last_rows_filename).exists():
        logger.verbose(f'Reading {last_rows_filename}')
        last_rows = pickle.load(open(last_rows_filename, 'rb'))
    else:
        last_rows = {}

    # Go through each MSID and get the raw HDF5 table data corresponding to the
    # time range tstart:tstop found above.
    n_rows_set = set()
    for msid in msids:
        last_row1 = last_rows.get(msid)
        ft['msid'] = msid
        filename = fetch.msid_files['stats'].abs
        if not Path(filename).exists():
            logger.debug(f'No {stat} stat data for {msid} - skipping')
            continue

        stat_rows, row0, row1 = _get_stat_data_from_archive(
            filename, stat, tstart, tstop, last_row1, logger)
        logger.verbose(f'Got stat rows {row0} {row1} for stat {stat} {msid}')
        n_rows_set.add(row1 - row0)
        if row1 > row0:
            out[f'{msid}.data'] = stat_rows
            out[f'{msid}.row0'] = row0
            out[f'{msid}.row1'] = row1
            last_rows[msid] = row1

    if len(n_rows_set) > 1:
        logger.warning(f'Unexpected difference in number of rows: {n_rows_set}')

    n_msids = len(msids)
    n_rows = n_rows_set.pop() if len(n_rows_set) == 1 else n_rows_set

    outfile.parent.mkdir(exist_ok=True, parents=True)
    # TODO: increase compression to max (gzip?)
    logger.info(f'Writing {outfile} with {n_rows} rows of data and {n_msids} msids')
    with gzip.open(outfile, 'wb') as fh:
        pickle.dump(out, fh)

    # Save the row1 value for each MSID to use as row0 for the next update
    logger.verbose(f'Writing {last_rows_filename}')
    with open(last_rows_filename, 'wb') as fh:
        pickle.dump(last_rows, fh)


if __name__ == '__main__':
    main()
