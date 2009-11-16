#!/usr/bin/env python
"""
Fetch values from the SKA telemetry archive.
"""
from __future__ import with_statement  # only for python 2.5

__docformat__ = 'restructuredtext'
import os
import time
import contextlib
import cPickle as pickle

import numpy
import tables
import Ska.Table
import pyyaks.context

import file_defs

SKA = os.getenv('SKA') or '/proj/sot/ska'
SKA_DATA = SKA + '/data/eng_archive'

ft = pyyaks.context.ContextDict('ft')

msid_files = pyyaks.context.ContextDict('msid_files', basedir=file_defs.msid_root) 
msid_files.update(file_defs.msid_files)

filetypes = Ska.Table.read_ascii_table(os.path.join(SKA_DATA, 'filetypes.dat'))
content = dict()
for filetype in filetypes:
    ft['content'] = filetype['content'].lower()
    colnames = pickle.load(open(msid_files['colnames'].abs))
    content.update((x, ft['content'].val) for x in colnames)

fetch_cache = dict(key=None,
                   times=None,
                   quals=None)

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

    with cache_ft():
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

    The telemetry values are returned in three dictionaries: ``times``, ``values``,
    and ``quals``.  Each of these dictionaries contains key-value pairs for each
    of the input ``msids``.

    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry
    :param msids: list of MSIDs (case-insensitive)

    :returns: times, values, quals
    """
    
    with cache_ft():
        tstart, tstop, _times, _values, _quals = _fetch(start, stop, msids)

    times = {}
    values = {}
    quals = {}

    for msid in msids:
        MSID = msid.upper()
        i0, i1 = numpy.searchsorted(_times[MSID], [tstart, tstop])
        times[msid] = _times[MSID][i0:i1]
        values[msid] = _values[MSID][i0:i1]
        quals[msid] = _quals[MSID][i0:i1]

    return times, values, quals

def fetch_array(start, stop, msid):
    """
    Fetch data for single ``msid`` from the telemetry archive as an array.  

    The telemetry values are returned in three arrays: ``times``, ``values``,
    and ``quals``.  

    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry
    :param msid: MSID (case-insensitive)

    :returns: times, values, quals
    """
    
    with cache_ft():
        tstart, tstop, _times, _values, _quals = _fetch(start, stop, [msid])

    MSID = msid.upper()
    i0, i1 = numpy.searchsorted(_times[MSID], [tstart, tstop])

    return _times[MSID][i0:i1], _values[MSID][i0:i1], _quals[MSID][i0:i1]

def _fetch(start, stop, msids):
    """
    Fetch data from the telemetry archive.  Returns a bit more than the requested
    time range so that calling routine can filter appropriately.  This routine is
    not intended for external use.

    :param start: start date of telemetry (Chandra.Time compatible)
    :param stop: stop date of telemetry
    :param msids: list of MSIDs (case-insensitive)

    :returns: times, values, quals
    """
    from Chandra.Time import DateTime

    # Convert input date values to time in CXC seconds.  tstop defaults to Now.
    tstart = DateTime(start).secs
    tstop = DateTime(stop).secs if stop else DateTime(time.time(), format='unix').secs

    msids = [x.upper() for x in msids]

    times = dict()
    values = dict()
    quals = dict()

    for msid in msids:
        if msid not in content:
            raise ValueError('MSID %s is not in Eng Archive' % msid)
        cm = content[msid]
        ft['content'] = cm
        ft['msid'] = msid
        rowslice = get_interval(cm, tstart, tstop)

        h5 = tables.openFile(msid_files['data'].abs)
        data = h5.root.data[rowslice]
        qual = h5.root.quality[rowslice]
        h5.close()

        key = (cm, tstart, tstop)
        if key == fetch_cache['key']:
            content_times = fetch_cache['times']
            content_quals = fetch_cache['quals']
        else:
            ft['msid'] = 'time'
            h5 = tables.openFile(msid_files['msid'].abs)
            content_times = h5.root.data[rowslice]
            content_quals = h5.root.quality[rowslice]
            h5.close()
            fetch_cache.update(dict(key=key,
                                    times=content_times,
                                    quals=content_quals))

        values[msid] = data
        times[msid] = content_times
        quals[msid] = qual | content_quals

    return tstart, tstop, times, values, quals

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
    Get the approximate row and time intervals that enclose the specified ``tstart`` and
    ``tstop`` times for the ``content`` type.

    :returns: rowslice, timestart, timestop
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
def cache_ft():
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

