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

    # Attributes for each content type represented by msids list
    rowslice = dict()    # slice object that selects hdf5 row ranges
    timestart = dict()   # start time of arch file containing tstart or first available
    timestop = dict()    # stop time of arch file containing tstop or last available

    # Go through msids and use the archfiles database to get the time and row ranges
    for msid in msids:
        if msid not in content:
            raise ValueError('MSID %s is not in Eng Archive' % msid)
        if content[msid] not in rowslice:
            cm = content[msid]
            rowslice[cm], timestart[cm], timestop[cm] = get_interval(cm, tstart, tstop)
    
    # Determine final tstart, tstop values incorporating knowledge of times available
    # in MSID eng archive files.  Then generate array of times.
    tstart = max([tstart] + list(timestart.values()))
    tstop = min([tstop] + list(timestop.values()))

    content_times = dict()              # time stamps for each content type
    content_quals = dict()              # quality flags for each content type
    times = dict()
    values = dict()
    quals = dict()

    for msid in msids:
        cm = content[msid]
        ft['content'] = cm
        ft['msid'] = msid

        h5 = tables.openFile(msid_files['data'].abs)
        data = h5.root.data[rowslice[cm]]
        qual = h5.root.quality[rowslice[cm]]
        h5.close()

        if cm not in content_times:
            ft['msid'] = 'time'
            h5 = tables.openFile(msid_files['msid'].abs)
            content_times[cm] = h5.root.data[rowslice[cm]]
            content_quals[cm] = h5.root.quality[rowslice[cm]]
            h5.close()
        
        values[msid] = data
        times[msid] = content_times[cm]
        quals[msid] = qual | content_quals[cm]

    return tstart, tstop, times, values, quals

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
    timestart = query_row['tstart']

    query_row = db.fetchone('SELECT tstop, rowstop FROM archfiles '
                            'WHERE filetime > ? order by filetime asc', (tstop,))

    if not query_row:
        query_row = db.fetchone('SELECT tstop, rowstop FROM archfiles order by filetime desc')

    rowstop = query_row['rowstop']
    timestop = query_row['tstop']

    return slice(rowstart, rowstop), timestart, timestop

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

