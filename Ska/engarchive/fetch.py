#!/usr/bin/env python
"""
Fetch values from the Ska engineering telemetry archive.
"""
__docformat__ = 'restructuredtext'
import os
import time
import contextlib
import cPickle as pickle
import logging
import operator

import numpy
import tables
import asciitable
import pyyaks.context

from . import file_defs
from . import units
from Chandra.Time import DateTime

SKA = os.getenv('SKA') or '/proj/sot/ska'
ENG_ARCHIVE = os.getenv('ENG_ARCHIVE') or SKA + '/data/eng_archive'
IGNORE_COLNAMES = ('TIME', 'MJF', 'MNF', 'TLM_FMT')

# Context dictionary to provide context for msid_files
ft = pyyaks.context.ContextDict('ft')

# Global (eng_archive) definition of file names
msid_files = pyyaks.context.ContextDict('msid_files', basedir=ENG_ARCHIVE) 
msid_files.update(file_defs.msid_files)

# Module-level values defining available content types and column (MSID) names
filetypes = asciitable.read(os.path.join(ENG_ARCHIVE, 'filetypes.dat'))
content = dict()
for filetype in filetypes:
    ft['content'] = filetype['content'].lower()
    try:
        colnames = pickle.load(open(msid_files['colnames'].abs))
        content.update((x, ft['content'].val) for x in colnames
                       if x not in IGNORE_COLNAMES)
    except IOError:
        pass

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
    units.set_units(unit_system)

def read_bad_times(table):
    """Include a list of bad times from ``table`` in the fetch module
    ``bad_times`` registry.  This routine can be called multiple times with
    different tables and the bad times will be appended to the registry.  The
    table can include any number of bad time interval specifications, one per
    line.  A bad time interval line has three columns separated by whitespace,
    e.g.::

      aogbias1  2008:292:00:00:00  2008:297:00:00:00
      
    The MSID name is not case sensitive and the time values can be in any ``DateTime`` format.
    Blank lines and any line starting with the # character are ignored.
    """
    bad_times = asciitable.read(table, Reader=asciitable.NoHeader, names=['msid', 'start', 'stop'])

    for msid, start, stop in bad_times:
        msid_bad_times.setdefault(msid.upper(), []).append((start, stop))
    
# Set up bad times dict
msid_bad_times = dict()
try:
    read_bad_times(os.path.join(ENG_ARCHIVE, 'msid_bad_times.dat'))
except IOError:
    pass

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
        self.unit = units.units_out.get(self.MSID)
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

        self.bads = None
        self.times = times[row0:row1]
        self.colnames = ['times']
        for colname in table_rows.dtype.names:
            # Don't like the way columns were named in the stats tables.  Fix that here.
            colname_out = _plural(colname) if colname != 'n' else 'samples' 

            if colname_out in ('vals', 'mins', 'maxes', 'means',
                               'p01s', 'p05s', 'p16s', 'p50s', 'p84s', 'p95s', 'p99s'):
                vals = units.convert(self.MSID, table_rows[colname])
            elif colname_out == 'stds':
                vals = units.convert(self.MSID, table_rows[colname], delta_val=True)
            else:
                vals = table_rows[colname]
                
            setattr(self, colname_out, vals)
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
        self.vals = units.convert(self.MSID, vals[row0:row1])
        self.times = times[row0:row1]
        self.bads = bads[row0:row1]
        self.colnames = ['times', 'vals', 'bads']

    def filter_bad(self, bads=None):
        """Filter out any bad values.

        After applying this method the "bads" column will be set to None to indicate
        that there are no bad values.  

        :param bads: Bad values mask.  If not supplied then self.bads is used.
        """
        # If a bad mask is provided then override any existing bad mask for the MSID
        if bads is not None:
            self.bads = bads
            
        # Nothing to do if bads is None (indicating bad values already filtered)
        if self.bads is None:
            return

        if numpy.any(self.bads):
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
        - Supply both ``start`` and ``stop`` values where each is a single value
          in a valid DateTime format.
        - Supply an ``table`` parameter in the form of a 2-column table of
          start and stop dates (space-delimited) or the name of a file with data
          in the same format.

        The ``table`` parameter must be supplied as a table or the name of a
        table file, for example::

          bad_times = ['2008:292:00:00:00 2008:297:00:00:00',
                       '2008:305:00:12:00 2008:305:00:12:03',
                       '2010:101:00:01:12 2010:101:00:01:25']
          msid.filter_bad_times(table=bad_times)
          msid.filter_bad_times(table='msid_bad_times.dat')

        :param start: Start of time interval to exclude (any DateTime format is acceptable)
        :param stop: End of time interval to exclude (any DateTime format is acceptable)
        :param table: Two-column table (start, stop) of bad time intervals
        """
        if table is not None:
            bad_times = asciitable.read(table, Reader=asciitable.NoHeader, names=['start', 'stop'])
        elif start is None and stop is None:
            bad_times = msid_bad_times.get(self.MSID, [])
        elif start is None or stop is None:
            raise ValueError('filter_times requires either 2 args (start, stop) or no args')
        else:
            bad_times = [(start, stop)]
            
        for start, stop in bad_times:
            tstart = DateTime(start).secs
            tstop = DateTime(stop).secs
            if tstart > tstop:
                raise ValueError("Start time %s must be less than stop time %s" % (start, stop))

            if tstop < self.times[0] or tstart > self.times[-1]:
                continue

            logger.info('Filtering times between %s and %s' % (start, stop))
            ok = (self.times < tstart) | (self.times > tstop)
            colnames = (x for x in self.colnames)
            for colname in colnames:
                setattr(self, colname, getattr(self, colname)[ok])

    def write_zip(self, filename, append=False):
        """Write MSID to a zip file named ``filename``

        Within the zip archive the data for this MSID will be stored in csv format with
        the name <msid_name>.csv.

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

        f = zipfile.ZipFile(filename, ('a' if append and os.path.exists(filename) else 'w')) 
        info = zipfile.ZipInfo(self.msid + '.csv')
        info.external_attr = 0664 << 16L # Set permissions 
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
            raise ValueError('op = "{}" is not in allowed values: {}'.format(
                    op, sorted(ops.keys())))

        # Do local version of bad value filtering
        if self.bads is not None and numpy.any(self.bads):
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
        i_starts = numpy.flatnonzero(starts)
        if op(vals[-1], val):
            i_starts = i_starts[:-1]

        # If first entry is val then the telemetry starts during an interval
        # and there will be an extra end transition that must be removed.
        i_ends = numpy.flatnonzero(ends)
        if op(vals[0], val):
            i_ends = i_ends[1:]

        tstarts = times[i_starts]
        tstop = times[i_ends]
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
        if self.bads is not None and numpy.any(self.bads):
            ok = ~self.bads
            vals = self.vals[ok]
            times = self.times[ok]
        else:
            vals = self.vals
            times = self.times

        if len(self.vals) < 2:
            raise ValueError('Filtered data length must be at least 2')

        transitions = numpy.hstack([[True], vals[:-1] != vals[1:], [True]])
        t0 = times[0] - (times[1] - times[0]) / 2
        t1 = times[-1] + (times[-1] - times[-2]) / 2
        midtimes = numpy.hstack([[t0], (times[:-1] + times[1:]) / 2, [t1]])

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
            self[msid] = MSID(msid, self.tstart, self.tstop, filter_bad=False, stat=stat)

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
                                
        Since ``aorate1`` and ``aorate2`` both have content type of ``pcad3eng`` they
        will be filtered as a group and will remain with the same sampling.  This
        will allow something like::

          plot(msids['aorate1'].vals, msids['aorate2'].vals)

        Likewise the two gyro count MSIDs would be filtered as a group.  If this
        group-filtering is not the desired behavior one can always call the individual
        MSID.filter_bad() function for each MSID in the set::

          for msid in msids.values():
              msid.filter_bad()
        """
        for content in set(x.content for x in self.values()):
            bads = None

            msids = [x for x in self.values() if x.content == content]
            for msid in msids:
                if bads is None:
                    bads = msid.bads.copy()
                else:
                    bads |= msid.bads

            for msid in msids:
                msid.filter_bad(bads)

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
        import Ska.Numpy
        
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

