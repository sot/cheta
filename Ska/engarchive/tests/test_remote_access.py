import os
import sys
from pathlib import Path

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


def test_remote_access_get_data_access_info(tmpdir):
    """
    Unit test of the get_data_access_info() function.
    """
    # Make a fake Ska data installation
    ska_dir = Path(tmpdir)
    eng_archive_dir = ska_dir / 'data' / 'eng_archive'
    (eng_archive_dir / 'data').mkdir(parents=True)

    # Check some possible use cases:

    # No env vars set
    setenv('SKA', None)
    setenv('ENG_ARCHIVE', None)  # I.e. not set
    setenv('SKA_ACCESS_REMOTELY', None)

    # Windows
    eng_archive, ska_access_remotely = get_data_access_info(is_windows=True)
    assert eng_archive is None
    assert ska_access_remotely is True

    # Not windows
    with pytest.raises(RuntimeError) as err:
        get_data_access_info(is_windows=False)
    assert 'need to define SKA or ENG_ARCHIVE environment variable' in str(err)

    # Just SKA set to a valid directory (typical case on linux/mac)
    setenv('SKA', ska_dir)
    setenv('ENG_ARCHIVE', None)  # I.e. not set
    setenv('SKA_ACCESS_REMOTELY', None)
    for is_windows in True, False:
        eng_archive, ska_access_remotely = get_data_access_info(is_windows)
        assert eng_archive == str(eng_archive_dir.absolute())
        assert ska_access_remotely is False

    # Just ENG_ARCHIVE set to a valid directory (typical for testing)
    # SKA either unset or set to a bad directory
    for ska_env in None, INVALID_DIR:
        setenv('SKA', ska_env)
        setenv('ENG_ARCHIVE', eng_archive_dir)
        setenv('SKA_ACCESS_REMOTELY', None)
        for is_windows in True, False:
            eng_archive, ska_access_remotely = get_data_access_info(is_windows)
            assert eng_archive == str(eng_archive_dir.absolute())
            assert ska_access_remotely is False

    # ENG_ARCHIVE set to a bad directory
    setenv('SKA', ska_dir)
    setenv('ENG_ARCHIVE', INVALID_DIR)
    setenv('SKA_ACCESS_REMOTELY', None)
    # Windows
    eng_archive, ska_access_remotely = get_data_access_info(is_windows=True)
    assert eng_archive == INVALID_DIR
    assert ska_access_remotely is True

    # No SKA or ENG_ARCHIVE and SKA_ACCESS_REMOTELY=False
    setenv('SKA', None)
    setenv('ENG_ARCHIVE', None)  # I.e. not set
    setenv('SKA_ACCESS_REMOTELY', False)

    for is_windows in True, False:
        with pytest.raises(RuntimeError) as err:
            get_data_access_info(is_windows)
        assert 'need to define SKA or ENG_ARCHIVE environment variable' in str(err)

    # Teardown
    for name in 'SKA', 'ENG_ARCHIVE', 'SKA_ACCESS_REMOTELY':
        setenv(name, ORIG_ENV[name])
