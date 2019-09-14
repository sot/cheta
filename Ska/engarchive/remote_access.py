# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Settings and functions for remotely accessing an engineering archive.
"""
from __future__ import print_function, division, absolute_import

import sys
import os
import getpass
from pathlib import Path

try:
    import ipyparallel as parallel
except ImportError:
    from IPython import parallel
from six.moves import input


def get_data_access_info(is_windows=sys.platform.startswith('win')):
    """
    Determine path to eng archive data and whether to access data remotely.

    Returns path to data, equivalent of the ENG_ARCHIVE variable, i.e.
    Path(SKA, 'data', 'eng_archive').  This is returned as a string absolute
    path.

    Also returns whether to access data using the remote server.

    :param is_windows: bool, is this windows platform?
    :return: eng_archive, access_remotely
    """
    # Define the path to eng archive data (``eng_archive``), using either the ENG_ARCHIVE env var
    # or looking in the standard SKA place.  In the case of accessing data remotely this is all
    # moot (and SKA is not required to be defined), so just make sure this bit runs without
    # failing.
    ska = os.getenv('SKA')
    ska_eng_path = None if (ska is None) else os.path.join(ska, 'data', 'eng_archive')
    eng_archive = os.getenv('ENG_ARCHIVE')
    if eng_archive is None and ska_eng_path is not None:
        eng_archive = ska_eng_path

    # Remote access is controlled as follows:
    # - The environment variable SKA_ACCESS_REMOTELY can be set to "False" or "True"
    # - Remote access defaults to True on Windows systems unless the SKA environment
    #   variable is set and data on $SKA\data\eng_archive are found.
    # - Remote access defaults to False on non-Windows systems.

    # First check if there is a local data archive
    if eng_archive is not None:
        eng_archive = str(Path(eng_archive).absolute())
        has_ska_data = Path(eng_archive).exists()
    else:
        has_ska_data = False

    if 'SKA_ACCESS_REMOTELY' in os.environ:
        # User explicitly specified, so that is the end of the story.
        import ast
        ska_access_remotely = ast.literal_eval(os.environ['SKA_ACCESS_REMOTELY'])
    else:
        ska_access_remotely = False if has_ska_data else is_windows

    if not ska_access_remotely and not has_ska_data:
        if eng_archive is None:
            msg = 'need to define SKA or ENG_ARCHIVE environment variable'
        else:
            msg = f'no {eng_archive} directory'
        raise RuntimeError(f'no local Ska data found and remote access is not selected: {msg}')

    if ska_access_remotely:
        # If accessing remotely, then hardwire eng_archive to the linux path where
        # the data are stored on the server.  This prevents a local SKA repository
        # from getting used on the remote server.
        ska_eng_path = '/proj/sot/ska/data/eng_archive'
        eng_archive = ska_eng_path

    # Warn the user if eng data path is non-standard.  Note: if no SKA then
    # any path is non-standard.
    if eng_archive != ska_eng_path:
        print(f'fetch: using ENG_ARCHIVE={eng_archive} for archive path')

    return eng_archive, ska_access_remotely


# Module globals with eng archive data root path and whether or not to access
# data remotely.
ENG_ARCHIVE, access_remotely = get_data_access_info()

# Hostname (IP), username, and password for remote access to the eng archive
hostname = None
username = None
password = None

# Flag to ask the user for credentials if the ssh login fails
ask_again_if_connect_fails = True

# Flag to show print output for remote calls
show_print_output = sys.platform.startswith('win')

# Client key file for connecting to the remote server (ipcontroller)
client_key_file = os.path.join(sys.prefix, "ska_remote_access.json")

# IPython parallel client for accessing the remote python engine
_remote_client = None


class RemoteConnectionError(Exception):
    pass


def establish_connection():
    """
    Function to establish a connection to the remote server
    Return success status (True/False)
    """
    global _remote_client
    global hostname
    global username
    global password

    try_to_connect = True

    # Loop until the user is able to connect or cancels
    while _remote_client is None:
        # Get the username and password if not already set
        hostname = hostname or input('Enter hostname (or IP) of Ska ' +
                                     'server (enter to cancel):')
        if hostname == "":
            break
        default_username = getpass.getuser()
        username = username or input('Enter your login username [' +
                                     default_username + ']:')
        password = password or getpass.getpass('Enter your password:')

        # Open the connection to the server
        print('Establishing connection to ' + hostname + '...')
        sys.stdout.flush()
        try:
            _remote_client = parallel.Client(client_key_file,
                                             sshserver=f'{username}@{hostname}',
                                             password=password)
        except Exception:
            raise
            print('Error connecting to server ', hostname, ': ', sys.exc_info()[0])
            sys.stdout.flush()
            _remote_client = None
            # Clear out information so the user can try again
            hostname = None
            username = None
            password = None
            if not ask_again_if_connect_fails:
                break

    return connection_is_established()


def connection_is_established():
    """
    Function to check if a connection to the remote server has been established
    """
    return _remote_client is not None


def execute_remotely(fcn, *args, **kwargs):
    """
    Function for executing a function remotely
    """
    if not connection_is_established():
        raise parallel.ConnectionError("Connection not established to remote server")
    dview = _remote_client[0]  # Use the first (and should be only) engine
    dview.block = True
    return dview.apply_sync(fcn, *args, **kwargs)


def test_connection():
    """
    Function to perform a quick test of the connection to the
    remote server
    """
    def remote_fcn():
        import os
        return os.sys.version
    return execute_remotely(remote_fcn)


def close_connection():
    """
    Function to close the connection to the remote server
    """
    global _remote_client

    _remote_client.close()
    _remote_client = None
