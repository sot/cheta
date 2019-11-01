# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Synchronize local client copy of cheta archive to the server version.

This uses the bundles of sync data that are available on the ICXC server
to update the local HDF5 files that comprise the cheta telemetry archive.
It also updates the archfiles.db3 that serve as a date index for queries.
"""

import argparse
import collections
import contextlib
import getpass
import gzip
import itertools
import os
import shutil
import sys
import pickle
import re
import sqlite3
import urllib
import urllib.error
from fnmatch import fnmatch
from pathlib import Path
import importlib
import time
import signal

import numpy as np
import pyyaks.context
import pyyaks.logger
import tables
from Chandra.Time import DateTime
from Ska.DBI import DBI
from astropy.table import Table
from astropy.utils.data import download_file

from . import file_defs, __version__
from .utils import get_date_id, STATS_DT

sync_files = pyyaks.context.ContextDict('update_client_archive.sync_files')
sync_files.update(file_defs.sync_files)

process_errors = []


def get_options(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync-root",
                        default='https://icxc.cfa.harvard.edu/aspect/cheta/',
                        help=("URL or file dir for sync files to read from "
                              "(default=https://icxc.cfa.harvard.edu/aspect/cheta/)"))
    parser.add_argument("--data-root",
                        help=("Data directory of eng archive data files to update "
                              "(default=usual fetch default)"))
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
    parser.add_argument('--add-msids-from-file',
                        help='Add MSIDs specified in <file> to eng archive data files"')
    parser.add_argument('--server-data-root',
                        help=('Add MSID data from root (/path/to/data, user@remote, '
                              'or user@remote:/path/to/data'))
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=__version__))

    opt = parser.parse_args(args)
    opt.is_url = re.match(r'http[s]?://', opt.sync_root)
    opt.date_stop = DateTime(opt.date_stop)

    return opt


@contextlib.contextmanager
def timing_logger(logger, text, level_pre='info', level_post='info'):
    start = time.time()
    getattr(logger, level_pre)(text)
    yield
    elapsed_time = time.time() - start
    getattr(logger, level_post)(f'  elapsed time: {elapsed_time:.3f} sec')


@contextlib.contextmanager
def get_readable(sync_root, is_url, filename, timeout=30):
    """
    Get readable filename from either a local file or remote URL.

    Returns None for the output filename if input does not exist.

    :param sync_root: str, root directory of sync data (URL or local dir name)
    :param is_url: bool, True if ``sync_root`` is a URL
    :param filename: ContextVal, relative filename
    :param timeout: Download timeout (default=60 sec)
    :return: filename, URI
    """
    filename = str(filename)  # Not needed with pyyaks >= 4.4.

    if is_url:
        uri = sync_root.rstrip('/') + '/' + Path(filename).as_posix()
        try:
            filename = download_file(uri, show_progress=False, cache=False, timeout=timeout)
        except urllib.error.URLError as err:
            raise urllib.error.URLError('Are you on a network with icxc access?') from err

    else:
        uri = Path(sync_root, filename)
        filename = uri.absolute()
        if not uri.exists():
            raise FileNotFoundError(str(uri))

    try:
        yield filename, uri
    finally:
        if is_url and filename is not None:
            # Clean up tmp file
            os.unlink(filename)


class DelayedKeyboardInterrupt(object):
    """Delay keyboard interrupt while critical operation finishes.

    Taken from https://stackoverflow.com/questions/842557/
    how-to-prevent-a-block-of-code-from-being-interrupted-by-keyboardinterrupt-in-py/21919644
    """
    def __init__(self, logger):
        self.logger = logger
        self.signal_received = False

    def __enter__(self):
        self.old_handler = signal.signal(signal.SIGINT, self.handler)

    def handler(self, sig, frame):
        self.signal_received = (sig, frame)
        self.logger.info('KEYBOARD INTERRUPT RECEIVED. Please hold tight for moment while we '
                         'finish up cleanly, otherwise the archive may get corrupted.')

    def __exit__(self, typ, value, traceback):
        signal.signal(signal.SIGINT, self.old_handler)
        if self.signal_received:
            print('Shutting down due to keyboard interrupt', file=sys.stderr)
            sys.exit(1)


def add_msids_from_file(opt, logger):
    msids, msids_content = get_msids_for_add_msids_from_file(opt, logger)
    copy_files = get_copy_files(logger, msids, msids_content)
    if '@' in opt.server_data_root:
        copy_server_files_ssh(opt, logger, copy_files)
    else:
        copy_server_files(opt, logger, copy_files, opt.server_data_root, copy_func=shutil.copyfile)


def copy_server_files(opt, logger, copy_files, server_path, copy_func):
    from astropy.utils.console import ProgressBar

    logger.info(f'Copying {len(copy_files)} files from {opt.server_data_root} to {opt.data_root}')
    with ProgressBar(len(copy_files)) as bar:
        for copy_file in copy_files:
            bar.update()
            local_file = Path(opt.data_root, copy_file)
            server_file = Path(server_path, copy_file)
            local_file.parent.mkdir(parents=True, exist_ok=True)
            with DelayedKeyboardInterrupt(logger):
                copy_func(str(server_file), str(local_file))


def copy_server_files_ssh(opt, logger, copy_files):
    import paramiko

    match = re.match(r'(\w+)@([\w.]+)(:.+)?', opt.server_data_root)
    if not match:
        raise ValueError(f'could not parse {opt.server_data_root} into username@host:path')
    username, hostname, server_path = match.groups()
    server_path = server_path or '/proj/sot/ska/data/eng_archive'

    password = getpass.getpass(f'Password for {username}@{hostname}: ')

    logger.info(f'Connecting to {hostname}')
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=hostname,
                       username=username,
                       password=password)
    ftp_client = ssh_client.open_sftp()
    copy_server_files(opt, logger, copy_files, server_path, copy_func=ftp_client.get)
    ftp_client.close()
    ssh_client.close()


def get_copy_files(logger, msids, msids_content):
    logger.info('Searching for missing archive files')
    msid_files = fetch.msid_files
    basedir = msid_files.basedir
    ft = fetch.ft
    copy_files = set()
    for msid in msids:
        ft['content'] = msids_content[msid]
        copy_specs = [(msid, None, 'msid'),
                      (msid, None, 'archfiles'),
                      (msid, None, 'colnames'),
                      (msid, '5min', 'stats'),
                      (msid, 'daily', 'stats'),
                      ('TIME', None, 'msid')]
        for ft_msid, interval, filetype in copy_specs:
            ft['msid'] = ft_msid
            ft['interval'] = interval
            pth = Path(msid_files[filetype].abs)
            if not pth.exists():
                copy_files.add(str(pth.relative_to(basedir)))

    return sorted(copy_files)


def get_msids_for_add_msids_from_file(opt, logger):
    # Get global list of MSIDs
    logger.info(f'Reading available cheta archive MSIDs from {opt.sync_root}')
    with get_readable(opt.sync_root, opt.is_url, sync_files['msid_contents']) as (tmpfile, uri):
        if tmpfile is None:
            # If index_file is not found then get_readable returns None
            logger.info(f'No cheta MSIDs list file found at{uri}')
            return None
        logger.info(f'Reading cheta MSIDs list file {uri}')
        msids_content = pickle.load(gzip.open(tmpfile, 'rb'))

    content_msids = collections.defaultdict(list)
    for msid, content in msids_content.items():
        content_msids[content].append(msid)

    logger.info(f'Reading MSID specs from {opt.add_msids_from_file}')
    with open(opt.add_msids_from_file) as fh:
        lines = [line.strip() for line in fh.readlines()]
    msid_specs = [line.upper() for line in lines if (line and not line.startswith('#'))]

    logger.info('Assembling list of MSIDs that match MSID specs')
    msids_out = []
    for msid_spec in msid_specs:
        if msid_spec.startswith('**/'):
            msid_spec = msid_spec[3:]
            content = msids_content[msid_spec]
            subsys = re.match(r'([^\d]+)\d', content).group(1)
            for content, msids in content_msids.items():
                if content.startswith(subsys):
                    logger.info(f'Found {len(msids)} MSIDs from content = {content}')
                    msids_out.extend(msids)

        elif msid_spec.startswith('*/'):
            msid_spec = msid_spec[2:]
            content = msids_content[msid_spec]
            msids = content_msids[content]
            logger.info(f'Found {len(msids)} MSIDs from content = {content}')
            msids_out.extend(msids)

        else:
            msids_out.extend([msid for msid in msids_content if fnmatch(msid, msid_spec)])
    logger.info(f'Found {len(msids_out)} matching MSIDs total')

    return msids_out, msids_content


def sync_full_archive(opt, msid_files, logger, content, index_tbl):
    """
    Sync the archive for ``content``.

    :param opt:
    :param msid_files:
    :param logger:
    :param content:
    :param index_tbl: index of sync file entries
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

    try:
        dats = get_full_data_sets(ft, index_tbl, logger, opt)
    except urllib.error.URLError as err:
        if 'timed out' in str(err):
            msg = f'  ERROR: timed out getting full data for {content}'
            logger.error(msg)
            process_errors.append(msg)
            dats = []
        else:
            raise

    if dats:
        dat, msids = concat_data_sets(dats, ['data', 'quality'])
        with DelayedKeyboardInterrupt(logger):
            update_full_h5_files(dat, logger, msid_files, msids, opt)
            update_full_archfiles_db3(dat, logger, msid_files, opt)


def update_full_archfiles_db3(dat, logger, msid_files, opt):
    # Update the archfiles.db3 database to include the associated archive files
    server_file = msid_files['archfiles'].abs
    logger.debug(f'Updating {server_file}')

    def as_python(val):
        try:
            return val.item()
        except AttributeError:
            return val

    with timing_logger(logger, f'Updating {server_file}', 'info', 'info'):
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


def update_full_h5_files(dat, logger, msid_files, msids, opt):
    with timing_logger(logger, f'Applying updates to {len(msids)} h5 files',
                       'info', 'info'):
        for msid in msids:
            vals = {key: dat[f'{msid}.{key}'] for key in ('data', 'quality', 'row0', 'row1')}
            append_h5_col(opt, msid, vals, logger, msid_files)


def get_full_data_sets(ft, index_tbl, logger, opt):
    # Iterate over sync files that contain new data
    dats = []
    for date_id, filetime0, filetime1, row0, row1 in index_tbl:
        # Limit processed archfiles by date
        if filetime0 > DateTime(opt.date_stop).secs:
            break

        # File names like sync/acis4eng/2019-07-08T1150z/full.npz
        ft['date_id'] = date_id

        # Read the file with all the MSID data as a hash with keys like {msid}.data
        # {msid}.quality etc, plus an `archive` key with the table of corresponding
        # archfiles rows.
        with get_readable(opt.sync_root, opt.is_url, sync_files['data']) as (data_input, uri):
            with timing_logger(logger, f'Reading update date file {uri}'):
                with gzip.open(data_input, 'rb') as fh:
                    dats.append(pickle.load(fh))
    return dats


def sync_stat_archive(opt, msid_files, logger, content, stat, index_tbl):
    """
    Sync the archive for ``content``.

    :param opt:
    :param msid_files:
    :param logger:
    :param content:
    :param stat: stat interval '5min' or 'daily'
    :param index_tbl: table of sync file entries
    :return:
    """
    # Get the last row of data from the length of the TIME.col (or archfiles?)
    ft = fetch.ft
    ft['content'] = content
    ft['interval'] = stat

    stats_dir = Path(msid_files['statsdir'].abs)
    if not stats_dir.exists():
        logger.debug(f'Skipping {stat} data for {content}: no directory')
        return

    logger.info('')
    logger.info(f'Processing {stat} data for {content}')

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

    # Get list of applicable dat objects (new data, before opt.date_stop).  Also
    # return ``date_id`` which is the date_id of the final data set in the list.
    # This will be written as the new ``last_date_id``.
    try:
        dats, date_id = get_stat_data_sets(ft, index_tbl, last_date_id, logger, opt)
    except urllib.error.URLError as err:
        if 'timed out' in str(err):
            msg = f'  ERROR: timed out getting {stat} data for {content}'
            logger.error(msg)
            process_errors.append(msg)
            return
        else:
            raise

    if not dats:
        return

    dat, msids = concat_data_sets(dats, ['data'])
    with DelayedKeyboardInterrupt(logger):
        with timing_logger(logger, f'Applying updates to {len(msids)} h5 files'):
            for msid in msids:
                fetch.ft['msid'] = msid
                stat_file = msid_files['stats'].abs
                if os.path.exists(stat_file):
                    append_stat_col(dat, stat_file, msid, date_id, opt, logger)

            logger.debug(f'Updating {last_date_id_file} with {date_id}')
            with open(last_date_id_file, 'w') as fh:
                fh.write(f'{date_id}')


def get_stat_data_sets(ft, index_tbl, last_date_id, logger, opt):
    # Iterate over sync files that contain new data
    dats = []
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
        last_date_id = ft['date_id'] = date_id

        # Read the file with all the MSID data as a hash with keys {msid}.data
        # {msid}.row0, {msid}.row1
        with get_readable(opt.sync_root, opt.is_url, sync_files['data']) as (data_input, uri):
            with timing_logger(logger, f'Reading update date file {uri}'):
                with gzip.open(data_input, 'rb') as fh:
                    dat = pickle.load(fh)
                    if dat:
                        # Stat pickle dict can be empty, e.g. in the case of a daily file
                        # with no update.
                        dats.append(dat)

    return dats, last_date_id


def concat_data_sets(dats, data_keys):
    """
    Concatenate the list of ``dat`` dicts into a single such dict

    Each dat dict has keys {msid}.{key} for key in data, row0, row1.
    The ``.data`` elements are numpy structured arrays, while ``.row0`` and
    ``.row1`` are integers.

    :param dats: list of dict
    :param data_keys: list of data keys (e.g. ['data', 'quality'])
    :return: dict, concatenated version
    """
    dat_lists = collections.defaultdict(list)
    for dat in dats:
        for key, val in dat.items():
            dat_lists[key].append(val)

    msids = {key[:-5] for key in dat_lists if key.endswith('.data')}

    dat = {}
    for msid in msids:
        lens = set()
        lens.add(len(dat_lists[f'{msid}.row0']))
        lens.add(len(dat_lists[f'{msid}.row1']))
        for key in data_keys:
            lens.add(len(dat_lists[f'{msid}.{key}']))
        if len(lens) != 1:
            raise ValueError('inconsistency in lengths of data file inputs')

        for row1, next_row0 in zip(dat_lists[f'{msid}.row1'][:-1],
                                   dat_lists[f'{msid}.row0'][1:]):
            if row1 != next_row0:
                raise ValueError('unexpected inconsistency in rows in data files')

        dat[f'{msid}.row0'] = dat_lists[f'{msid}.row0'][0]
        dat[f'{msid}.row1'] = dat_lists[f'{msid}.row1'][-1]
        for key in data_keys:
            dat[f'{msid}.{key}'] = np.concatenate(dat_lists[f'{msid}.{key}'])

    if 'archfiles' in dats[0]:
        dat['archfiles'] = list(itertools.chain.from_iterable(
            dat['archfiles'] for dat in dats))

    return dat, msids


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
            raise ValueError(f'ERROR: unexpected discontinuity for stat msid={msid} '
                             f'content={fetch.ft["content"]}\n'
                             f'Looks like your archive is in a bad state, CONTACT '
                             f'your local Ska expert with this info:\n'
                             f'  First row0 in new data {vals["row0"]} != '
                             f'length of existing data {len(h5.root.data)}')

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
    last_date_id_file = msid_files['last_date_id'].abs

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

        # Get the least recent stats data available and then go back 5 days to be
        # sure nothing gets missed.  Except for ephemeris files that are weird:
        # when they appear in the archive they include weeks of data in the past
        # and possibly future data.
        last_time = min(times)
        lookback = 30 if re.search(r'ephem[01]$', fetch.ft['content'].val) else 5
        last_date_id = get_date_id(DateTime(last_time - lookback * 86400).fits)

    return last_date_id, last_date_id_file


def append_h5_col(opt, msid, vals, logger, msid_files):
    """Append new values to an HDF5 MSID data table.

    :param opt:
    :param msid:
    :param vals: dict with `data`, `quality`, `row0` and `row1` keys
    :param logger:
    :param msid_files:
    """
    fetch.ft['msid'] = msid

    msid_file = Path(msid_files['msid'].abs)
    if not msid_file.exists():
        logger.debug(f'Skipping MSID update no {msid_file}')
        return

    mode = 'r' if opt.dry_run else 'a'
    with tables.open_file(str(msid_file), mode=mode) as h5:
        # If the vals[] data begins before then end of current data then chop the
        # beginning of data for this row.
        last_row_idx = len(h5.root.data) - 1
        if vals['row0'] <= last_row_idx:
            idx0 = last_row_idx + 1 - vals['row0']
            logger.debug(f'Chopping {idx0 + 1} rows from data')
            for key in ('data', 'quality'):
                vals[key] = vals[key][idx0:]
            vals['row0'] += idx0

        n_vals = len(vals['data'])
        logger.verbose(f'Appending {n_vals} rows to {msid_file}')

        # Normally at this point there is always data to append since we got here
        # by virtue of the TIME.h5 file being incomplete relative to available sync
        # data.  However, user might have manually rsynced a file as part of adding
        # a new MSID, in which case it might be up to date and there is no req'd action.
        if n_vals == 0:
            return

        if vals['row0'] != len(h5.root.data):
            raise ValueError(f'ERROR: unexpected discontinuity for full msid={msid} '
                             f'content={fetch.ft["content"]}\n'
                             f'Looks like your archive is in a bad state, CONTACT '
                             f'your local Ska expert with this info:\n'
                             f'  First row0 in new data {vals["row0"]} != '
                             f'length of existing data {len(h5.root.data)}')

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


def get_index_tbl(content, logger, opt):
    # Read the index file to know what is available for new data
    with get_readable(opt.sync_root, opt.is_url, sync_files['index']) as (index_input, uri):
        if index_input is None:
            # If index_file is not found then get_readable returns None
            logger.info(f'No new sync data for {content}: {uri} not found')
            return None
        logger.info(f'Reading index file {uri}')
        index_tbl = Table.read(index_input, format='ascii.ecsv')
    return index_tbl


def main(args=None):
    global fetch  # fetch module, see below

    # Setup for updating the sync repository
    opt = get_options(args)

    # Set up logging
    loglevel = int(opt.log_level)
    logger = pyyaks.logger.get_logger(name='cheta_update_client_archive', level=loglevel,
                                      format="%(asctime)s %(message)s")

    # If --data-root is supplied then set the fetch msid_files basedir via ENG_ARCHIVE
    # prior to importing fetch.  This ensures that ``content`` is consistent with
    # the destination archive.
    if opt.data_root is not None:
        if not Path(opt.data_root).exists():
            raise FileNotFoundError(
                f'local cheta archive directory {Path(opt.data_root).absolute()} not found')
        os.environ['ENG_ARCHIVE'] = opt.data_root

    fetch = importlib.import_module('.fetch', __package__)

    # Turn things around and define data_root based on fetch, relying on it to
    # find the archive if --data-root is not specified.
    opt.data_root = fetch.msid_files.basedir

    logger.info(f'Running cheta_update_client_archive version {__version__}')
    logger.info(f'  {__file__}')
    logger.info('')
    logger.info(f'Updating client archive at {fetch.msid_files.basedir}')

    if opt.add_msids_from_file:
        add_msids_from_file(opt, logger)
        return

    if opt.content:
        contents = opt.content
    else:
        # fetch.content is a dict of {MSID: content_type} values
        contents = set(fetch.content.values())

    # Global list of timeout errors
    process_errors.clear()

    for content in sorted(contents):
        fetch.ft['content'] = content
        index_tbl = get_index_tbl(content, logger, opt)
        if index_tbl is not None:
            sync_full_archive(opt, fetch.msid_files, logger, content, index_tbl)
            for stat in STATS_DT:
                sync_stat_archive(opt, fetch.msid_files, logger, content, stat, index_tbl)

    if process_errors:
        logger.error('')
        logger.error('TIMEOUT ERRORS:')

    for process_error in process_errors:
        logger.error(process_error)


if __name__ == '__main__':
    main()
