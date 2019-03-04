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
    parser.add_argument("--date-now",
                        default=DateTime().date,
                        help="Set effective processing date for testing (default=NOW)")
    parser.add_argument("--max-days",
                        type=float,
                        default=1.5,
                        help="Maximum number of days of files per sync directory")
    parser.add_argument("--data-root",
                        default=".",
                        help="Root directory for sync files")
    parser.add_argument("--content",
                        action='append',
                        help="Content type to process [match regex] (default = all)")
    parser.add_argument("--log-level",
                        help="Logging level")
    return parser.parse_args(args)


def main():
    # Setup for updating the sync repository
    opt = get_options()

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
    if not index_file.exists():
        row0 = create_index_file(index_file, opt, logger)

    print(row0)
    ft['msid'] = '1wrat'
    ft['filetime0'] = '1000'
    ft['filetime1'] = '2000'
    logger.info(str(opt))
    logger.info(f'{sync_files["datadir"].abs}')
    logger.info(f'{fetch.msid_files["msid"].abs}')


def create_index_file(index_file, opt, logger):
    """

    :param index_file: Path of index ECSV file
    :param opt: options
    :return: None
    """
    with Ska.DBI.DBI(dbi='sqlite', server=fetch.msid_files['archfiles'].abs) as dbi:
        archfile1 = dbi.fetchone('select * from archfiles order by filetime desc')
        time0 = archfile1['filetime'] - int(opt.max_days * 86400)
        archfiles = dbi.fetchall(f'select * from archfiles '
                                 f'where filetime > {time0} '
                                 f'order by filetime ')

    row0 = {'filetime0': archfiles[0]['filetime'],
            'filetime1': archfiles[-1]['filetime'],
            'n_archfiles': len(archfiles),
            'date0': archfiles[0]['date'],
            'date1': archfiles[-1]['date'],
            'rowstart': archfiles[0]['rowstart'],
            'rowstop': archfiles[-1]['rowstop']}

    if not index_file.parent.exists():
        logger.info(f'Making directory {index_file.parent}')
        index_file.parent.mkdir(exist_ok=True, parents=True)

    logger.info(f'Writing initial index file {index_file}')
    Table([row0]).write(index_file, format='ascii.ecsv')

    return row0

if __name__ == '__main__':
    main()
