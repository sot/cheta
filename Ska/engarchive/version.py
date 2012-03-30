"""
Version numbering for Ska.engarchive. The `major`, `minor`, and `bugfix` varaibles hold
the respective parts of the version number (bugfix is '0' if absent). The 
`release` variable is True if this is a release, and False if this is a 
development version. For the actual version string, use::

    from Ska.engarchive.version import version
    
or::

    from Ska.engarchive import __version__
    
NOTE: this code copied from astropy and modified.  Any license restrictions
therein are applicable.
"""

version = '0.17dev'

_versplit = version.replace('dev', '').split('.')
major = int(_versplit[0])
minor = int(_versplit[1])
if len(_versplit) < 3:
    bugfix = 0
else:
    bugfix = int(_versplit[2])
del _versplit

release = not version.endswith('dev')

def _get_git_devstr():
    """Determines the number of revisions in this repository.

    Returns
    -------
    devstr : str
        A string that begins with 'dev' to be appended to the version number string.
        
    """
    from os import path
    from subprocess import Popen, PIPE
    from warnings import warn
    
    if release:
        raise ValueError('revision devstring should not be used in a release version')

    currdir = path.abspath(path.split(__file__)[0])
    
    p = Popen(['git', 'rev-list', 'HEAD'], cwd=currdir,
              stdout=PIPE, stderr=PIPE, stdin=PIPE)
    stdout, stderr = p.communicate()
        
    if p.returncode == 128:
        # warn('No git repository present! Using default dev version.')
        return ''
    elif p.returncode != 0:
        # warn('Git failed while determining revision count: '+stderr)
        return ''
    
    nrev = stdout.count('\n')
    return  '-r%i' % nrev
    
if not release:
    version = version + _get_git_devstr()
