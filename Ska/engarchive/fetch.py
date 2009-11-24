#!/usr/bin/env python
"""
Fetch values from the Ska engineering archive.
"""
from __future__ import with_statement  # only for python 2.5

__docformat__ = 'restructuredtext'
import os
import time
import contextlib
import cPickle as pickle
import logging

import numpy
import tables
import Ska.Table
import pyyaks.context

import file_defs
from Chandra.Time import DateTime

SKA = os.getenv('SKA') or '/proj/sot/ska'
SKA_DATA = SKA + '/data/eng_archive'

# Context dictionary to provide context for msid_files
ft = pyyaks.context.ContextDict('ft')

# Global (eng_archive) definition of file names
msid_files = pyyaks.context.ContextDict('msid_files', basedir=file_defs.msid_root) 
msid_files.update(file_defs.msid_files)

# Module-level values defining available content types and column (MSID) names
filetypes = Ska.Table.read_ascii_table(os.path.join(SKA_DATA, 'filetypes.dat'))
content = dict()
for filetype in filetypes:
    ft['content'] = filetype['content'].lower()
    colnames = pickle.load(open(msid_files['colnames'].abs))
    content.update((x, ft['content'].val) for x in colnames)

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

class MSID(object):
    """
    Fetch data from the engineering telemetry archive into an MSID object. 

    :param msid: name of MSID (case-insensitive)
    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry (current time if not supplied)
    :param filter_bad: automatically filter out bad values
    :param stat: return 5-minute or daily statistics ('5min' or 'daily')

    :returns: MSID instance
    """
    def __init__(self, msid, start, stop=None, filter_bad=False, stat=None):
        self.msid = msid
        self.MSID = msid.upper()
        self.stat = stat
        if stat:
            self.dt = {'5min': 328, 'daily': 86400}[stat]
            
        self.tstart = DateTime(start).secs
        self.tstop = DateTime(stop).secs if stop else DateTime(time.time(),
                                                               format='unix').secs
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
        logger.info('Getting data for %s between %s to %s', self.msid, self.datestart, self.datestop)

        # Avoid stomping on caller's filetype 'ft' values with _cache_ft()
        with _cache_ft():
            ft['content'] = self.content
            ft['msid'] = self.MSID

            if self.stat:
                ft['interval'] = self.stat
                self._get_stat_data()
            else:
                self._get_msid_data()

    def _get_stat_data(self):
        """Do the actual work of getting stats values for an MSID from HDF5 files"""
        filename = msid_files['stats'].abs
        logger.info('Opening %s', filename)
        h5 = tables.openFile(filename)
        table = h5.root.data
        times = (table.col('index') + 0.5) * self.dt
        row0, row1 = numpy.searchsorted(times, [self.tstart, self.tstop])
        table_rows = table[row0:row1]   # returns np.ndarray (structured array)
        h5.close()
        logger.info('Closed %s', filename)

        self.times = times[row0:row1]
        self.colnames = ['times']
        for colname in table_rows.dtype.names:
            # Don't like the way columns were named in the stats tables.  Fix that here.
            colname_out = _plural(colname) if colname != 'n' else 'samples' 
            setattr(self, colname_out, table_rows[colname])
            self.colnames.append(colname_out)

    def _get_msid_data(self):
        """Do the actual work of getting time and values for an MSID from HDF5 files"""

        # Get a row slice into HDF5 file for this content type that picks out
        # the required time range plus a little padding on each end.
        h5_slice = get_interval(self.content, self.tstart, self.tstop)

        # Read the TIME values either from cache or from disk.
        if times_cache['key'] == (self.content, self.tstart, self.tstop):
            logger.info('Using times_cache for %s %s to %s', self.content, self.datestart, self.datestop)
            times = times_cache['val']    # Already filtered on times_ok
            times_ok = times_cache['ok']  # For filtering MSID.val and MSID.bad
            times_all_ok = times_cache['all_ok']
        else:
            ft['msid'] = 'time'
            filename = msid_files['msid'].abs
            logger.info('Reading %s', filename)
            h5 = tables.openFile(filename)
            times_ok = ~h5.root.quality[h5_slice]
            times = h5.root.data[h5_slice]
            h5.close()

            # Filter bad times.  Last instance of bad times in archive is 2004 so
            # don't do this unless needed.  Creating a new 'times' array is much
            # more expensive than checking for numpy.all(times_ok).
            times_all_ok = numpy.all(times_ok)
            if not times_all_ok:
                times = times[times_ok]

            times_cache.update(dict(key=(self.content, self.tstart, self.tstop),
                                   val=times,
                                   ok=times_ok,
                                   all_ok=times_all_ok))

        # Extract the actual MSID values and bad values mask
        ft['msid'] = self.msid
        filename = msid_files['msid'].abs
        logger.info('Reading %s', filename)
        h5 = tables.openFile(filename)
        vals = h5.root.data[h5_slice]
        bads = h5.root.quality[h5_slice]
        h5.close()

        # Filter bad times rows if needed
        if not times_all_ok:
            logger.info('Filtering bad times values for %s', self.msid)
            bads = bads[times_ok]
            vals = vals[times_ok]

        # Slice down to exact requested time range
        row0, row1 = numpy.searchsorted(times, [self.tstart, self.tstop])
        logger.info('Slicing %s arrays [%d:%d]', self.msid, row0, row1)
        self.vals = vals[row0:row1]
        self.times = times[row0:row1]
        self.bads = bads[row0:row1]
        self.colnames = ['times', 'vals', 'bads']

    def filter_bad(self):
        """Filter out any bad values.

        After applying this method the "bads" column will be set to None to indicate
        that there are no bad values.  
        """
        if self.bads is None:
            return

        if self.stat:
            pass
        else:
            if numpy.any(self.bads):
                logger.info('Filtering bad values for %s', self.msid)
                ok = ~self.bads
                self.vals = self.vals[ok]
                self.times = self.times[ok]
            else:
                logger.info('No bad values to filter for %s', self.msid)
            self.bads = None

class MSIDset(dict):
    """Fetch a set of MSIDs from the engineering telemetry archive.

    :param msids: list of MSID names (case-insensitive)
    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry (current time if not supplied)
    :param filter_bad: automatically filter out bad values
    :param stat: return 5-minute or daily statistics ('5min' or 'daily')

    :returns: Dict-like object containing MSID instances keyed by MSID name
    """
    def __init__(self, msids, start, stop=None, filter_bad=False, stat=None):
        super(MSIDset, self).__init__()

        self.msids = msids
        self.tstart = DateTime(start).secs
        self.tstop = DateTime(stop).secs if stop else DateTime(time.time(),
                                                               format='unix').secs
        self.datestart = DateTime(self.tstart).date
        self.datestop = DateTime(self.tstop).date

        for msid in msids:
            self[msid] = MSID(msid, self.tstart, self.tstop, filter_bad=filter_bad, stat=stat)

    def interpolate(self, dt=328.0, start=None, stop=None):
        """Nearest-neighbor interpolation of all MSID values in the set to a common time sequence.
        The values are updated in-place.

        The time sequence steps uniformly by ``dt`` seconds starting at the ``start`` time for
        the set.

        :param dt: time step (sec)
        """
        # Speed could be improved by clever use of bad masking among common content types
        # (assuming no bad filtering to begin with) so that interpolation only gets done once.
        # For now just brute-force it for every MSID.
        
        tstart = DateTime(start).secs if start else self.tstart
        tstop = DateTime(stop).secs if stop else self.tstop
        self.times = numpy.arange(tstart, tstop, dt)

        for msid in self.values():
            msid.filter_bad()
            logger.info('Interpolating index for %s', msid.msid)
            indexes = Ska.Numpy.interpolate(numpy.arange(len(msid.times)),
                                            msid.times, self.times, method='nearest')
            logger.info('Slicing on indexes')
            for colname in msid.colnames:
                colvals = getattr(msid, colname)
                if colvals is not None:
                    setattr(msid, colname, colvals[indexes])

def fetch_records(start, stop, msids, dt=32.8):
    """
    Fetch data from the telemetry archive as a recarray at a uniform time spacing.

    Only records where all columns have good quality get included.  This routine
    can be substantially slower than fetch_arrays because of the interpolation
    onto a common time sequence.

    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry
    :param msids: list of MSIDs (case-insensitive)
    :param dt: sampling time (sec)

    :returns: numpy recarray with columns for time (CXC seconds) and ``msids``
    """
    import Ska.Numpy

    with _cache_ft():
        tstart, tstop, times, values, quals = _fetch(start, stop, msids)
    dt_times = numpy.arange(tstart, tstop, dt)

    len_times = len(dt_times)
    bad = numpy.zeros(len_times, dtype=bool)
    for msid in msids:
        MSID = msid.upper()
        index = Ska.Numpy.interpolate(numpy.arange(len(times[MSID])), times[MSID], dt_times, 'nearest')
        # Include also some interpolation validation check, something like (but not exactly)
        # (abs(dt_times - times[MSID][index]) > 1.05 * dt) 
        bad |= quals[MSID][index]
        values[msid] = values[MSID][index]

    ok = ~bad
    records = [dt_times[ok].copy()]
    for msid in msids:
        records.append(values[msid][ok].copy())

    out = numpy.rec.fromarrays(records, titles=['time'] + msids)
    return out

def fetch_arrays(start, stop, msids):
    """
    Fetch data for ``msids`` from the telemetry archive as arrays.

    This routine is deprecated and is retained only for back-compatibility with
    old plotting analysis scripts.

    The telemetry values are returned in three dictionaries: ``times``, ``values``,
    and ``quals``.  Each of these dictionaries contains key-value pairs for each
    of the input ``msids``.

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
    import Ska.DBI

    ft['content'] = content
    db = Ska.DBI.DBI(dbi='sqlite', server=msid_files['archfiles'].abs)

    query_row = db.fetchone('SELECT tstart, rowstart FROM archfiles '
                            'WHERE filetime < ? order by filetime desc', (tstart,))
    if not query_row:
        query_row = db.fetchone('SELECT tstart, rowstart FROM archfiles order by filetime asc')

    rowstart = query_row['rowstart']

    query_row = db.fetchone('SELECT tstop, rowstop FROM archfiles '
                            'WHERE filetime > ? order by filetime asc', (tstop,))
    if not query_row:
        query_row = db.fetchone('SELECT tstop, rowstop FROM archfiles order by filetime desc')

    rowstop = query_row['rowstop']

    return slice(rowstart, rowstop)

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
    return x + 'es' if (x.endswith('x')  or x.endswith('s')) else x + 's'

