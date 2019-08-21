import os
import pickle
import shutil
from pathlib import Path

import pytest
import numpy as np
import Ska.DBI
import tables
from Chandra.Time import DateTime

from .. import fetch
from .. import update_client_archive, update_server_sync
from ..utils import STATS_DT, set_fetch_basedir

# Covers safe mode and IRU swap activities around 2018:283.  This is a time
# with rarely-seen telemetry.
START, STOP = '2018:281', '2018:293'

# Content types and associated MSIDs that will be tested
CONTENTS = {'acis4eng': ['1WRAT'],  # [float]
            'dp_pcad32': ['DP_SYS_MOM_TOT'],  # Derived parameter [float]
            'orbitephem0': ['ORBITEPHEM0_X'],  # Heavily overlapped [float]
            'cpe1eng': ['6GYRCT1', '6RATE1'],  # Safe mode, [int, float]
            'pcad13eng': ['ASPAGYC2A'],  # PCAD subformat and rarely sampled [int]
            'sim_mrg': ['3TSCMOVE', '3TSCPOS'],  # [str, float]
            'simcoor': ['SIM_Z_MOVED'],  # [bool]
            }

LOG_LEVEL = 50  # quiet


def make_linked_local_archive(outdir, content, msids):
    """
    Create a hard-link version of archive containing only
    necessary files.  In this way the sync repo creation is done
    for only required MSIDs.

    :param content: content type
    :param msids: list of MSIDs in that content type
    :param outdir: temporary output directory
    :return: None
    """

    basedir_in = Path(fetch.msid_files.basedir) / 'data'
    # Was: Path(os.environ['SKA']) / 'data' / 'eng_archive' / 'data' but that
    # doesn't respect possible ENG_ARCHIVE override

    basedir_out = Path(outdir) / 'data'
    if basedir_out.exists():
        shutil.rmtree(basedir_out)

    (basedir_out / content).mkdir(parents=True)
    (basedir_out / content / '5min').mkdir()
    (basedir_out / content / 'daily').mkdir()
    for file in 'archfiles.db3', 'colnames.pickle', 'TIME.h5':
        shutil.copy(basedir_in / content / file,
                    basedir_out / content / file)
    for msid in msids:
        file = f'{msid}.h5'
        try:
            os.link(basedir_in / content / file,
                    basedir_out / content / file)
        except OSError:
            os.symlink(basedir_in / content / file,
                       basedir_out / content / file)
        try:
            os.link(basedir_in / content / '5min' / file,
                    basedir_out / content / '5min' / file)
        except OSError:
            os.symlink(basedir_in / content / '5min' / file,
                       basedir_out / content / '5min' / file)
        try:
            os.link(basedir_in / content / 'daily' / file,
                    basedir_out / content / 'daily' / file)
        except OSError:
            os.symlink(basedir_in / content / 'daily' / file,
                       basedir_out / content / 'daily' / file)


def make_sync_repo(outdir, content):
    """Create a new sync repository with data root ``outdir`` (which is
    assumed to be clean).

    This also assumes the correct fetch.msid_files.basedir is set to point at
    a copy of the cheta archfile that contains requisite data.
    """
    date_start = (DateTime(START) - 8).date
    date_stop = (DateTime(STOP) + 2).date

    print(f'Updating server sync for {content}')
    args = [f'--sync-root={outdir}',
            f'--date-start={date_start}',
            f'--date-stop={date_stop}',
            f'--log-level={LOG_LEVEL}',
            f'--content={content}']

    update_server_sync.main(args)


def make_stub_archfiles(date, basedir_ref, basedir_stub):
    archfiles_def = (Path(fetch.__file__).parent / 'archfiles_def.sql').read_text()

    with set_fetch_basedir(basedir_ref):
        filename = fetch.msid_files['archfiles'].abs

    with Ska.DBI.DBI(dbi='sqlite', server=filename) as db:
        filetime = DateTime(date).secs
        # Last archfile that starts before date.
        last_row = db.fetchone(f'select * from archfiles '
                               f'where filetime < {filetime} '
                               f'order by filetime desc'
                              )

    with set_fetch_basedir(basedir_stub):
        filename = fetch.msid_files['archfiles'].abs
    if os.path.exists(filename):
        os.unlink(filename)

    with Ska.DBI.DBI(dbi='sqlite', server=filename, autocommit=False) as db:
        db.execute(archfiles_def)
        db.insert(last_row, 'archfiles')
        db.commit()

    return last_row['rowstart'], last_row['rowstop']


def make_stub_stats_col(msid, stat, row1, basedir_ref, basedir_stub, date_stop):
    # Max allowed tstop.
    tstop = DateTime(date_stop).secs

    with set_fetch_basedir(basedir_ref):
        fetch.ft['msid'] = 'TIME'
        file_time = fetch.msid_files['msid'].abs

        fetch.ft['msid'] = msid
        fetch.ft['interval'] = stat
        file_stats_ref = fetch.msid_files['stats'].abs

    if not Path(file_stats_ref).exists():
        return

    with set_fetch_basedir(basedir_stub):
        file_stats_stub = fetch.msid_files['stats'].abs

    with tables.open_file(file_time, 'r') as h5:
        # Pad out tstop by DT in order to be sure that all records before a long
        # gap get found.  This comes into play for pcad13eng which is in PCAD subformat only.
        # In addition, do not select data beyond tstop (date_stop), which is the
        # stub file end time.  This is mostly for ephemeris data, where one archfile covers
        # many weeks (6?) of data.
        tstop = min(h5.root.data[row1 - 1] + STATS_DT[stat], tstop)
        # Need at least 10 days of real values in stub file to start sync
        tstart = tstop - 10 * 86400

    with tables.open_file(file_stats_ref, 'r') as h5:
        tbl = h5.root.data
        times = (tbl.col('index') + 0.5) * STATS_DT[stat]
        stat_row0, stat_row1 = np.searchsorted(times, [tstart, tstop])
        # Back up a bit to ensure getting something since an MSID that is not
        # typically sampled (because of subformat for instance) may show up
        # in full data with quality=True everywhere
        # and thus have no stats samples.
        stat_row0 -= 5
        tbl_rows = np.zeros(stat_row1, dtype=tbl.dtype)
        tbl_rows[stat_row0:stat_row1] = tbl[stat_row0:stat_row1]
        # returns np.ndarray (structured array)

    Path(file_stats_stub).parent.mkdir(exist_ok=True, parents=True)

    filters = tables.Filters(complevel=5, complib='zlib')
    with tables.open_file(file_stats_stub, mode='a', filters=filters) as stats:
        stats.create_table(stats.root, 'data', tbl_rows,
                           f'{stat} sampling', expectedrows=1e5)
        stats.root.data.flush()


def make_stub_h5_col(msid, row0, row1, basedir_ref, basedir_stub):
    fetch.ft['msid'] = msid

    with set_fetch_basedir(basedir_ref):
        file_ref = fetch.msid_files['data'].abs

    if not Path(file_ref).exists():
        return

    with tables.open_file(file_ref, 'r') as h5:
        data_stub = h5.root.data[row0:row1]
        qual_stub = h5.root.quality[row0:row1]
        n_rows = len(h5.root.data)

    data_fill = np.zeros(row0, dtype=data_stub.dtype)
    qual_fill = np.ones(row0, dtype=qual_stub.dtype)  # True => bad

    with set_fetch_basedir(basedir_stub):
        file_stub = fetch.msid_files['data'].abs

    if os.path.exists(file_stub):
        os.unlink(file_stub)

    filters = tables.Filters(complevel=5, complib='zlib')
    with tables.open_file(file_stub, mode='w', filters=filters) as h5:
        h5shape = (0,) + data_stub.shape[1:]
        h5type = tables.Atom.from_dtype(data_stub.dtype)
        h5.create_earray(h5.root, 'data', h5type, h5shape, title=msid,
                         expectedrows=n_rows)
        h5.create_earray(h5.root, 'quality', tables.BoolAtom(), (0,), title='Quality',
                         expectedrows=n_rows)

    with tables.open_file(file_stub, mode='a') as h5:
        h5.root.data.append(data_fill)
        h5.root.data.append(data_stub)
        h5.root.quality.append(qual_fill)
        h5.root.quality.append(qual_stub)


def make_stub_colnames(basedir_ref, basedir_stub):
    """
    Copy colnames.pickle to the stub dir.  Also get the list of MSIDs that are
    actually in the reference archive.
    """
    with set_fetch_basedir(basedir_ref):
        file_ref = fetch.msid_files['colnames'].abs

    with set_fetch_basedir(basedir_stub):
        file_stub = fetch.msid_files['colnames'].abs

    shutil.copy(file_ref, file_stub)

    with open(file_stub, 'rb') as fh:
        msids = pickle.load(fh)

    return msids


def make_stub_content(content=None, date=None,
                      basedir_ref=None, basedir_stub=None,
                      msids=None, msids_5min=None, msids_daily=None):
    # If no content then require msids has been passed
    if content is None:
        content = fetch.content[msids[0].upper()]
        for msid in msids:
            assert fetch.content[msid.upper()] == content

    print(f'Making stub archive for {content}')

    fetch.ft['content'] = content
    with set_fetch_basedir(basedir_stub):
        dirname = Path(fetch.msid_files['contentdir'].abs)
    if dirname.exists():
        shutil.rmtree(dirname)
    dirname.mkdir(parents=True)

    row0, row1 = make_stub_archfiles(date, basedir_ref, basedir_stub)
    msids_ref = make_stub_colnames(basedir_ref, basedir_stub)

    if msids is None:
        msids = msids_ref
    msids = msids.copy()

    if 'TIME' not in msids:
        msids.append('TIME')

    if msids_5min is None:
        msids_5min = msids

    if msids_daily is None:
        msids_daily = msids

    for msid in msids:
        make_stub_h5_col(msid, row0, row1, basedir_ref, basedir_stub)

    for msid in msids_5min:
        make_stub_stats_col(msid, '5min', row1, basedir_ref, basedir_stub, date)

    for msid in msids_daily:
        make_stub_stats_col(msid, 'daily', row1, basedir_ref, basedir_stub, date)


def check_content(outdir, content, msids=None):
    outdir = Path(outdir)
    if outdir.exists():
        shutil.rmtree(outdir)

    print()
    print(f'Test dir: {outdir}')

    if msids is None:
        msids = CONTENTS[content]

    basedir_ref = outdir / 'orig'
    basedir_test = outdir / 'test'

    basedir_ref.mkdir(parents=True)
    basedir_test.mkdir(parents=True)

    # Make a local hard-link copy of select parts (content and msids) of the
    # "official" cheta archive data (nominally $SKA/data/engarchive) in basedir_ref.
    # This hard-link repo servers as the source for making the sync repo so this
    # is faster/lighter.
    make_linked_local_archive(basedir_ref, content, msids)

    # Make the sync repo, using basedir_ref as input data and outputting the
    # sync/ dir to basedir_test.
    with set_fetch_basedir(basedir_ref):
        make_sync_repo(basedir_test, content)

    # Make stubs of archive content, meaning filled with mostly zeros until about
    # before before test start date, then some real data to get the sync'ing going.
    make_stub_content(content,
                      date=DateTime(START) - 2,
                      basedir_stub=basedir_test,
                      basedir_ref=basedir_ref,
                      msids=msids)

    date_stop = (DateTime(STOP) + 2).date

    print(f'Updating client archive {content}')
    with set_fetch_basedir(basedir_test):
        update_client_archive.main([f'--content={content}',
                                    f'--log-level={LOG_LEVEL}',
                                    f'--date-stop={date_stop}',
                                    f'--data-root={basedir_test}',
                                    f'--sync-root={basedir_test}'])

    print(f'Checking {content} {msids}')
    for stat in None, '5min', 'daily':
        for msid in msids:
            fetch.times_cache['key'] = None
            with set_fetch_basedir(basedir_test):
                dat_stub = fetch.Msid(msid, START, STOP, stat=stat)

            fetch.times_cache['key'] = None
            with set_fetch_basedir(basedir_ref):
                dat_orig = fetch.Msid(msid, START, STOP, stat=stat)

            for attr in dat_orig.colnames:
                assert np.all(getattr(dat_stub, attr) == getattr(dat_orig, attr))


@pytest.mark.parametrize('content', list(CONTENTS))
def test_sync(tmpdir, content):
    check_content(tmpdir, content)

    # Clean up if test successful (otherwise check_content raises)
    if Path(tmpdir).exists():
        shutil.rmtree(tmpdir)
