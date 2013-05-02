#!/usr/bin/env python
"""
Fetch values from the Ska engineering telemetry archive.
"""
__docformat__ = 'restructuredtext'
import sys
import os
import time
import contextlib
import cPickle as pickle
import logging
import operator
import fnmatch
import collections
import warnings

import numpy as np
import asciitable
import pyyaks.context

from . import file_defs
from .units import Units
from . import cache
from . import remote_access
from .version import version as __version__

from Chandra.Time import DateTime

# Module-level units, defaults to CXC units (e.g. Kelvins etc)
UNITS = Units(system='cxc')

# Module-level control of whether MSID.fetch will cache the last 30 results
CACHE = False

SKA = os.getenv('SKA') or '/proj/sot/ska'
ENG_ARCHIVE = os.getenv('ENG_ARCHIVE') or SKA + '/data/eng_archive'
IGNORE_COLNAMES = ('TIME', 'MJF', 'MNF', 'TLM_FMT')
DIR_PATH = os.path.dirname(os.path.abspath(__file__))

# Maximum number of MSIDs that should ever match an input MSID spec
# (to prevent accidentally selecting a very large number of MSIDs)
MAX_GLOB_MATCHES = 10

# Special-case state codes that override those in the TDB
STATE_CODES = {'3TSCMOVE': [(0, 'F'), (1, 'T')],
               '3FAMOVE': [(0, 'F'), (1, 'T')],
               '3SEAID': [(0, 'SEA-A'), (1, 'SEA-B')],
               '3SEARSET': [(0, 'F'), (1, 'T')],
               '3SEAROMF': [(0, 'F'), (1, 'T')],
               '3SEAINCM': [(0, 'F'), (1, 'T')],
               '3STAB2EN': [(0, 'DISABLE'), (1, 'ENABLE')],
               '3SMOTPEN': [(0, 'ENABLE'), (1, 'DISABLE')],
               '3SMOTSEL': [(0, 'TSC'), (1, 'FA')],
               '3SHTREN': [(0, 'DISABLE'), (1, 'ENABLE')],
               '3SEARAMF': [(0, 'F'), (1, 'T')],
               }


def local_or_remote_function(remote_print_output):
    """
    Decorator maker so that a function gets run either locally or remotely
    depending on the state of remote_access.access_remotely.  This decorator
    maker takes an optional remote_print_output argument that will be
    be printed (locally) if the function is executed remotely,

    For functions that are decorated using this wrapper:

    Every path that may be generated locally but used remotely should be
    split with _split_path(). Conversely the functions that use
    the resultant path should re-join them with os.path.join. In the
    remote case the join will happen using the remote rules.
    """
    def the_decorator(func):
        def wrapper(*args, **kwargs):
            if remote_access.access_remotely:
                # If accessing a remote archive, establish the connection (if
                # necessary)
                if not remote_access.connection_is_established():
                    try:
                        if not remote_access.establish_connection():
                            raise remote_access.RemoteConnectionError(
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
                if remote_access.show_print_output and not remote_print_output is None:
                    print remote_print_output
                    sys.stdout.flush()
                # Execute the function remotely and return the result
                return remote_access.execute_remotely(func, *args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return the_decorator


def _split_path(path):
    """
    Return a tuple of the components for ``path``. Strip off the drive if
    it exists. This works correctly for the local OS (linux / windows).
    """
    drive, path = os.path.splitdrive(path)
    folders = []
    while True:
        path, folder = os.path.split(path)

        if folder != "":
            folders.append(folder)
        else:
            if path == "\\":
                folders.append("/")
            elif path != "":
                folders.append(path)
            break

    folders.reverse()
    return folders

# Context dictionary to provide context for msid_files
ft = pyyaks.context.ContextDict('ft')

# Global (eng_archive) definition of file names
msid_files = pyyaks.context.ContextDict('msid_files', basedir=ENG_ARCHIVE)
msid_files.update(file_defs.msid_files)

# Module-level values defining available content types and column (MSID) names
filetypes = asciitable.read(os.path.join(DIR_PATH, 'filetypes.dat'))
content = collections.OrderedDict()

# Get the list of filenames (an array is built to pass all the filenames at
# once to the remote machine since passing them one at a time is rather slow)
all_msid_names_files = dict()
for filetype in filetypes:
    ft['content'] = filetype['content'].lower()
    all_msid_names_files[str(ft['content'])] = \
        _split_path(msid_files['colnames'].abs)


# Function to load MSID names from the files (executed remotely, if necessary)
@local_or_remote_function("Loading MSID names from Ska eng archive server...")
def load_msid_names(all_msid_names_files):
    import cPickle as pickle
    all_colnames = dict()
    for k, msid_names_file in all_msid_names_files.iteritems():
        try:
            all_colnames[k] = pickle.load(open(os.path.join(*msid_names_file)))
        except IOError:
            pass
    return all_colnames
# Load the MSID names
all_colnames = load_msid_names(all_msid_names_files)

# Save the names
for k, colnames in all_colnames.iteritems():
    content.update((x, k) for x in sorted(colnames)
                   if x not in IGNORE_COLNAMES)

# Cache of the most-recently used TIME array and associated bad values mask.
# The key is (content_type, tstart, tstop).
times_cache = dict(key=None)


# Set up logging.
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

logger = logging.getLogger('Ska.engarchive.fetch')
logger.addHandler(NullHandler())
logger.propagate = False

# Warn the user if ENG_ARCHIVE is set such that the data path is non-standard
if os.getenv('ENG_ARCHIVE'):
    print('fetch: using ENG_ARCHIVE={} for archive path'
          .format(os.getenv('ENG_ARCHIVE')))


def get_units():
    """Get the unit system currently being used for conversions.
    """
    return UNITS['system']


def set_units(unit_system):
    """Set the unit system used for output telemetry values.  The default
    is "cxc".  Allowed values for ``unit_system``  are:

    ====  ==============================================================
    cxc   FITS standard units used in CXC archive files (basically MKS)
    sci   Same as "cxc" but with temperatures in degC instead of Kelvins
    eng   OCC engineering units (TDB P009, e.g. degF, ft-lb-sec, PSI)
    ====  ==============================================================

    :param unit_system: system of units (cxc, sci, eng)
    """
    UNITS.set_units(unit_system)


def read_bad_times(table):
    """Include a list of bad times from ``table`` in the fetch module
    ``bad_times`` registry.  This routine can be called multiple times with
    different tables and the bad times will be appended to the registry.  The
    table can include any number of bad time interval specifications, one per
    line.  A bad time interval line has three columns separated by whitespace,
    e.g.::

      aogbias1  2008:292:00:00:00  2008:297:00:00:00

    The MSID name is not case sensitive and the time values can be in any
    ``DateTime`` format.  Blank lines and any line starting with the #
    character are ignored.
    """
    bad_times = asciitable.read(table, Reader=asciitable.NoHeader,
                                names=['msid', 'start', 'stop'])

    for msid, start, stop in bad_times:
        msid_bad_times.setdefault(msid.upper(), []).append((start, stop))

# Set up bad times dict
msid_bad_times = dict()
read_bad_times(os.path.join(DIR_PATH, 'msid_bad_times.dat'))


def msid_glob(msid):
    """Get the archive MSIDs matching ``msid``.

    The function returns a tuple of (msids, MSIDs) where ``msids`` is a list of
    MSIDs that is all lower case and (where possible) matches the input
    ``msid``.  The output ``MSIDs`` is all upper case and corresponds to the
    exact MSID names stored in the archive HDF5 files.

    :param msid: input MSID glob
    :returns: tuple (msids, MSIDs)
    """

    MSID = msid.upper()
    # First try MSID or DP_<MSID>.  If success then return the upper
    # case version and whatever the user supplied (could be any case).
    for match in (MSID, 'DP_' + MSID):
        if match in content:
            return [msid], [match]

    # Next try as a file glob.  If there is a match then return a
    # list of matches, all lower case and all upper case.  Since the
    # input was a glob the returned msids are just lower case versions
    # of the matched upper case MSIDs.
    for match in (MSID, 'DP_' + MSID):
        matches = fnmatch.filter(content.keys(), match)
        if matches:
            if len(matches) > MAX_GLOB_MATCHES:
                raise ValueError(
                    'MSID spec {} matches more than {} MSIDs.  '
                    'Refine the spec or increase fetch.MAX_GLOB_MATCHES'
                    .format(msid, MAX_GLOB_MATCHES))
            return [x.lower() for x in matches], matches

    raise ValueError('MSID {} is not in Eng Archive'.format(MSID))


class MSID(object):
    """Fetch data from the engineering telemetry archive into an MSID object.

    The input ``msid`` is case-insensitive and can include linux file "glob"
    patterns, for instance ``orb*1*_x`` (ORBITEPHEM1_X) or ``*pcadmd``
    (AOPCADMD).  For derived parameters the initial ``DP_`` is optional, for
    instance ``dpa_pow*`` (DP_DPA_POWER).

    :param msid: name of MSID (case-insensitive)
    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry (current time if not supplied)
    :param filter_bad: automatically filter out bad values
    :param stat: return 5-minute or daily statistics ('5min' or 'daily')

    :returns: MSID instance
    """
    units = UNITS
    fetch = sys.modules[__name__]

    def __init__(self, msid, start, stop=None, filter_bad=False, stat=None):
        msids, MSIDs = msid_glob(msid)
        if len(MSIDs) > 1:
            raise ValueError('Multiple matches for {} in Eng Archive'
                             .format(msid))
        else:
            self.msid = msids[0]
            self.MSID = MSIDs[0]

        # Capture the current module units
        self.units = Units(self.units['system'])
        self.unit = self.units.get_msid_unit(self.MSID)
        self.stat = stat
        if stat:
            self.dt = {'5min': 328, 'daily': 86400}[stat]

        self.tstart = DateTime(start).secs
        self.tstop = (DateTime(stop).secs if stop else
                      DateTime(time.time(), format='unix').secs)
        self.datestart = DateTime(self.tstart).date
        self.datestop = DateTime(self.tstop).date
        try:
            self.content = content[self.MSID]
        except KeyError:
            raise ValueError('MSID %s is not in Eng Archive' % self.MSID)

        # Get the times, values, bad values mask from the HDF5 files archive
        self._get_data()

        # If requested filter out bad values and set self.bad = None
        if filter_bad:
            self.filter_bad()

    def _get_data(self):
        """Get data from the Eng archive"""
        logger.info('Getting data for %s between %s to %s',
                    self.msid, self.datestart, self.datestop)

        # Avoid stomping on caller's filetype 'ft' values with _cache_ft()
        with _cache_ft():
            ft['content'] = self.content
            ft['msid'] = self.MSID

            if self.stat:
                ft['interval'] = self.stat
                self._get_stat_data()
            else:
                gmd = (self._get_msid_data_cached if CACHE else
                       self._get_msid_data)
                self.vals, self.times, self.bads, self.colnames = \
                    gmd(self.content, self.tstart, self.tstop, self.MSID,
                        self.units['system'])

    def _get_stat_data(self):
        """Do the actual work of getting stats values for an MSID from HDF5
        files"""
        filename = msid_files['stats'].abs
        logger.info('Opening %s', filename)

        @local_or_remote_function("Getting stat data for " + self.MSID +
                                  " from Ska eng archive server...")
        def get_stat_data_from_server(filename, dt, tstart, tstop):
            import tables
            h5 = tables.openFile(os.path.join(*filename))
            table = h5.root.data
            times = (table.col('index') + 0.5) * dt
            row0, row1 = np.searchsorted(times, [tstart, tstop])
            table_rows = table[row0:row1]  # returns np.ndarray (structured array)
            h5.close()
            return (times[row0:row1], table_rows, row0, row1)
        times, table_rows, row0, row1 = \
            get_stat_data_from_server(_split_path(filename),
                                      self.dt, self.tstart, self.tstop)
        logger.info('Closed %s', filename)

        self.bads = None
        self.times = times
        self.colnames = ['times']
        for colname in table_rows.dtype.names:
            # Don't like the way columns were named in the stats tables.
            # Fix that here.
            colname_out = _plural(colname) if colname != 'n' else 'samples'

            if colname_out in ('vals', 'mins', 'maxes', 'means',
                               'p01s', 'p05s', 'p16s', 'p50s',
                               'p84s', 'p95s', 'p99s'):
                vals = self.units.convert(self.MSID, table_rows[colname])
            elif colname_out == 'stds':
                vals = self.units.convert(self.MSID, table_rows[colname],
                                          delta_val=True)
            else:
                vals = table_rows[colname]

            setattr(self, colname_out, vals)
            self.colnames.append(colname_out)

        # Redefine the 'vals' attribute to be 'means' if it exists.  This is a
        # more consistent use of the 'vals' attribute and there is little use
        # for the original sampled version.
        if hasattr(self, 'means'):
            self.midvals = self.vals
            self.vals = self.means

    @staticmethod
    @cache.lru_cache(30)
    def _get_msid_data_cached(content, tstart, tstop, msid, unit_system):
        """Do the actual work of getting time and values for an MSID from HDF5
        files and cache recent results.  Caching is very beneficial for derived
        parameter updates but not desirable for normal fetch usage."""
        return MSID._get_msid_data(content, tstart, tstop, msid, unit_system)

    @staticmethod
    def _get_msid_data(content, tstart, tstop, msid, unit_system):
        """Do the actual work of getting time and values for an MSID from HDF5
        files"""

        # Get a row slice into HDF5 file for this content type that picks out
        # the required time range plus a little padding on each end.
        h5_slice = get_interval(content, tstart, tstop)

        # Read the TIME values either from cache or from disk.
        if times_cache['key'] == (content, tstart, tstop):
            logger.info('Using times_cache for %s %s to %s',
                        content, tstart, tstop)
            times = times_cache['val']  # Already filtered on times_ok
            times_ok = times_cache['ok']  # For filtering MSID.val and MSID.bad
            times_all_ok = times_cache['all_ok']
        else:
            ft['msid'] = 'time'
            filename = msid_files['msid'].abs
            logger.info('Reading %s', filename)

            @local_or_remote_function("Getting time data from Ska eng archive server...")
            def get_time_data_from_server(h5_slice, filename):
                import tables
                h5 = tables.openFile(os.path.join(*filename))
                times_ok = ~h5.root.quality[h5_slice]
                times = h5.root.data[h5_slice]
                h5.close()
                return(times_ok, times)

            times_ok, times = get_time_data_from_server(h5_slice, _split_path(filename))

            # Filter bad times.  Last instance of bad times in archive is 2004
            # so don't do this unless needed.  Creating a new 'times' array is
            # much more expensive than checking for np.all(times_ok).
            times_all_ok = np.all(times_ok)
            if not times_all_ok:
                times = times[times_ok]

            times_cache.update(dict(key=(content, tstart, tstop),
                                    val=times,
                                    ok=times_ok,
                                    all_ok=times_all_ok))

        # Extract the actual MSID values and bad values mask
        ft['msid'] = msid
        filename = msid_files['msid'].abs
        logger.info('Reading %s', filename)

        @local_or_remote_function("Getting msid data for " + msid +
                                  " from Ska eng archive server...")
        def get_msid_data_from_server(h5_slice, filename):
            import tables
            h5 = tables.openFile(os.path.join(*filename))
            vals = h5.root.data[h5_slice]
            bads = h5.root.quality[h5_slice]
            h5.close()
            return(vals, bads)

        vals, bads = get_msid_data_from_server(h5_slice, _split_path(filename))

        # Filter bad times rows if needed
        if not times_all_ok:
            logger.info('Filtering bad times values for %s', msid)
            bads = bads[times_ok]
            vals = vals[times_ok]

        # Slice down to exact requested time range
        row0, row1 = np.searchsorted(times, [tstart, tstop])
        logger.info('Slicing %s arrays [%d:%d]', msid, row0, row1)
        vals = Units(unit_system).convert(msid.upper(), vals[row0:row1])
        times = times[row0:row1]
        bads = bads[row0:row1]
        colnames = ['times', 'vals', 'bads']

        return (vals, times, bads, colnames)

    @property
    def state_codes(self):
        """List of state codes tuples (raw_count, state_code) for state-valued
        MSIDs
        """
        if 'S' not in self.vals.dtype.str:
            self._state_codes = None

        if self.MSID in STATE_CODES:
            self._state_codes = STATE_CODES[self.MSID]

        if not hasattr(self, '_state_codes'):
            import Ska.tdb
            states = Ska.tdb.msids[self.MSID].Tsc
            if states is None or len(set(states['CALIBRATION_SET_NUM'])) != 1:
                warnings.warn('MSID {} has string vals but no state codes '
                              'or multiple calibration sets'.format(self.msid))
                self._state_codes = None
            else:
                states = np.sort(states.data, order='LOW_RAW_COUNT')
                self._state_codes = [(state['LOW_RAW_COUNT'],
                                      state['STATE_CODE']) for state in states]
        return self._state_codes

    @property
    def raw_vals(self):
        """Raw counts corresponding to the string state-code values that are
        stored in ``self.vals``
        """
        # If this is not a string-type value then there are no raw values
        if 'S' not in self.vals.dtype.str or self.state_codes is None:
            self._raw_vals = None

        if not hasattr(self, '_raw_vals'):
            self._raw_vals = np.zeros(len(self.vals), dtype='int8') - 1
            # CXC state code telem all has same length with trailing spaces
            # so find max length for formatting below.
            max_len = max(len(x[1]) for x in self.state_codes)
            fmtstr = '{:' + str(max_len) + 's}'
            for raw_val, state_code in self.state_codes:
                ok = self.vals == fmtstr.format(state_code)
                self._raw_vals[ok] = raw_val

        return self._raw_vals

    @property
    def tdb(self):
        """Access the Telemetry database entries for this MSID
        """
        import Ska.tdb
        return Ska.tdb.msids[self.MSID]

    def interpolate(self, dt=328.0, start=None, stop=None):
        """Perform nearest-neighbor interpolation of the MSID to the specified
        time sequence.

        The time sequence steps uniformly by ``dt`` seconds starting at the
        ``start`` time and ending at the ``stop`` time.  If not provided the
        times default to the first and last times for the MSID.

        The MSID ``times`` attribute is set to the common time sequence.  In
        addition a new attribute ``times0`` is defined that stores the nearest
        neighbor interpolated time, providing the *original* timestamps of each
        new interpolated value for that MSID.

        :param dt: time step (sec)
        :param start: start of interpolation period (DateTime format)
        :param stop: end of interpolation period (DateTime format)
        """
        import Ska.Numpy

        tstart = DateTime(start).secs if start else self.times[0]
        tstop = DateTime(stop).secs if stop else self.times[-1]

        # Don't allow extrapolation
        tstart = max(tstart, self.times[0])
        tstop = min(tstop, self.times[-1])

        times = np.arange(tstart, tstop, dt)

        logger.info('Interpolating index for %s', self.msid)
        indexes = Ska.Numpy.interpolate(np.arange(len(self.times)),
                                        self.times, times,
                                        method='nearest', sorted=True)
        logger.info('Slicing on indexes')
        for colname in self.colnames:
            colvals = getattr(self, colname)
            if colvals is not None:
                setattr(self, colname, colvals[indexes])

        # Make a new attribute times0 that stores the nearest neighbor
        # interpolated times.  Then set the MSID times to be the common
        # interpolation times.
        self.times0 = self.times
        self.times = times

    def filter_bad(self, bads=None):
        """Filter out any bad values.

        After applying this method the "bads" column will be set to None to
        indicate that there are no bad values.

        :param bads: Bad values mask.  If not supplied then self.bads is used.
        """
        # If bad mask is provided then override any existing bad mask for MSID
        if bads is not None:
            self.bads = bads

        # Nothing to do if bads is None (i.e. bad values already filtered)
        if self.bads is None:
            return

        if np.any(self.bads):
            logger.info('Filtering bad values for %s', self.msid)
            ok = ~self.bads
            colnames = (x for x in self.colnames if x != 'bads')
            for colname in colnames:
                setattr(self, colname, getattr(self, colname)[ok])

        self.bads = None

    def filter_bad_times(self, start=None, stop=None, table=None):
        """Filter out intervals of bad data in the MSID object.

        There are three usage options:

        - Supply no arguments.  This will use the global list of bad times read
          in with fetch.read_bad_times().
        - Supply both ``start`` and ``stop`` values where each is a single
          value in a valid DateTime format.
        - Supply an ``table`` parameter in the form of a 2-column table of
          start and stop dates (space-delimited) or the name of a file with
          data in the same format.

        The ``table`` parameter must be supplied as a table or the name of a
        table file, for example::

          bad_times = ['2008:292:00:00:00 2008:297:00:00:00',
                       '2008:305:00:12:00 2008:305:00:12:03',
                       '2010:101:00:01:12 2010:101:00:01:25']
          msid.filter_bad_times(table=bad_times)
          msid.filter_bad_times(table='msid_bad_times.dat')

        :param start: Start of time interval to exclude (any DateTime format)
        :param stop: End of time interval to exclude (any DateTime format)
        :param table: Two-column table (start, stop) of bad time intervals
        """
        if table is not None:
            bad_times = asciitable.read(table, Reader=asciitable.NoHeader,
                                        names=['start', 'stop'])
        elif start is None and stop is None:
            bad_times = []
            for msid_glob, times in msid_bad_times.items():
                if fnmatch.fnmatch(self.MSID, msid_glob):
                    bad_times.extend(times)
        elif start is None or stop is None:
            raise ValueError('filter_times requires either 2 args '
                             '(start, stop) or no args')
        else:
            bad_times = [(start, stop)]

        self._filter_times(bad_times, exclude=True)

    def remove_intervals(self, intervals):
        """
        Remove telemetry points that occur within the specified ``intervals``

        This method is the converse of select_intervals().

        The ``intervals`` argument can be either a list of (start, stop) tuples
        or an EventQuery object from kadi.

        Examples
        --------
        This example shows fetching the pitch component of the spacecraft rate.
        After examining the rates, the samples during maneuvers are then removed
        and the standard deviation is recomputed.  This filters out the large
        rates during maneuvers::

          >>> aorate2 = fetch.Msid('aorate2', '2011:001', '2011:002')
          >>> aorate2.vals.mean() * 3600 * 180 / np.pi  # rate in arcsec/sec
          3.9969393528801782
          >>> figure(1)
          >>> aorate2.plot(',')

          >>> from kadi import events
          >>> aorate2.remove_intervals(events.manvrs)
          >>> aorate2.vals.mean() * 3600 * 180 / np.pi  # rate in arcsec/sec
          -0.0003688639491030978
          >>> figure(2)
          >>> aorate2.plot(',')

        :param intervals: EventQuery or iterable (N x 2) with start, stop dates/times
        """
        self._filter_times(intervals, exclude=True)

    def select_intervals(self, intervals):
        """
        Select telemetry points that occur within the specified ``intervals``

        This method is the converse of remove_intervals().

        The ``intervals`` argument can be either a list of (start, stop) tuples
        or an EventQuery object from kadi.

        Examples
        --------
        This example shows fetching the pitch component of the spacecraft rate.
        After examining the rates, the samples during maneuvers are then selected
        and the mean is recomputed.  This highlights the large rates during
        maneuvers::

          >>> aorate2 = fetch.Msid('aorate2', '2011:001', '2011:002')
          >>> aorate2.vals.mean() * 3600 * 180 / np.pi  # rate in arcsec/sec
          3.9969393528801782
          >>> figure(1)
          >>> aorate2.plot(',')

          >>> from kadi import events
          >>> aorate2.select_intervals(events.manvrs)
          >>> aorate2.vals.mean() * 3600 * 180 / np.pi  # rate in arcsec/sec
          24.764309542605481
          >>> figure(2)
          >>> aorate2.plot(',')

        :param intervals: EventQuery or iterable (N x 2) with start, stop dates/times
        """
        self._filter_times(intervals, exclude=False)

    def _filter_times(self, intervals, exclude=True):
        """
        Filter the times of self based on ``intervals``.

        :param intervals: iterable (N x 2) with tstart, tstop in seconds
        :param exclude: exclude intervals if True, else include intervals
        """
        # Make an initial acceptance mask.  If exclude is True then initially
        # all values are allowed (ok=True).  If exclude is False (i.e. only
        # include the interval times) then ok=False everywhere.
        ok = np.empty(len(self.times), dtype=bool)
        ok[:] = exclude

        # Check if this is an EventQuery.  Would rather not import EventQuery
        # because this is expensive (django), so just look at the name and
        # count on no inheritence.
        if intervals.__class__.__name__ == 'EventQuery':
            intervals = intervals.intervals(self.datestart, self.datestop)

        intervals = [(DateTime(start).secs, DateTime(stop).secs)
                     for start, stop in intervals]

        for tstart, tstop in intervals:
            if tstart > tstop:
                raise ValueError("Start time %s must be less than stop time %s"
                                 % (tstart, tstop))

            if tstop < self.times[0] or tstart > self.times[-1]:
                continue

            # Find the indexes of bad data.  Using side=left,right respectively
            # will exclude points exactly equal to the bad_times values
            # (though in reality an exact tie is extremely unlikely).
            i0 = np.searchsorted(self.times, tstart, side='left')
            i1 = np.searchsorted(self.times, tstop, side='right')
            ok[i0:i1] = not exclude

        colnames = (x for x in self.colnames)
        for colname in colnames:
            attr = getattr(self, colname)
            if isinstance(attr, np.ndarray):
                setattr(self, colname, attr[ok])

    def write_zip(self, filename, append=False):
        """Write MSID to a zip file named ``filename``

        Within the zip archive the data for this MSID will be stored in csv
        format with the name <msid_name>.csv.

        :param filename: output zipfile name
        :param append: append to an existing zipfile
        """
        import zipfile
        from itertools import izip
        colnames = self.colnames[:]
        if self.bads is None and 'bads' in colnames:
            colnames.remove('bads')

        colvals = tuple(getattr(self, x) for x in colnames)
        fmt = ",".join("%s" for x in colnames)

        f = zipfile.ZipFile(filename, ('a' if append
                                       and os.path.exists(filename)
                                       else 'w'))
        info = zipfile.ZipInfo(self.msid + '.csv')
        info.external_attr = 0664 << 16L  # Set permissions
        info.date_time = time.localtime()[:7]
        info.compress_type = zipfile.ZIP_DEFLATED
        f.writestr(info,
                   ",".join(colnames) + '\n' +
                   '\n'.join(fmt % x for x in izip(*colvals)) + '\n')
        f.close()

    def logical_intervals(self, op, val):
        """Determine contiguous intervals during which the logical comparison
        expression "MSID.vals op val" is True.  Allowed values for ``op``
        are::

          ==  !=  >  <  >=  <=

        The intervals are guaranteed to be complete so that the all reported
        intervals had a transition before and after within the telemetry
        interval.

        Returns a structured array table with a row for each interval.
        Columns are:

        * datestart: date of interval start
        * datestop: date of interval stop
        * duration: duration of interval (sec)
        * tstart: time of interval start (CXC sec)
        * tstop: time of interval stop (CXC sec)

        Example::

          dat = fetch.MSID('aomanend', '2010:001', '2010:005')
          manvs = dat.logical_intervals('==', 'NEND')
          manvs['duration']

        :param op: logical operator, one of ==  !=  >  <  >=  <=
        :param val: comparison value
        :returns: structured array table of intervals
        """
        ops = {'==': operator.eq,
               '!=': operator.ne,
               '>': operator.gt,
               '<': operator.lt,
               '>=': operator.ge,
               '<=': operator.le}
        try:
            op = ops[op]
        except KeyError:
            raise ValueError('op = "{}" is not in allowed values: {}'
                             .format(op, sorted(ops.keys())))

        # Do local version of bad value filtering
        if self.bads is not None and np.any(self.bads):
            ok = ~self.bads
            vals = self.vals[ok]
            times = self.times[ok]
        else:
            vals = self.vals
            times = self.times

        starts = ~op(vals[:-1], val) & op(vals[1:], val)
        ends = op(vals[:-1], val) & ~op(vals[1:], val)

        # If last telemetry point is not val then the data ends during that
        # interval and there will be an extra start transition that must be
        # removed.
        i_starts = np.flatnonzero(starts)
        if op(vals[-1], val):
            i_starts = i_starts[:-1]

        # If first entry is val then the telemetry starts during an interval
        # and there will be an extra end transition that must be removed.
        i_ends = np.flatnonzero(ends)
        if op(vals[0], val):
            i_ends = i_ends[1:]

        tstarts = times[i_starts]
        tstops = times[i_ends]
        intervals = {'datestart': DateTime(tstarts).date,
                     'datestop': DateTime(tstops).date,
                     'duration': times[i_ends] - times[i_starts],
                     'tstart': tstarts,
                     'tstop':  tstops}

        import Ska.Numpy
        return Ska.Numpy.structured_array(intervals)

    def state_intervals(self):
        """Determine contiguous intervals during which the MSID value
        is unchanged.

        Returns a structured array table with a row for each interval.
        Columns are:

        * datestart: date of interval start
        * datestop: date of interval stop
        * duration: duration of interval (sec)
        * tstart: time of interval start (CXC sec)
        * tstop: time of interval stop (CXC sec)
        * val: MSID value during the interval

        Example::

          dat = fetch.MSID('cobsrqid', '2010:001', '2010:005')
          obsids = dat.state_intervals()

        :param val: state value for which intervals are returned.
        :returns: structured array table of intervals
        """

        # Do local version of bad value filtering
        if self.bads is not None and np.any(self.bads):
            ok = ~self.bads
            vals = self.vals[ok]
            times = self.times[ok]
        else:
            vals = self.vals
            times = self.times

        if len(self.vals) < 2:
            raise ValueError('Filtered data length must be at least 2')

        transitions = np.hstack([[True], vals[:-1] != vals[1:], [True]])
        t0 = times[0] - (times[1] - times[0]) / 2
        t1 = times[-1] + (times[-1] - times[-2]) / 2
        midtimes = np.hstack([[t0], (times[:-1] + times[1:]) / 2, [t1]])

        state_vals = vals[transitions[1:]]
        state_times = midtimes[transitions]

        intervals = {'datestart': DateTime(state_times[:-1]).date,
                     'datestop': DateTime(state_times[1:]).date,
                     'tstart': state_times[:-1],
                     'tstop': state_times[1:],
                     'duration': state_times[1:] - state_times[:-1],
                     'val': state_vals}

        import Ska.Numpy
        return Ska.Numpy.structured_array(intervals)

    def iplot(self, fmt='-b', fmt_minmax='-c', **plot_kwargs):
        """Make an interactive plot for exploring the MSID data.

        This method opens a new plot figure (or clears the current figure) and
        plots the MSID ``vals`` versus ``times``.  This plot can be panned or
        zoomed arbitrarily and the data values will be fetched from the archive
        as needed.  Depending on the time scale, ``iplot`` displays either full
        resolution, 5-minute, or daily values.  For 5-minute and daily values
        the min and max values are also plotted.

        Once the plot is displayed and the window is selected by clicking in
        it, the following key commands are recognized::

          a: autoscale for full data range in x and y
          m: toggle plotting of min/max values
          p: pan at cursor x
          y: toggle autoscaling of y-axis
          z: zoom at cursor x
          ?: print help

        Example::

          dat = fetch.Msid('aoattqt1', '2011:001', '2012:001', stat='5min')
          dat.iplot()
          dat.iplot('.b', '.c', markersize=0.5)

        Caveat: the ``iplot()`` method is not meant for use within scripts, and
        may give unexpected results if used in combination with other plotting
        commands directed at the same plot figure.

        :param fmt: plot format for values (default="-b")
        :param fmt_minmax: plot format for mins and maxes (default="-c")
        :param plot_kwargs: additional plotting keyword args

        """

        from .plot import MsidPlot
        self._iplot = MsidPlot(self, fmt, fmt_minmax, **plot_kwargs)

    def plot(self, *args, **kwargs):
        """Plot the MSID ``vals`` using Ska.Matplotlib.plot_cxctime()

        This is a convenience function for plotting the MSID values.  It
        is equivalent to::

          plot_cxctime(self.times, self.vals, *args, **kwargs)

        where ``*args`` are additional arguments and ``**kwargs`` are
        additional keyword arguments that are accepted by ``plot_cxctime()``.

        Example::

          dat = fetch.Msid('tephin', '2011:001', '2012:001', stat='5min')
          dat.plot('-r', linewidth=2)

        """

        from Ska.Matplotlib import plot_cxctime
        vals = self.raw_vals if self.state_codes else self.vals
        plot_cxctime(self.times, vals, *args, state_codes=self.state_codes,
                     **kwargs)


class MSIDset(collections.OrderedDict):
    """Fetch a set of MSIDs from the engineering telemetry archive.

    Each input ``msid`` is case-insensitive and can include linux file "glob"
    patterns, for instance ``orb*1*_?`` (ORBITEPHEM1_X, Y and Z) or
    ``aoattqt[1234]`` (AOATTQT1, 2, 3, and 4).  For derived parameters the
    initial ``DP_`` is optional, for instance ``dpa_pow*`` (DP_DPA_POWER).

    :param msids: list of MSID names (case-insensitive)
    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry (current time if not supplied)
    :param filter_bad: automatically filter out bad values
    :param stat: return 5-minute or daily statistics ('5min' or 'daily')

    :returns: Dict-like object containing MSID instances keyed by MSID name
    """
    MSID = MSID

    def __init__(self, msids, start, stop=None, filter_bad=False, stat=None):
        super(MSIDset, self).__init__()

        self.tstart = DateTime(start).secs
        self.tstop = (DateTime(stop).secs if stop else DateTime().secs)
        self.datestart = DateTime(self.tstart).date
        self.datestop = DateTime(self.tstop).date

        # Input ``msids`` may contain globs, so expand each and add to new list
        new_msids = []
        for msid in msids:
            new_msids.extend(msid_glob(msid)[0])
        for msid in new_msids:
            self[msid] = self.MSID(msid, self.tstart, self.tstop,
                                   filter_bad=False, stat=stat)
        if filter_bad:
            self.filter_bad()

    def filter_bad(self):
        """Filter bad values for the MSID set.

        This function applies the union (logical-OR) of bad value masks for all
        MSIDs in the set with the same content type.  The result is that the
        filtered MSID samples are valid for *all* MSIDs within the
        content type and the arrays all match up.

        For example::

          msids = fetch.MSIDset(['aorate1', 'aorate2', 'aogyrct1', 'aogyrct2'],
                                '2009:001', '2009:002')
          msids.filter_bad()

        Since ``aorate1`` and ``aorate2`` both have content type of
        ``pcad3eng`` they will be filtered as a group and will remain with the
        same sampling.  This will allow something like::

          plot(msids['aorate1'].vals, msids['aorate2'].vals)

        Likewise the two gyro count MSIDs would be filtered as a group.  If
        this group-filtering is not the desired behavior one can always call
        the individual MSID.filter_bad() function for each MSID in the set::

          for msid in msids.values():
              msid.filter_bad()
        """
        for content in set(x.content for x in self.values()):
            bads = None

            msids = [x for x in self.values()
                     if x.content == content and x.bads is not None]
            for msid in msids:
                if bads is None:
                    bads = msid.bads.copy()
                else:
                    bads |= msid.bads

            for msid in msids:
                msid.filter_bad(bads)

    def filter_bad_times(self, start=None, stop=None, table=None):
        """Filter out intervals of bad data in the MSIDset object.

        There are three usage options:

        - Supply no arguments.  This will use the global list of bad times read
          in with fetch.read_bad_times().
        - Supply both ``start`` and ``stop`` values where each is a single
          value in a valid DateTime format.
        - Supply an ``table`` parameter in the form of a 2-column table of
          start and stop dates (space-delimited) or the name of a file with
          data in the same format.

        The ``table`` parameter must be supplied as a table or the name of a
        table file, for example::

          msidset.filter_bad_times()
          bad_times = ['2008:292:00:00:00 2008:297:00:00:00',
                       '2008:305:00:12:00 2008:305:00:12:03',
                       '2010:101:00:01:12 2010:101:00:01:25']
          msidset.filter_bad_times(table=bad_times)
          msidset.filter_bad_times(table='msid_bad_times.dat')

        :param start: Start of time interval to exclude (any DateTime format)
        :param stop: End of time interval to exclude (any DateTime format)
        :param table: Two-column table (start, stop) of bad time intervals
        """
        for msid in self.values():
            msid.filter_bad_times(start, stop, table)

    def interpolate(self, dt=328.0, start=None, stop=None, filter_bad=True):
        """Perform nearest-neighbor interpolation of all MSID values in the set
        to a common time sequence.  The values are updated in-place.

        The time sequence steps uniformly by ``dt`` seconds starting at the
        ``start`` time and ending at the ``stop`` time.  If not provided the
        times default to the ``start`` and ``stop`` times for the MSID set.

        For each MSID in the set the ``times`` attribute is set to the common
        time sequence.  In addition a new attribute ``times0`` is defined that
        stores the nearest neighbor interpolated time, providing the *original*
        timestamps of each new interpolated value for that MSID.

        By default ``filter_bad`` is True and each MSID has bad data filtered
        *before* interpolation so that the nearest neighbor interpolation only
        finds good data.  In this case (or for ``stat`` values which do not
        have bad values), the ``times0`` attribute can be used to diagnose
        whether the interpolation is meaningful.  For instance large numbers of
        identical time stamps in ``times0`` may be a problem.

        If ``filter_bad`` is set to false then data are not filtered.  In this
        case the MSID ``bads`` values are interpolated as well and provide an
        indication if the interpolated values are bad.

        :param dt: time step (sec)
        :param start: start of interpolation period (DateTime format)
        :param stop: end of interpolation period (DateTime format)
        :param filter_bad: filter bad values before interpolating
        """
        import Ska.Numpy

        msids = self.values()  # MSID objects in the MSIDset

        # Get the nominal tstart / tstop range
        tstart = DateTime(start).secs if start else self.tstart
        tstop = DateTime(stop).secs if stop else self.tstop

        # Ensure that tstart / tstop is entirely within the range of available
        # data fetched from the archive.
        max_fetch_tstart = max(msid.times[0] for msid in msids)
        min_fetch_tstop = min(msid.times[-1] for msid in msids)
        tstart = max(tstart, max_fetch_tstart)
        tstop = min(tstop, min_fetch_tstop)

        self.times = np.arange(tstart, tstop, dt)

        for msid in msids:
            if filter_bad:
                msid.filter_bad()
            logger.info('Interpolating index for %s', msid.msid)
            indexes = Ska.Numpy.interpolate(np.arange(len(msid.times)),
                                            msid.times, self.times,
                                            method='nearest', sorted=True)
            logger.info('Slicing on indexes')
            for colname in msid.colnames:
                colvals = getattr(msid, colname)
                if colvals is not None:
                    setattr(msid, colname, colvals[indexes])

            # Make a new attribute times0 that stores the nearest neighbor
            # interpolated times.  Then set the MSID times to be the common
            # interpolation times.
            msid.times0 = msid.times
            msid.times = self.times

    def write_zip(self, filename):
        """Write MSIDset to a zip file named ``filename``

        Within the zip archive the data for each MSID in the set will be stored
        in csv format with the name <msid_name>.csv.

        :param filename: output zipfile name
        """
        append = False
        for msid in self.values():
            msid.write_zip(filename, append=append)
            append = True


class Msid(MSID):
    """
    Fetch data from the engineering telemetry archive into an MSID object.
    Same as MSID class but with filter_bad=True by default.

    :param msid: name of MSID (case-insensitive)
    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry (current time if not supplied)
    :param filter_bad: automatically filter out bad values
    :param stat: return 5-minute or daily statistics ('5min' or 'daily')
    :param unit_system: Unit system (cxc|eng|sci, default=current units)

    :returns: MSID instance
    """
    units = UNITS

    def __init__(self, msid, start, stop=None, filter_bad=True, stat=None):
        super(Msid, self).__init__(msid, start, stop=stop,
                                   filter_bad=filter_bad, stat=stat)


class Msidset(MSIDset):
    """Fetch a set of MSIDs from the engineering telemetry archive.
    Same as MSIDset class but with filter_bad=True by default.

    :param msids: list of MSID names (case-insensitive)
    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry (current time if not supplied)
    :param filter_bad: automatically filter out bad values
    :param stat: return 5-minute or daily statistics ('5min' or 'daily')
    :param unit_system: Unit system (cxc|eng|sci, default=current units)

    :returns: Dict-like object containing MSID instances keyed by MSID name
    """
    MSID = MSID

    def __init__(self, msids, start, stop=None, filter_bad=True, stat=None):
        super(Msidset, self).__init__(msids, start, stop=stop,
                                      filter_bad=filter_bad, stat=stat)


def fetch_records(start, stop, msids, dt=32.8):
    """
    Fetch data from the telemetry archive as a recarray at a uniform time
    spacing.

    Only records where all columns have good quality get included.  This
    routine can be substantially slower than fetch_arrays because of the
    interpolation onto a common time sequence.

    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry
    :param msids: list of MSIDs (case-insensitive)
    :param dt: sampling time (sec)

    :returns: numpy recarray with columns for time (CXC seconds) and ``msids``
    """
    import Ska.Numpy

    with _cache_ft():
        tstart, tstop, times, values, quals = _fetch(start, stop, msids)
    dt_times = np.arange(tstart, tstop, dt)

    len_times = len(dt_times)
    bad = np.zeros(len_times, dtype=bool)
    for msid in msids:
        MSID = msid.upper()
        index = Ska.Numpy.interpolate(np.arange(len(times[MSID])),
                                      times[MSID], dt_times, 'nearest')
        # Include also some interpolation validation check, something like (but
        # not exactly) (abs(dt_times - times[MSID][index]) > 1.05 * dt)
        bad |= quals[MSID][index]
        values[msid] = values[MSID][index]

    ok = ~bad
    records = [dt_times[ok].copy()]
    for msid in msids:
        records.append(values[msid][ok].copy())

    out = np.rec.fromarrays(records, titles=['time'] + msids)
    return out


def fetch_arrays(start, stop, msids):
    """
    Fetch data for ``msids`` from the telemetry archive as arrays.

    This routine is deprecated and is retained only for back-compatibility with
    old plotting analysis scripts.

    The telemetry values are returned in three dictionaries: ``times``,
    ``values``, and ``quals``.  Each of these dictionaries contains key-value
    pairs for each of the input ``msids``.

    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry
    :param msids: list of MSIDs (case-insensitive)

    :returns: times, values, quals
    """
    times = {}
    values = {}
    quals = {}

    for msid in msids:
        m = MSID(msid, start, stop)
        times[msid] = m.times
        values[msid] = m.vals
        quals[msid] = m.bads

    return times, values, quals


def fetch_array(start, stop, msid):
    """
    Fetch data for single ``msid`` from the telemetry archive as an array.

    This routine is deprecated and is retained only for back-compatibility with
    old plotting analysis scripts.

    The telemetry values are returned in three arrays: ``times``, ``values``,
    and ``quals``.

    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry
    :param msid: MSID (case-insensitive)

    :returns: times, values, quals
    """

    m = MSID(msid, start, stop)
    times = m.times
    values = m.vals
    quals = m.bads

    return times, values, quals


class memoized(object):
    """Decorator that caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned, and
    not re-evaluated.
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        try:
            return self.cache[args]
        except KeyError:
            self.cache[args] = value = self.func(*args)
            return value
        except TypeError:
            # uncachable -- for instance, passing a list as an argument.
            # Better to not cache than to blow up entirely.
            return self.func(*args)

    def __repr__(self):
        """Return the function's docstring."""
        return self.func.__doc__


@memoized
def get_interval(content, tstart, tstop):
    """
    Get the approximate row intervals that enclose the specified ``tstart`` and
    ``tstop`` times for the ``content`` type.

    :param content: content type (e.g. 'pcad3eng', 'thm1eng')
    :param tstart: start time (CXC seconds)
    :param tstop: stop time (CXC seconds)

    :returns: rowslice
    """

    ft['content'] = content

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

    return get_interval_from_db(tstart, tstop, _split_path(msid_files['archfiles'].abs))


@contextlib.contextmanager
def _cache_ft():
    """
    Cache the global filetype ``ft`` context variable so that fetch operations
    do not corrupt user values of ``ft``.
    """
    ft_cache_pickle = pickle.dumps(ft)
    try:
        yield
    finally:
        ft_cache = pickle.loads(ft_cache_pickle)
        ft.update(ft_cache)
        delkeys = [x for x in ft if x not in ft_cache]
        for key in delkeys:
            del ft[key]


def add_logging_handler(level=logging.INFO,
                        formatter=None,
                        handler=None):
    """Configure logging for fetch module.

    :param level: logging level (logging.DEBUG, logging.INFO, etc)
    :param formatter: logging.Formatter (default: Formatter('%(funcName)s: %(message)s'))
    :param handler: logging.Handler (default: StreamHandler())
    """

    if formatter is None:
        formatter = logging.Formatter('%(funcName)s: %(message)s')

    if handler is None:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)


def _plural(x):
    """Return English plural of ``x``.  Super-simple and only valid for the
    known small set of cases within fetch where it will get applied.
    """
    return x + 'es' if (x.endswith('x') or x.endswith('s')) else x + 's'
