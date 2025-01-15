# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Test getting data archive path information for eng archive and possible access via a
remote server.

Functional testing
------------------
For tests that require remote access, yoou must be VPN'd to the remote network and enter
an IP address and credentials for the remote server. Normally this is the OCC VPN and
chimchim (respectively) using the existing flight remote server. However, testing with
the SI VPN and a server on the HEAD network is also possible.

Client remote access key file
-----------------------------
The file ``ska_remote_access.json`` must be installed at the Ska3 root (``python -c
'import sys; print(sys.prefix)'``). This provides credentials for connecting to the
server. See the TWiki path SpecialProject > DAWG > DAWG_TIPS_AND_TRICKS > Ska section
for the file.

Remote access on Windows
------------------------
Here there are no special environment vars set (SKA, ENG_ARCHIVE, SKA_ACCESS_REMOTELY).
Confirm that remote access is enabled and works by fetching an MSID::

    >>> import os
    >>> os.environ.pop('SKA', None)
    >>> os.environ.pop('ENG_ARCHIVE', None)
    >>> os.environ.pop('SKA_ACCESS_REMOTELY', None)
    >>> from cheta import fetch, remote_access
    >>> fetch.add_logging_handler()
    >>> assert remote_access.access_remotely is True
    >>> dat = fetch.Msid('tephin', '2018:001', '2018:010')
    >>> print(dat.vals)

Local Ska data on Windows
-------------------------
Override remote access on Windows by setting SKA to a valid path so eng archive data is
found. Confirm that remote access is disabled and fetch uses local access::

    >>> import os
    >>> os.environ['SKA'] = <path_to_ska_root>
    >>> os.environ.pop('ENG_ARCHIVE', None)
    >>> os.environ.pop('SKA_ACCESS_REMOTELY', None)
    >>> from cheta import fetch, remote_access
    >>> fetch.add_logging_handler()
    >>> assert remote_access.access_remotely is False
    >>> dat = fetch.Msid('1wrat', '2018:001', '2018:010')
    >>> print(dat.vals)

Remote access on non-Windows
----------------------------
Override remote access on non-Windows by setting SKA_ACCESS_REMOTELY to 'True'::

    >>> import os
    >>> os.environ['SKA_ACCESS_REMOTELY'] = 'True'
    >>> from cheta
    >>> import fetch, remote_access
    >>> fetch.add_logging_handler()
    >>> assert remote_access.access_remotely is True

    # Optional for testing with a custom remote server on kady
    >>> remote_access.client_key_file = <path_to_ska_remote_access.json>

    >>> dat = fetch.Msid('tephin', '2018:001', '2018:010')
    >>> print(dat.vals)

Start a test remote server
--------------------------
Normally it is sufficient to use the existing ``chimchim`` server. However, for testing
with a new Python version or other changes, you can start a new server on ``kady``.

Scripts related to starting and maintaining a remote data server can be found in
``/home/mbaski/python``. The files there are named obviously, though circa 2025 they
still refer to SHINY throughout.

.. warning:: For aspect team testing, it is best to use ``kady`` as the test server.
     There was some question about whether testing on ``chimchim`` was interfering
     with the production server that is normally running.

As an example (in the flight Ska3 environment)::

  ipcontroller --profile=test_remote --reuse >& remote_ipython_server.log &

  ipengine --file $HOME/.ipython/profile_test_remote/security/ipcontroller-engine.json \
  >& remote_ipython_engine.log &

The first time you run the ``ipcontroller`` command this will create the
``ipcontroller-client.json`` and ``ipcontroller-engine.json`` files in
``$HOME/.ipython/profile_test_remote/security/``. You might want to skip the ``--reuse``
flag to get a fresh start if things are not working.

The ``ipcontroller-client.json`` then needs to be copied to the local client machine.
For testing, you should copy it to any local file and then override
``remote_access.client_key_file`` accordingly.
"""

import os
import shutil
from pathlib import Path

import pytest
from astropy.utils.exceptions import AstropyUserWarning

from cheta.remote_access import get_data_access_info

INVALID_DIR = str(Path(__file__).parent / "__non_existent_invalid_directory____")

ORIG_ENV = {
    name: os.getenv(name) for name in ("SKA", "ENG_ARCHIVE", "SKA_ACCESS_REMOTELY")
}


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
    eng_archive_dir = ska_dir / "data" / "eng_archive"
    (eng_archive_dir / "data").mkdir(parents=True)

    yield (ska_dir, eng_archive_dir)

    # Teardown: return environment to original
    for name in "SKA", "ENG_ARCHIVE", "SKA_ACCESS_REMOTELY":
        setenv(name, ORIG_ENV[name])

    shutil.rmtree(tmpdir)


def test_remote_access_get_data_access_info1(remote_setup_dirs):
    """
    Unit test of the get_data_access_info() function with no env vars set.
    """
    # No env vars set
    setenv("SKA", None)
    setenv("ENG_ARCHIVE", None)  # I.e. not set
    setenv("SKA_ACCESS_REMOTELY", None)

    # Windows
    eng_archive, ska_access_remotely = get_data_access_info(is_windows=True)
    assert eng_archive == "/proj/sot/ska/data/eng_archive"
    assert ska_access_remotely is True

    # Not windows
    with pytest.warns(AstropyUserWarning):
        eng_archive, ska_access_remotely = get_data_access_info(is_windows=False)
    assert eng_archive is None
    assert ska_access_remotely is False


def test_remote_access_get_data_access_info2(remote_setup_dirs):
    """
    Just SKA set to a valid directory (typical case on linux/mac)
    """
    ska_dir, eng_archive_dir = remote_setup_dirs

    setenv("SKA", ska_dir)
    setenv("ENG_ARCHIVE", None)  # I.e. not set
    setenv("SKA_ACCESS_REMOTELY", None)
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
        setenv("SKA", ska_env)
        setenv("ENG_ARCHIVE", eng_archive_dir)
        setenv("SKA_ACCESS_REMOTELY", None)
        for is_windows in True, False:
            eng_archive, ska_access_remotely = get_data_access_info(is_windows)
            assert eng_archive == str(eng_archive_dir.absolute())
            assert ska_access_remotely is False


def test_remote_access_get_data_access_info4(remote_setup_dirs):
    """
    ENG_ARCHIVE set to a non-existent directory
    """
    setenv("SKA", None)
    setenv("ENG_ARCHIVE", INVALID_DIR)
    setenv("SKA_ACCESS_REMOTELY", None)

    # Windows doesn't care about an invalid ENG_ARCHIVE, goes to remote access
    # with hardwired /proj/sot/ska root for remote data.
    eng_archive, ska_access_remotely = get_data_access_info(is_windows=True)
    assert eng_archive == "/proj/sot/ska/data/eng_archive"
    assert ska_access_remotely is True

    # Not windows: raises RuntimeError because no local data around found
    with pytest.warns(
        AstropyUserWarning,
        match="no local Ska data found and remote access is not selected",
    ):
        get_data_access_info(is_windows=False)


def test_remote_access_get_data_access_info5(remote_setup_dirs):
    """
    No SKA or ENG_ARCHIVE and SKA_ACCESS_REMOTELY=False

    Raises RuntimeError on windows and not-windows.
    """
    setenv("SKA", None)
    setenv("ENG_ARCHIVE", None)
    setenv("SKA_ACCESS_REMOTELY", False)

    for is_windows in True, False:
        with pytest.warns(
            AstropyUserWarning,
            match="need to define SKA or ENG_ARCHIVE environment variable",
        ):
            out = get_data_access_info(is_windows)
        assert out == (None, False)


def test_remote_access_get_data_access_info6(remote_setup_dirs):
    """
    SKA set to a valid directory and SKA_ACCESS_REMOTELY=True
    """
    ska_dir, eng_archive_dir = remote_setup_dirs

    setenv("SKA", ska_dir)
    setenv("ENG_ARCHIVE", None)  # I.e. not set
    setenv("SKA_ACCESS_REMOTELY", "True")

    for is_windows in True, False:
        eng_archive, ska_access_remotely = get_data_access_info(is_windows)
        assert eng_archive == "/proj/sot/ska/data/eng_archive"
        assert ska_access_remotely is True
