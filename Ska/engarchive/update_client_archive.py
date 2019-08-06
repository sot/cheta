# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Synchronize local client copy of cheta archive to the server version.

This uses the bundles of sync data that are available on the ICXC server
to update the local HDF5 files that comprise the cheta telemetry archive.
It also updates the archfiles.db3 that serve as a date index for queries.

Note that this updates cheta files in $SKA/data/eng_archive.  One can
change the output directory by setting the environment variable
``ENG_ARCHIVE``.
"""

import argparse
import contextlib
import gzip
import os
import pickle
import re
import sqlite3
import urllib
from pathlib import Path

import numpy as np
import pyyaks.context
import pyyaks.logger
import tables
from Chandra.Time import DateTime
from Ska.DBI import DBI
from astropy.table import Table
from astropy.utils.data import download_file

from . import fetch
from . import file_defs
from .utils import get_date_id, STATS_DT


def get_options(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root",
                        default='https://icxc.cfa.harvard.edu/aspect/cheta/',
                        help=("URL or file dir for sync files "
                              "(default=https://icxc.cfa.harvard.edu/aspect/cheta/)"))
    parser.add_argument("--content",
                        action='append',
                        help="Content type to process [match regex] (default=all)")
    parser.add_argument("--log-level",
                        default=20,
                        help="Logging level (default=20 (info))")
    parser.add_argument("--date-stop",
                        help="Stop process date (default=NOW)")
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Dry run (no actual file or database updates)")

    opt = parser.parse_args(args)
    opt.is_url = re.match(r'http[s]?://', opt.data_root)
    opt.date_stop = DateTime(opt.date_stop)

    return opt


@contextlib.contextmanager
def get_readable(data_root, is_url, filename):
    """
    Get readable filename from either a local file or remote URL.

    Returns None for the output filename if input does not exist.

    :param data_root:
    :param is_url:
    :param filename:
    :return: filename, URI
    """
    try:
        if is_url:
            uri = data_root.rstrip('/') + '/' + Path(filename).as_posix()
            filename = download_file(uri, show_progress=False, cache=False, timeout=60)
        else:
            uri = filename
            assert os.path.exists(uri)
    except (AssertionError, urllib.error.HTTPError):
        filename = None

    try:
        yield filename, uri
    finally:
        if is_url and filename is not None:
            # Clean up tmp file
            os.unlink(filename)


def sync_full_archive(opt, sync_files, msid_files, logger, content):
    """
    Sync the archive for ``content``.

    :param opt:
    :param sync_files:
    :param msid_files:
    :param logger:
    :param content:
    :return:
    """
    # Get the last row of data from the length of the TIME.col (or archfiles?)
    ft = fetch.ft
    ft['content'] = content
    ft['msid'] = 'TIME'
    ft['interval'] = 'full'

    # If no TIME.h5 file then no point in going further
    time_file = Path(msid_files['msid'].abs)
    if not time_file.exists():
        logger.debug(f'Skipping full data for {content}: no {time_file} file')
        return

    logger.info('')
    logger.info(f'Processing full data for {content}')

    # Read the index file to know what is available for new data
    index_file = sync_files['index'].rel
    with get_readable(opt.data_root, opt.is_url, index_file) as (index_input, uri):
        if index_input is None:
            # If index_file is not found then get_readable returns None
            logger.info(f'No new sync data for {content}: {uri} not found')
            return
        logger.info(f'Reading index file {uri}')
        index_tbl = Table.read(index_input, format='ascii.ecsv')

    # Get the 0-based index of last available full data row
    with tables.open_file(str(time_file), 'r') as h5:
        last_row_idx = len(h5.root.data) - 1

    # Look for index table rows that have new data => the row ends after the last existing
    # data.  Note: row0 and row1 correspond to the slice row0:row1, so up to but
    # not including the row indexed row1 (0-based).  So for 3 existing rows,
    # last_row_idx=2 so to get the new row with index=3 you need row1=4, or equivalently
    # row1 > n_rows. By def'n we know that row0 <= 3 at this point.
    ok = index_tbl['row1'] > last_row_idx + 1

    if np.count_nonzero(ok) == 0:
        logger.info(f'No new sync data for {content}: no new rows in index table')

    index_tbl = index_tbl[ok]

    # Iterate over sync files that contain new data
    for date_id, filetime0, filetime1, row0, row1 in index_tbl:
        # Limit processed archfiles by date
        if filetime0 > DateTime(opt.date_stop).secs:
            break

        # File names like sync/acis4eng/2019-07-08T1150z/full.npz
        ft['date_id'] = date_id
        datafile = sync_files['data'].rel

        # Read the file with all the MSID data as a hash with keys like {msid}.data
        # {msid}.quality etc, plus an `archive` key with the table of corresponding
        # archfiles rows.
        with get_readable(opt.data_root, opt.is_url, datafile) as (data_input, uri):
            logger.info(f'Reading update date file {uri}')
            with gzip.open(data_input, 'rb') as fh:
                dat = pickle.load(fh)

        # Find the MSIDs in this file
        msids = {key[:-5] for key in dat if key.endswith('.data')}

        for msid in msids:
            vals = {key: dat[f'{msid}.{key}'] for key in ('data', 'quality', 'row0', 'row1')}

            # If this row begins before then end of current data then chop the
            # beginning of data for this row.
            if vals['row0'] <= last_row_idx:
                idx0 = last_row_idx + 1 - vals['row0']
                logger.debug(f'Chopping {idx0 + 1} rows from data')
                for key in ('data', 'quality'):
                    vals[key] = vals[key][idx0:]
                vals['row0'] += idx0

            append_h5_col(opt, msid, vals, logger, msid_files)

        # Update the archfiles.db3 database to include the associated archive files
        server_file = msid_files['archfiles'].abs
        logger.debug(f'Updating {server_file}')

        def as_python(val):
            try:
                return val.item()
            except AttributeError:
                return val

        with DBI(dbi='sqlite', server=server_file) as db:
            for archfile in dat['archfiles']:
                vals = {name: as_python(archfile[name]) for name in archfile.dtype.names}
                logger.debug(f'Inserting {vals["filename"]}')
                if not opt.dry_run:
                    try:
                        db.insert(vals, 'archfiles')
                    except sqlite3.IntegrityError as err:
                        # Expected exception for archfiles already in the table
                        assert 'UNIQUE constraint failed: archfiles.filename' in str(err)

            if not opt.dry_run:
                db.commit()


def sync_stat_archive(opt, sync_files, msid_files, logger, content, stat):
    """
    Sync the archive for ``content``.

    :param opt:
    :param sync_files:
    :param msid_files:
    :param logger:
    :param content:
    :param stat: stat interval '5min' or 'daily'
    :return:
    """
    # Get the last row of data from the length of the TIME.col (or archfiles?)
    ft = fetch.ft
    ft['content'] = content
    ft['interval'] = stat

    stats_dir = Path(msid_files['statsdir'].rel)
    if not stats_dir.exists():
        logger.debug(f'Skipping {stat} data for {content}: no directory')
        return

    logger.info('')
    logger.info(f'Processing {stat} data for {content}')

    # Read the index file to know what is available for new data
    # TODO: factor this out
    index_file = sync_files['index'].rel
    with get_readable(opt.data_root, opt.is_url, index_file) as (index_input, uri):
        if index_input is None:
            # If index_file is not found then get_readable returns None
            logger.info(f'No new {stat} sync data for {content}: {uri} not found')
            return
        logger.info(f'Reading index file {uri}')
        index_tbl = Table.read(index_input, format='ascii.ecsv')

    # Get the MSIDs that are in client archive
    msids = [str(fn.name)[:-3] for fn in stats_dir.glob('*.h5')]
    if not msids:
        logger.debug(f'Skipping {stat} data for {content}: no stats h5 files')
        return
    else:
        logger.debug(f'Stat msids are {msids}')

    last_date_id, last_date_id_file = get_last_date_id(
        msid_files, msids, stat, logger)
    logger.verbose(f'Got {last_date_id} as last date_id that was applied to archive')

    # Iterate over sync files that contain new data
    for date_id, filetime0, filetime1, row0, row1 in index_tbl:
        # Limit processed archfiles by date
        if filetime0 > DateTime(opt.date_stop).secs:
            logger.verbose(f'Index {date_id} filetime0 > date_stop, breaking')
            break

        # Compare date_id of this row to last one that was processed.  These
        # are lexically ordered
        if date_id <= last_date_id:
            logger.verbose(f'Index {date_id} already processed, skipping')
            continue

        # File names like sync/acis4eng/2019-07-08T1150z/5min.npz
        ft['date_id'] = date_id
        datafile = sync_files['data'].rel

        # Read the file with all the MSID data as a hash with keys {msid}.data
        # {msid}.row0, {msid}.row1
        with get_readable(opt.data_root, opt.is_url, datafile) as (data_input, uri):
            logger.info(f'Reading update date file {uri}')
            with gzip.open(data_input, 'rb') as fh:
                dat = pickle.load(fh)

        # Find the MSIDs in this file
        msids = {key[:-5] for key in dat if key.endswith('.data')}

        for msid in msids:
            fetch.ft['msid'] = msid
            stat_file = msid_files['stats'].rel
            if os.path.exists(stat_file):
                append_stat_col(dat, stat_file, msid, date_id, opt, logger)

        logger.debug(f'Updating {last_date_id_file} with {date_id}')
        with open(last_date_id_file, 'w') as fh:
            fh.write(f'{date_id}')


def append_stat_col(dat, stat_file, msid, date_id, opt, logger):
    """
    Append ``dat`` to the appropriate stats h5 file.

    :param dat:
    :param stat_file:
    :param msid:
    :param date_id:
    :param opt:
    :param logger:
    :return: None
    """
    vals = {key: dat[f'{msid}.{key}'] for key in ('data', 'row0', 'row1')}
    logger.debug(f'append_stat_col msid={msid} date_id={date_id}, '
                 f'row0,1 = {vals["row0"]} {vals["row1"]}')

    mode = 'r' if opt.dry_run else 'a'
    with tables.open_file(stat_file, mode=mode) as h5:
        last_row_idx = len(h5.root.data) - 1

        # Check if there is any new data in this chunk
        if vals['row1'] - 1 <= last_row_idx:
            logger.debug(f'Skipping {date_id} for {msid}: no new data '
                         f'row1={vals["row1"]} last_row_idx={last_row_idx}')
            return

        # If this row begins before then end of current data then chop the
        # beginning of data for this row.
        if vals['row0'] <= last_row_idx:
            idx0 = last_row_idx + 1 - vals['row0']
            logger.debug(f'Chopping {idx0 + 1} rows from data')
            vals['data'] = vals['data'][idx0:]
            vals['row0'] += idx0

        if vals['row0'] != len(h5.root.data):
            raise ValueError(f'ERROR: unexpected discontinuity '
                             f'row0 {vals["row0"]} != len {len(h5.root.data)}')

        logger.debug(f'Appending {len(vals["data"])} rows to {stat_file}')
        if not opt.dry_run:
            h5.root.data.append(vals['data'])


def get_last_date_id(msid_files, msids, stat, logger):
    """
    Get the last date_id used for syncing the client archive.  First try the
    last_date_id file.  If this does not exist then infer a reasonable value
    by looking at stat data for ``msids``

    :param msid_files:
    :param msids:
    :param stat:
    :param logger:
    :return:
    """
    last_date_id_file = msid_files['last_date_id'].rel

    if Path(last_date_id_file).exists():
        logger.verbose(f'Reading {last_date_id_file} to get last update time')
        with open(last_date_id_file, 'r') as fh:
            last_date_id = fh.read()
    else:
        logger.verbose(f'Reading stat h5 files to get last update time')
        times = []
        for msid in msids:
            fetch.ft['msid'] = msid
            filename = msid_files['stats'].abs
            logger.debug(f'Reading {filename} to check stat times')
            with tables.open_file(filename, 'r') as h5:
                index = h5.root.data.cols.index[-1]
                times.append((index + 0.5) * STATS_DT[stat])

        # Get the most recent stats data available.  Since these are always updated
        # in lock step we can use the most recent but then go back 5 days to be
        # sure nothing gets missed.
        last_time = max(times)
        last_date_id = get_date_id(DateTime(last_time - 5 * 86400).fits)

    return last_date_id, last_date_id_file


def append_h5_col(opt, msid, vals, logger, msid_files):
    """Append new values to an HDF5 MSID data table.

    :param opt:
    :param msid:
    :param vals: dict with `data`, `quality`, `row0` and `row1` keys
    :param logger:
    :param msid_files:
    """
    n_vals = len(vals['data'])
    fetch.ft['msid'] = msid

    msid_file = Path(msid_files['msid'].abs)
    if not msid_file.exists():
        logger.debug(f'Skipping MSID update no {msid_file}')
        return

    mode = 'r' if opt.dry_run else 'a'
    with tables.open_file(str(msid_file), mode=mode) as h5:
        logger.verbose(f'Appending {n_vals} rows to {msid_file}')

        if vals['row0'] != len(h5.root.data):
            raise ValueError(f'ERROR: unexpected discontinuity '
                             f'row0 {vals["row0"]} != len {len(h5.root.data)}')

        # For the TIME column include special processing to effectively remove
        # existing rows that are superceded by new rows in time.  This is done by
        # marking the TIME value as bad quality.  This process happens regularly
        # for ephemeris content, which gets updated once weekly and has substantial
        # overlaps in the archive data.  Here we only worry about the beginning of
        # new data because anything in the middle will have already been marked
        # bad by update_archive.py.
        if msid == 'TIME':
            time0 = vals['data'][0]
            idx1 = len(h5.root.data) - 1
            ii = 0
            while h5.root.data[idx1 - ii] - time0 > -0.0001:
                h5.root.quality[idx1 - ii] = True
                ii += 1
            if ii > 0:
                logger.verbose(f'Excluded {ii} rows due to overlap')

        if not opt.dry_run:
            h5.root.data.append(vals['data'])
            h5.root.quality.append(vals['quality'])


def main(args=None):
    # Setup for updating the sync repository
    opt = get_options(args)

    basedir = '.' if opt.is_url else opt.data_root
    sync_files = pyyaks.context.ContextDict('update_client_archive.sync_files',
                                            basedir=basedir)
    sync_files.update(file_defs.sync_files)

    # Set up logging
    loglevel = int(opt.log_level)
    logger = pyyaks.logger.get_logger(name='cheta_update_client_archive', level=loglevel,
                                      format="%(asctime)s %(message)s")

    if opt.content:
        contents = opt.content
    else:
        contents = set(fetch.content.values())

    for content in sorted(contents):
        sync_full_archive(opt, sync_files, fetch.msid_files, logger, content)
        for stat in STATS_DT:
            sync_stat_archive(opt, sync_files, fetch.msid_files, logger, content, stat)


if __name__ == '__main__':
    main()
