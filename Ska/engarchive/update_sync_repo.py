import argparse
import gzip
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
                        help="Root directory for sync files")
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
        update_sync_repo(opt, sync_files, logger, content)


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
    ft['interval'] = 'full'

    index_file = Path(sync_files['index'].abs)
    index_tbl = update_index_file(index_file, opt, logger)

    if index_tbl is None:
        # Index table was not created, nothing more to do here
        logger.warning(f'No index table for {content}')
        return

    for row in index_tbl:
        update_sync_data_full(content, sync_files, logger, row)

        for stat in ('full', '5min', 'daily'):
            update_sync_data_stat(content, sync_files, logger, row, stat)


def get_row_from_archfiles(archfiles):
    row = {'filetime0': archfiles[0]['filetime'],
           'filetime1': archfiles[-1]['filetime'],
           'date0': archfiles[0]['date'],
           'rowstart': archfiles[0]['rowstart'],
           'rowstop': archfiles[-1]['rowstop']}
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
        if row0['rowstop'] != row1['rowstart']:
            msg = f'rows not contiguous at table date0={index_tbl["date0"][idx]}'
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
    ft['rowstart'] = row['rowstart']
    ft['rowstop'] = row['rowstop']
    ft['interval'] = 'full'

    outfile = Path(sync_files['data'].abs)
    if outfile.exists():
        logger.debug(f'Skipping {outfile}, already exists')
        return

    out = {}
    msids = list(fetch.all_colnames[content]) + ['TIME']

    for msid in msids:
        ft['msid'] = msid
        with tables.open_file(fetch.msid_files['msid'].abs) as h5:
            out[f'{msid}.quality'] = h5.root.quality[row['rowstart']:row['rowstop']]
            out[f'{msid}.data'] = h5.root.data[row['rowstart']:row['rowstop']]

    n_rows = row['rowstop'] - row['rowstart']
    n_msids = len(msids)
    logger.info(f'Writing {outfile} with {n_rows} of data and {n_msids} msids')

    outfile.parent.mkdir(exist_ok=True, parents=True)
    # TODO: increase compression to max (gzip?)
    np.savez_compressed(outfile, **out)


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
    pass


if __name__ == '__main__':
    main()
