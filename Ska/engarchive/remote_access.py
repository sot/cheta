"""
Settings and functions for remotely accessing an engineering archive.
"""
from __future__ import print_function, division, absolute_import

import sys
import os
import getpass
import warnings
try:
    import ipyparallel as parallel
except ImportError:
    from IPython import parallel
from six.moves import input

from .file_defs import ENG_ARCHIVE

# Check if data directory for ENG_ARCHIVE exists.  In the local_or_remote_function
# decorator, if access_remotely is False and KADI_REMOTE_ENABLED is True then it will try
# using the kadi web server.  The KADI_REMOTE_TIMEOUT limits how long the kadi web server
# (via fetch) will work on a single function call.  This effectively limits the remote
# ingest size since read speed is of order 10^7 elements / second.
KADI_REMOTE_ENABLED = not os.path.exists(ENG_ARCHIVE)
KADI_REMOTE_URL = 'http://kadi.cfa.harvard.edu'
KADI_REMOTE_TIMEOUT = 20  # seconds
KADI_REMOTE_MAX_ROWS = 1e7  # max rows of data

# To use remote access, this flag should be set True (it is true by default
# on Windows systems, but can manually be set to true on Linux systems
# if you don't have direct access to the archive)
access_remotely = sys.platform.startswith('win')

# Hostname (IP), username, and password for remote access to the eng archive
hostname = None
username = None
password = None

# Flag to ask the user for credentials if the ssh login fails
ask_again_if_connect_fails = True

# Flag to show print output for remote calls
show_print_output = sys.platform.startswith('win')

# Client key file for connecting to the remote server (ipcontroller)
client_key_file = os.path.join(sys.prefix,"ska_remote_access.json")

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
        if hostname=="":
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
                                             sshserver=username+'@'+hostname,
                                             password=password)
        except:
            print('Error connecting to server ',hostname,': ',sys.exc_info()[0])
            sys.stdout.flush()
            _remote_client = None
            # Clear out information so the user can try again
            hostname = None
            username = None
            password = None
            if not ask_again_if_connect_fails:
                break
        
    return(connection_is_established())


def connection_is_established():
    """
Function to check if a connection to the remote server has been established
"""
    return (not _remote_client is None)
    

def execute_remotely(fcn, *args, **kwargs):
    """
Function for executing a function remotely
"""
    if not connection_is_established():
        raise parallel.ConnectionError(
                "Connection not established to remote server")
    dview = _remote_client[0]; # Use the first (and should be only) engine
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
    return (execute_remotely(remote_fcn))


def close_connection():
    """
Function to close the connection to the remote server
"""
    global _remote_client
    
    _remote_client.close()
    _remote_client = None
    

def local_or_remote_function(remote_print_output):
    """
    Decorator maker so that a function gets run either locally or remotely depending on
    the state of ``access_remotely`` (IPython parallel via SSH) and
    ``KADI_REMOTE_ENABLED`` (kadi web server).  This decorator maker takes an optional
    remote_print_output argument that will be be printed (locally) if the function is
    executed remotely,

    For functions that are decorated using this wrapper:

    Every path that may be generated locally but used remotely should be
    split with _split_path(). Conversely the functions that use
    the resultant path should re-join them with os.path.join. In the
    remote case the join will happen using the remote rules.
    """
    def the_decorator(func):
        def wrapper(*args, **kwargs):
            if access_remotely:
                # If accessing a remote archive, establish the connection (if
                # necessary)
                if not connection_is_established():
                    try:
                        if not establish_connection():
                            raise RemoteConnectionError(
                                "Unable to establish connection for remote fetch.")
                    except EOFError:
                        # An EOF error can be raised if the python interpreter is being
                        # called in such a way that input cannot be received from the
                        # user (e.g. when the python interpreter is called from MATLAB)
                        # If that is the case (and remote access is enabled), then
                        # raise an import error
                        raise ImportError("Unable to interactively get remote access "
                                          "info from user.")
                # Print the output, if specified
                if show_print_output and remote_print_output is not None:
                    print(remote_print_output)
                    sys.stdout.flush()
                # Execute the function remotely and return the result
                return execute_remotely(func, *args, **kwargs)
            else:
                if KADI_REMOTE_ENABLED:
                    # Let the user know that kadi web server being used for data access
                    warnings.warn('using {} for remote data access'.format(KADI_REMOTE_URL))
                    if show_print_output and remote_print_output is not None:
                        print(remote_print_output)
                        sys.stdout.flush()

                    # Set up to use the kadi web server to run function remotely
                    import requests
                    import zlib
                    from six.moves import cPickle as pickle

                    # Special case three functions that get potentially large datasets
                    # from the HDF5 file archives.  Add a ``max_rows`` kwarg.
                    if func.__name__.endswith('_data_from_server'):
                        kwargs['max_rows'] = KADI_REMOTE_MAX_ROWS
                    func_info = dict(func_name=func.__name__, args=args, kwargs=kwargs)
                    data = {'func_info': pickle.dumps(func_info, protocol=0)}
                    url = KADI_REMOTE_URL + '/eng_archive/remote_func/'

                    # Run the remote function and get response.
                    r = requests.post(url, data=data, timeout=KADI_REMOTE_TIMEOUT)

                    if r.status_code != 200:
                        raise RuntimeError('kadi remote function {} failed with status {}'
                                           .format(func.__name__, r.status_code))

                    # Unzip and unpickle the output
                    try:
                        out = pickle.loads(zlib.decompress(r.content))
                    except:
                        raise ValueError('kadi remote function {} returned content that '
                                         'failed unpickling'.format(func.__name__))

                    # Remote function raised an exception so re-raise here
                    if isinstance(out, Exception):
                        raise out

                else:
                    # Plain old local call
                    out = func(*args, **kwargs)

                return out

        return wrapper

    return the_decorator


#########################################################################
# Functions pulled from fetch.py that do the low-level work of accessing
# the CXC data files.
#########################################################################


# Load the MSID names
# Function to load MSID names from the files (executed remotely, if necessary)
@local_or_remote_function("Loading MSID names from Ska eng archive server...")
def load_msid_names(all_msid_names_files):
    from six.moves import cPickle as pickle
    all_colnames = dict()
    for k, msid_names_file in all_msid_names_files.items():
        try:
            all_colnames[k] = pickle.load(open(os.path.join(*msid_names_file), 'rb'))
        except IOError:
            pass
    return all_colnames


@local_or_remote_function("Getting stat data "
                          " from Ska eng archive server...")
def get_stat_data_from_server(filename, dt, tstart, tstop, max_rows=None):
    import tables
    import numpy as np
    open_file = getattr(tables, 'open_file', None) or tables.openFile
    h5 = open_file(os.path.join(*filename))
    table = h5.root.data
    times = (table.col('index') + 0.5) * dt
    row0, row1 = np.searchsorted(times, [tstart, tstop])
    if max_rows and row1 - row0 > max_rows:
        raise ValueError('max rows exceeded for remote query')
    table_rows = table[row0:row1]  # returns np.ndarray (structured array)
    h5.close()
    return (times[row0:row1], table_rows, row0, row1)


@local_or_remote_function("Getting time data from Ska eng archive server...")
def get_time_data_from_server(h5_slice, filename, max_rows=None):
    if max_rows and h5_slice.stop - h5_slice.start > max_rows:
        raise ValueError('max rows exceeded for remote query')
    import tables
    open_file = getattr(tables, 'open_file', None) or tables.openFile
    h5 = open_file(os.path.join(*filename))
    times_ok = ~h5.root.quality[h5_slice]
    times = h5.root.data[h5_slice]
    h5.close()
    return(times_ok, times)


@local_or_remote_function("Getting msid data "
                          " from Ska eng archive server...")
def get_msid_data_from_server(h5_slice, filename, max_rows=None):
    if max_rows and h5_slice.stop - h5_slice.start > max_rows:
        raise ValueError('max rows exceeded for remote query')
    import tables
    open_file = getattr(tables, 'open_file', None) or tables.openFile
    h5 = open_file(os.path.join(*filename))
    vals = h5.root.data[h5_slice]
    bads = h5.root.quality[h5_slice]
    h5.close()
    return(vals, bads)


@local_or_remote_function("Getting time range from Ska eng archive server...")
def get_time_range_from_server(filename):
    import tables
    open_file = getattr(tables, 'open_file', None) or tables.openFile
    h5 = open_file(os.path.join(*filename))
    tstart = h5.root.data[0]
    tstop = h5.root.data[-1]
    h5.close()
    return tstart, tstop


@local_or_remote_function("Getting interval data from " +
                          "DB on Ska eng archive server...")
def get_interval_from_db(tstart, tstop, server):

    import Ska.DBI

    db = Ska.DBI.DBI(dbi='sqlite', server=os.path.join(*server))

    query_row = db.fetchone('SELECT tstart, rowstart FROM archfiles '
                            'WHERE filetime < ? order by filetime desc',
                            (tstart,))
    if not query_row:
        query_row = db.fetchone('SELECT tstart, rowstart FROM archfiles '
                                'order by filetime asc')

    rowstart = query_row['rowstart']

    query_row = db.fetchone('SELECT tstop, rowstop FROM archfiles '
                            'WHERE filetime > ? order by filetime asc',
                            (tstop,))
    if not query_row:
        query_row = db.fetchone('SELECT tstop, rowstop FROM archfiles '
                                'order by filetime desc')

    rowstop = query_row['rowstop']

    return slice(rowstart, rowstop)
