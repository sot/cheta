import argparse
from pathlib import Path

import pyyaks.context
import pyyaks.logger
from Chandra.Time import DateTime
import Ska.DBI
from astropy.table import Table

import Ska.engarchive.fetch as fetch
import Ska.engarchive.file_defs as file_defs


def get_options(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Dry run (no actual file or database updatees)")
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


def get_row_from_archfiles(archfiles):
    row = {'filetime0': archfiles[0]['filetime'],
           'filetime1': archfiles[-1]['filetime'],
           'n_archfiles': len(archfiles),
           'date0': archfiles[0]['date'],
           'date1': archfiles[-1]['date'],
           'rowstart': archfiles[0]['rowstart'],
           'rowstop': archfiles[-1]['rowstop']}
    return row


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
    with Ska.DBI.DBI(dbi='sqlite', server=fetch.msid_files['archfiles'].abs) as dbi:
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

    logger.info(f'Writing {len(rows)} row(s) to index file {index_file}')
    index_tbl.write(index_file, format='ascii.ecsv')

    return index_tbl

def update_sync_data(opt, sync_files, logger, row, stat):
    """

    :param opt:
    :param sync_files:
    :param logger:
    :param row:
    :param stat:
    :return:
    """
    pass


def update_sync_repo(opt, sync_files, logger, content):
    """

    :param opt: argparse options
    :param msid_files: MSID files context dict
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

    if index_tbl is not None:
        for row in index_tbl:
            for stat in ('full', '5min', 'daily'):
                update_sync_data(opt, sync_files, logger, row, stat)


if __name__ == '__main__':
    main()
