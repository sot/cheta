# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test getting data archive path information for eng archive and possible
access via a remote server.

In addition, do manual tests below.  For tests that require remote access,
one must be VPN'd to the OCC network and enter an IP address and credentials
for chimchim.  In addition, the file ska_remote_access.json must be
installed at the Ska3 root (sys.prefix).  Search email around Jan 3, 2019 for
"ska_remote_access.json" to find a path to this file.

- Nominal remote access on Windows:
  No env vars set (SKA, ENG_ARCHIVE, SKA_ACCESS_REMOTELY).
  Confirm that remote access is enabled and works by fetching an MSID::

    import os
    os.environ.pop('SKA', None)
    os.environ.pop('ENG_ARCHIVE', None)
    os.environ.pop('SKA_ACCESS_REMOTELY', None)
    from Ska.engarchive import fetch, remote_access
    fetch.add_logging_handler()
    assert remote_access.access_remotely is True
    dat = fetch.Msid('tephin', '2018:001', '2018:010')
    print(dat.vals)

- Override remote access on Windows by setting SKA to a valid path
  so eng archive data will be found. Confirm that remote access is
  disabled and fetch uses local access::

    import os
    os.environ['SKA'] = <path_to_ska_root>
    os.environ.pop('ENG_ARCHIVE', None)
    os.environ.pop('SKA_ACCESS_REMOTELY', None)
    from Ska.engarchive import fetch, remote_access
    fetch.add_logging_handler()
    assert remote_access.access_remotely is False
    dat = fetch.Msid('1wrat', '2018:001', '2018:010')
    print(dat.vals)

- Override remote access on non-Windows by setting SKA_ACCESS_REMOTELY to 'True'::

    import os
    os.environ['SKA_ACCESS_REMOTELY'] = 'True'
    from Ska.engarchive import fetch, remote_access
    fetch.add_logging_handler()
    assert remote_access.access_remotely is True
    dat = fetch.Msid('tephin', '2018:001', '2018:010')
    print(dat.vals)

"""
import os
from pathlib import Path
import shutil

import pytest

from Ska.engarchive.remote_access import get_data_access_info

INVALID_DIR = str(Path(__file__).parent / '__non_existent_invalid_directory____')

ORIG_ENV = {name: os.getenv(name)
            for name in ('SKA', 'ENG_ARCHIVE', 'SKA_ACCESS_REMOTELY')}


def setenv(name, val):
    if val is not None:
        os.environ[name] = str(val)
    else:
        os.environ.pop(name, None)


@pytest.fixture()
def remote_setup_dirs(tmpdir):
    """
    Pytest fixture to provide temporary mock Ska eng archive data
    directory structure.

    :param tmpdir: temp directory supplied by pytest
    """
    ska_dir = Path(tmpdir)
    eng_archive_dir = ska_dir / 'data' / 'eng_archive'
    (eng_archive_dir / 'data').mkdir(parents=True)

    yield (ska_dir, eng_archive_dir)

    # Teardown: return environment to original
    for name in 'SKA', 'ENG_ARCHIVE', 'SKA_ACCESS_REMOTELY':
        setenv(name, ORIG_ENV[name])

    shutil.rmtree(tmpdir)


def test_remote_access_get_data_access_info1(remote_setup_dirs):
    """
    Unit test of the get_data_access_info() function with no env vars set.
    """
    # No env vars set
    setenv('SKA', None)
    setenv('ENG_ARCHIVE', None)  # I.e. not set
    setenv('SKA_ACCESS_REMOTELY', None)

    # Windows
    eng_archive, ska_access_remotely = get_data_access_info(is_windows=True)
    assert eng_archive == '/proj/sot/ska/data/eng_archive'
    assert ska_access_remotely is True

    # Not windows
    with pytest.raises(RuntimeError) as err:
        get_data_access_info(is_windows=False)
    assert 'need to define SKA or ENG_ARCHIVE environment variable' in str(err.value)


def test_remote_access_get_data_access_info2(remote_setup_dirs):
    """
    Just SKA set to a valid directory (typical case on linux/mac)
    """
    ska_dir, eng_archive_dir = remote_setup_dirs

    setenv('SKA', ska_dir)
    setenv('ENG_ARCHIVE', None)  # I.e. not set
    setenv('SKA_ACCESS_REMOTELY', None)
    for is_windows in True, False:
        eng_archive, ska_access_remotely = get_data_access_info(is_windows)
        assert eng_archive == str(eng_archive_dir.absolute())
        assert ska_access_remotely is False


def test_remote_access_get_data_access_info3(remote_setup_dirs):
    """
    Just ENG_ARCHIVE set to a valid directory (typical for testing)
    SKA either unset or set to a bad directory
    """
    ska_dir, eng_archive_dir = remote_setup_dirs

    for ska_env in None, INVALID_DIR:
        setenv('SKA', ska_env)
        setenv('ENG_ARCHIVE', eng_archive_dir)
        setenv('SKA_ACCESS_REMOTELY', None)
        for is_windows in True, False:
            eng_archive, ska_access_remotely = get_data_access_info(is_windows)
            assert eng_archive == str(eng_archive_dir.absolute())
            assert ska_access_remotely is False


def test_remote_access_get_data_access_info4(remote_setup_dirs):
    """
    ENG_ARCHIVE set to a non-existent directory
    """
    setenv('SKA', None)
    setenv('ENG_ARCHIVE', INVALID_DIR)
    setenv('SKA_ACCESS_REMOTELY', None)

    # Windows doesn't care about an invalid ENG_ARCHIVE, goes to remote access
    # with hardwired /proj/sot/ska root for remote data.
    eng_archive, ska_access_remotely = get_data_access_info(is_windows=True)
    assert eng_archive == '/proj/sot/ska/data/eng_archive'
    assert ska_access_remotely is True

    # Not windows: raises RuntimeError because no local data around found
    with pytest.raises(RuntimeError) as err:
        get_data_access_info(is_windows=False)


def test_remote_access_get_data_access_info5(remote_setup_dirs):
    """
    No SKA or ENG_ARCHIVE and SKA_ACCESS_REMOTELY=False

    Raises RuntimeError on windows and not-windows.
    """
    setenv('SKA', None)
    setenv('ENG_ARCHIVE', None)
    setenv('SKA_ACCESS_REMOTELY', False)

    for is_windows in True, False:
        with pytest.raises(RuntimeError) as err:
            get_data_access_info(is_windows)
        assert 'need to define SKA or ENG_ARCHIVE environment variable' in str(err.value)


def test_remote_access_get_data_access_info6(remote_setup_dirs):
    """
    SKA set to a valid directory and SKA_ACCESS_REMOTELY=True
    """
    ska_dir, eng_archive_dir = remote_setup_dirs

    setenv('SKA', ska_dir)
    setenv('ENG_ARCHIVE', None)  # I.e. not set
    setenv('SKA_ACCESS_REMOTELY', 'True')

    for is_windows in True, False:
        eng_archive, ska_access_remotely = get_data_access_info(is_windows)
        assert eng_archive == '/proj/sot/ska/data/eng_archive'
        assert ska_access_remotely is True
