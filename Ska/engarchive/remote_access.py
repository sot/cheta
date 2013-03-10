"""
Settings and functions for remote access to the engineering archive.
"""
import sys
import getpass
import IPython.parallel

# To use remote access, this flag needs to be enabled
enabled = False

# Username and password for remote access to the eng archive
username = None
password = None

# Server name
hostname = '131.142.113.4'

# IPython parallel client for accessing the remote python engine
remote_client = None

class RemoteConnectionError(Exception):
    pass

def establish_connection():
    # Returns success status
    
    global remote_client
    
#    max_num_tries = 3
#    num_tries = 0
#    while not connection_is_established() and num_tries <= max_num_tries:
#
#        num_tries = num_tries + 1
        
    # Get the username and password if not already set
    if username is None:
        default_username = getpass.getuser()
        response = raw_input('Enter your login username [' + default_username + ']:')
        the_username = response or default_username
    else:
        the_username = username
    the_password = password or getpass.getpass('Enter your password:')
    
    # Open the connection to the
    print('Establishing connection to ' + hostname + '...')
    try:
        remote_client = IPython.parallel.Client(sshserver = hostname,
                                                username=the_username,
                                                password=the_password)
    except:
        print 'Error connecting to server ',hostname,': ',sys.exc_info()[0]
        remote_client = None
        
    return(connection_is_established())


def connection_is_established():
    return (not remote_client is None)
    

def execute_remotely(fcn, *args, **kwargs):
    # Function for executing a function remotely
#    if not connection_is_established():
#        establish_connection()
#        if not connection_is_established():
#            raise IPython.parallel.ConnectionError("Error establishing connection to remote server")
    if not connection_is_established():
        raise IPython.parallel.ConnectionError("Connection not established to remote server")
    dview = remote_client[0]; # Use the first (and should be only) engine
    dview.block = True
    return dview.apply(fcn, *args, **kwargs)
    
    
def close_connection():
    
    global remote_client
    
    remote_client.close()
    remote_client = None