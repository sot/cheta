# Licensed under a 3-clause BSD style license - see LICENSE.rst

import argparse
import gzip
import pickle
import re
from itertools import count
from pathlib import Path

import numpy as np
import pyyaks.context
import pyyaks.logger
import tables
from Chandra.Time import DateTime
from Ska.DBI import DBI
from astropy.table import Table

import Ska.engarchive.fetch as fetch
import Ska.engarchive.file_defs as file_defs


def get_options(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root",
                        default=".",
                        help="Root directory for sync files (default='.')")
    parser.add_argument("--content",
                        action='append',
                        help="Content type to process [match regex] (default = all)")
    parser.add_argument("--max-days",
                        type=float,
                        default=1.5,
                        help="Maximum number of days of files per sync directory")
    parser.add_argument("--min-days",
                        type=float,
                        default=0.5,
                        help="Minimum number of days of files per sync directory")
    parser.add_argument("--log-level",
                        help="Logging level")
    parser.add_argument("--date-start",
                        help="Start process date for initial index creation")
    parser.add_argument("--date-stop",
                        help="Stop process date (mostly for testing, default=process all)")
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
        msid_contents = pickle.load(open(filename, 'rb'))
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
        update_sync_data_full(content, sync_files, logger, row)

        for stat in ('5min', 'daily'):
            update_sync_data_stat(content, sync_files, logger, row, stat)


def get_row_from_archfiles(archfiles):
    # Make a row that encapsulates info for this setup of data updates. The ``date_id`` key is a
    # date like 2019-02-20T2109z, human-readable and Windows-friendly (no :) for a unique
    # identifier for this set of updates.
    row = {'filetime0': archfiles[0]['filetime'],
           'filetime1': archfiles[-1]['filetime'],
           'date_id': re.sub(':', '', archfiles[0]['date'][:16]) + 'z',
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

    if np.any(np.diff(filetimes) <= 0):
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
        filetime0 = index_tbl['filetime1'][-1]
    else:
        # For initial index file creation use the --date-start option
        index_tbl = None
        filetime0 = DateTime(opt.date_start).secs

    max_secs = int(opt.max_days * 86400)
    min_secs = int(opt.min_days * 86400)

    # Step through the archfile files entries and collect them into groups of up
    # to --max-days based on file time stamp (which is an integer in CXC secs).
    rows = []
    with DBI(dbi='sqlite', server=fetch.msid_files['archfiles'].abs) as dbi:
        while True:
            filetime1 = filetime0 + max_secs
            archfiles = dbi.fetchall(f'select * from archfiles '
                                     f'where filetime > {filetime0} '
                                     f'and filetime < {filetime1} '
                                     f'order by filetime ')

            # Require new archfiles and don't allow a small "hanging" row at the end
            if len(archfiles) > 0 and archfiles['filetime'][-1] - filetime0 > min_secs:
                rows.append(get_row_from_archfiles(archfiles))
                filetime0 = filetime1
            else:
                break

            # User-specified stop date instead of processing to end of available entries.
            # Mostly for initial testing.
            if opt.date_stop is not None and filetime1 > DateTime(opt.date_stop).secs:
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
    ft['date_id'] = row['date_id']

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

        with tables.open_file(fetch.msid_files['msid'].abs, 'r') as h5:
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


def _get_stat_data_from_archive(filename, stat, tstart, tstop):
    """
    Return stat table rows in the range tstart <= time < tstop.

    Also returns the corresponding table row indexes.

    :param filename: HDF5 file to read
    :param stat: stat (5min or daily)
    :param tstart: min time
    :param tstop: max time
    :return:
    """
    dt = {'5min': 328, 'daily': 86400}[stat]

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

            table_rows = table[row0:row1]  # returns np.ndarray (structured array)

    return table_rows, row0, row1


def update_sync_data_stat(content, sync_files, logger, row, stat):
    """
    Update stats (5min, daily) sync data for index table ``row``

    :param content:
    :param sync_files:
    :param logger:
    :param row:
    :param stat:
    :return:
    """
    ft = fetch.ft
    ft['row0'] = row['row0']
    ft['row1'] = row['row1']
    ft['interval'] = stat

    outfile = Path(sync_files['data'].abs)
    if outfile.exists():
        logger.debug(f'Skipping {outfile}, already exists')
        return

    # First get the times corresponding to row0 and row1
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

    # Go through each MSID and get the raw HDF5 table data corresponding to the
    # time range tstart:tstop found above.
    n_rows_set = set()
    for msid in msids:
        ft['msid'] = msid
        filename = fetch.msid_files['stats'].abs
        stat_rows, row0, row1 = _get_stat_data_from_archive(filename, stat, tstart, tstop)
        n_rows_set.add(row1 - row0)
        if row1 > row0:
            out[f'{msid}.data'] = stat_rows
            out[f'{msid}.row0'] = row0
            out[f'{msid}.row1'] = row1

    if len(n_rows_set) > 1:
        logger.warning(f'Unexpected difference in number of rows: {n_rows_set}')

    n_msids = len(msids)
    n_rows = n_rows_set.pop() if len(n_rows_set) == 1 else n_rows_set
    logger.info(f'Writing {outfile} with {n_rows} rows of data and {n_msids} msids')

    outfile.parent.mkdir(exist_ok=True, parents=True)
    # TODO: increase compression to max (gzip?)
    with gzip.open(outfile, 'wb') as fh:
        pickle.dump(out, fh)


if __name__ == '__main__':
    main()
