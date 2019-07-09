# Licensed under a 3-clause BSD style license - see LICENSE.rst

import argparse
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
    parser.add_argument("--log-level",
                        help="Logging level")
    return parser.parse_args(args)


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
    time_file = Path(sync_files['msid'].abs)
    if not time_file.exists():
        logger.debug('Skipping full data for {content}: no {time_file} file')
        return

    logger.info(f'Processing full data for {content}')

    # Get the 0-based index of last available full data row
    with tables.open_file(time_file, 'r') as h5:
        last_row = len(h5.root.data) - 1

    # Read the index file to know what is available for new data
    index_file = sync_files['index'].abs
    index_tbl = Table.read(index_file)

    # Look for index table rows that have new data => the row ends after the last existing
    # data.  Note: row0 and row1 correspond to the slice row0:row1, so up to but
    # not including the row indexed row1 (0-based).  So for 3 existing rows,
    # last_row=2 so to get the new row with index=3 you need row1=4.  By def'n
    # we know that row0 <= 3 at this point.
    ok = index_tbl['row1'] >= last_row

    if np.count_nonzero(ok) == 0:
        logger.info(f'No new sync data for {content}')

    index_tbl = index_tbl[ok]

    # Iterate over sync files that contain new data
    for filetime0, filetime1, date_id, row0, row1 in index_tbl:
        ft['date_id'] = date_id
        # File names like sync/acis4eng/2019-07-08T1150z/full.npz
        datafile = sync_files['data'].abs

        # Read the file with all the MSID data as a hash with keys like {msid}.data
        # {msid}.quality etc, plus an `archive` key with the table of corresponding
        # archfiles rows.
        dat = np.load(datafile)

        # Find the MSIDs in this file
        msids = {key[:-5] for key in dat if key.endswith('.data')}

        keys = ('data', 'quality', 'row0', 'row1')
        vals = {}

        for msid in msids:
            for key in keys:
                vals[key] = dat[f'{msid}.{key}']

            # If this row begins before then end of current data then chop the
            # beginning of data for this row.
            if vals['row0'] <= last_row:
                idx0 = last_row + 1 - vals['row0']
                logger.debug(f'Chopping {idx0 + 1} rows from data')
                for key in ('data', 'quality'):
                    vals[key] = vals[key][idx0:]
                vals['row0'] += idx0

            append_h5_col(vals, logger, msid_files)


def append_h5_col(vals, logger, msid_files):
    """Append new values to an HDF5 MSID data table.

    :param vals: dict with `data`, `quality`, `row0` and `row1` keys
    :param logger:
    :param msid_files:
    """
    n_vals = len(vals['data'])

    msid_file = Path(msid_files['msid'].abs)
    if not msid_file.exists():
        logger.debug('Skipping MSID update no {msid_file}')
        return

    with tables.open_file(msid_file, mode='a') as h5:
        logger.verbose(f'Appending {n_vals} rows to {msid_file}')

        if vals['row0'] != len(h5.root.data):
            raise ValueError('ERROR: ')

        # h5.root.data.append(vals['data'])
        # h5.root.quality.append(vals['quality'])


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

    for content in contents:
        sync_full_archive(opt, sync_files, fetch.msid_files, logger, content)
