# Licensed under a 3-clause BSD style license - see LICENSE.rst

import argparse
import contextlib
import os
import re
import sqlite3
from pathlib import Path

import numpy as np
import pyyaks.context
import pyyaks.logger
import tables
from Ska.DBI import DBI
from astropy.table import Table
from astropy.utils.data import download_file

import Ska.engarchive.fetch as fetch
import Ska.engarchive.file_defs as file_defs


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
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Dry run (no actual file or database updatees)")

    opt = parser.parse_args(args)
    opt.is_url = re.match(r'http[s]?://', opt.data_root)

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
        last_row = len(h5.root.data) - 1

    # Look for index table rows that have new data => the row ends after the last existing
    # data.  Note: row0 and row1 correspond to the slice row0:row1, so up to but
    # not including the row indexed row1 (0-based).  So for 3 existing rows,
    # last_row=2 so to get the new row with index=3 you need row1=4.  By def'n
    # we know that row0 <= 3 at this point.
    ok = index_tbl['row1'] >= last_row

    if np.count_nonzero(ok) == 0:
        logger.info(f'No new sync data for {content}')

    index_tbl = index_tbl[ok]

    # List of tables of archfiles rows, one for each row in index_tbl
    archfiles_list = []

    # Iterate over sync files that contain new data
    for date_id, filetime0, filetime1, row0, row1 in index_tbl:
        # File names like sync/acis4eng/2019-07-08T1150z/full.npz
        ft['date_id'] = date_id
        datafile = sync_files['data'].rel

        # Read the file with all the MSID data as a hash with keys like {msid}.data
        # {msid}.quality etc, plus an `archive` key with the table of corresponding
        # archfiles rows.
        with get_readable(opt.data_root, opt.is_url, datafile) as (data_input, uri):
            logger.info(f'Reading update date file {uri}')
            dat = np.load(data_input)

        # Find the MSIDs in this file
        msids = {key[:-5] for key in dat if key.endswith('.data')}

        for msid in msids:
            vals = {}

            for key in ('data', 'quality', 'row0', 'row1'):
                vals[key] = dat[f'{msid}.{key}']

            # If this row begins before then end of current data then chop the
            # beginning of data for this row.
            if vals['row0'] <= last_row:
                idx0 = last_row + 1 - vals['row0']
                logger.debug(f'Chopping {idx0 + 1} rows from data')
                for key in ('data', 'quality'):
                    vals[key] = vals[key][idx0:]
                vals['row0'] += idx0

            append_h5_col(opt, msid, vals, logger, msid_files)

        # Update the archfiles.db3 database to include the associated archive files
        server_file = msid_files['archfiles'].abs
        logger.debug(f'Updating {server_file}')

        with DBI(dbi='sqlite', server=server_file) as db:
            for archfile in dat['archfiles']:
                vals = {name: archfile[name].item() for name in archfile.dtype.names}
                logger.debug(f'Inserting {vals["filename"]}')
                if not opt.dry_run:
                    try:
                        db.insert(vals, 'archfiles')
                    except sqlite3.IntegrityError as err:
                        # Expected exception for archfiles already in the table
                        assert 'UNIQUE constraint failed: archfiles.filename' in str(err)

            if not opt.dry_run:
                db.commit()


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
