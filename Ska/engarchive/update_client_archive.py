# Licensed under a 3-clause BSD style license - see LICENSE.rst

import argparse
import contextlib
import gzip
import os
import pickle
import re
import sqlite3
from pathlib import Path

import numpy as np
import pyyaks.context
import pyyaks.logger
import tables
from Chandra.Time import DateTime
from Ska.DBI import DBI
from astropy.table import Table
from astropy.utils.data import download_file

import Ska.engarchive.fetch as fetch
import Ska.engarchive.file_defs as file_defs
from Ska.engarchive.utils import get_date_id

STATS_DT = {'5min': 328,
            'daily': 86400}


def get_options(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root",
                        default='https://icxc.cfa.harvard.edu/aspect/cheta/',
                        help="URL for sync files")
    parser.add_argument("--content",
                        action='append',
                        help="Content type to process [match regex] (default = all)")
    parser.add_argument("--log-level",
                        default=1,
                        help="Logging level")
    parser.add_argument("--date-stop",
                        help="Stop process date (mostly for testing, default=NOW)")
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Dry run (no actual file or database updatees)")

    opt = parser.parse_args(args)
    opt.is_url = re.match(r'http[s]?://', opt.data_root)
    opt.date_stop = DateTime(opt.date_stop)

    return opt


@contextlib.contextmanager
def get_readable(data_root, is_url, filename):
    if is_url:
        uri = data_root.rstrip('/') + '/' + filename
        filename = download_file(uri, show_progress=False, cache=False, timeout=60)
    else:
        uri = filename

    try:
        yield filename, uri
    finally:
        if is_url:
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
        logger.info(f'No new sync data for {content}')

    index_tbl = index_tbl[ok]

    # List of tables of archfiles rows, one for each row in index_tbl
    archfiles_list = []

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
            vals = {}

            for key in ('data', 'quality', 'row0', 'row1'):
                vals[key] = dat[f'{msid}.{key}']

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

    stats_dir = Path(msid_files['statsdir'])
    if not stats_dir.exists():
        logger.debug('Skipping {stat} data for {content}: no directory')
        return

    logger.info('')
    logger.info(f'Processing {stat} data for {content}')

    # Read the index file to know what is available for new data
    # TODO: factor this out
    index_file = sync_files['index'].rel
    with get_readable(opt.data_root, opt.is_url, index_file) as (index_input, uri):
        logger.info(f'Reading index file {uri}')
        index_tbl = Table.read(index_input, format='ascii.ecsv')

    # Get the MSIDs that are in client archive
    msids = [str(fn)[:-3] for fn in stats_dir.glob('*.h5')]
    if not msids:
        logger.debug('Skpping {stat} data for {content}: no stats h5 files')

    last_date_id, last_date_id_file = get_last_date_id(
        msid_files, msids, stat)

    # Iterate over sync files that contain new data
    for date_id, filetime0, filetime1, row0, row1 in index_tbl:
        # Limit processed archfiles by date
        if filetime0 > DateTime(opt.date_stop).secs:
            logger.debug(f'Index {date_id} filetime0 > date_stop, breaking')
            break

        # Compare date_id of this row to last one that was processed.  These
        # are lexically ordered
        if date_id < last_date_id:
            logger.debug(f'Index {date_id} already processed, skipping')
            continue

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
            vals = {}

            for key in ('data', 'row0', 'row1'):
                vals[key] = dat[f'{msid}.{key}']

            with tables.open_file(msid_files['stat'], 'a') as h5:
                last_row_idx = len(h5.root.data) - 1

                # If this row begins before then end of current data then chop the
                # beginning of data for this row.
                if vals['row0'] <= last_row_idx:
                    idx0 = last_row_idx + 1 - vals['row0']
                    logger.debug(f'Chopping {idx0 + 1} rows from data')
                    for key in ('data', 'quality'):
                        vals[key] = vals[key][idx0:]
                    vals['row0'] += idx0

                append_h5_col(opt, msid, vals, logger, msid_files)

        with open(last_date_id_file, 'w') as fh:
            fh.write(f'{last_date_id:.3f}')


def get_last_date_id(msid_files, msids, stat):
    last_date_id_file = msid_files['last_date_id'].rel

    if Path(last_date_id_file).exists():
        with open(last_date_id_file, 'r') as fh:
            last_date_id = fh.read()
    else:
        times = []
        for msid in msids:
            fetch.ft['msid'] = msid
            with tables.open_file(msid_files['stats'].rel, 'r') as h5:
                index = h5.root.data.cols.index[-1]
                times.append((index + 0.5) * STATS_DT[stat])

        # Get the most recent stats data available.  Since these are always updated
        # in lock step we can use the most recent but then go back 2.5 days to be
        # sure nothing gets missed.
        last_time = max(times)
        last_date_id = get_date_id(DateTime(last_time - 86400).fits)

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
        logger.debug('Skipping MSID update no {msid_file}')
        return

    with tables.open_file(str(msid_file), mode='a') as h5:
        logger.verbose(f'Appending {n_vals} rows to {msid_file}')

        if vals['row0'] != len(h5.root.data):
            raise ValueError('ERROR: ')

        if not opt.dry_run:
            h5.root.data.append(vals['data'])
            h5.root.quality.append(vals['quality'])


def main(args=None):
    # Setup for updating the sync repository
    opt = get_options(args)

    basedir = '.' if opt.is_url else opt.data_root
    sync_files = pyyaks.context.ContextDict('update_sync_repo.sync_files',
                                            basedir=basedir)
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
        sync_full_archive(opt, sync_files, fetch.msid_files, logger, content)


if __name__ == '__main__':
    main()
