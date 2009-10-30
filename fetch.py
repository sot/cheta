#!/usr/bin/env python
"""
Fetch values from the SKA telemetry archive.
"""
__docformat__ = 'restructuredtext'
import os
import sys
import re
import time
import cPickle as pickle
import logging

from Chandra.Time import DateTime
import Ska.Table
import Ska.Numpy
import Ska.DBI
import pyyaks.context
import numpy
import tables

import file_defs

from IPython.Debugger import Tracer
debug = Tracer()

SKA = os.getenv('SKA') or '/proj/sot/ska'
SKA_DATA = SKA + '/data/eng_archive'

ft = pyyaks.context.ContextDict('ft')

msid_files = pyyaks.context.ContextDict('msid_files', basedir=file_defs.msid_root) 
msid_files.update(file_defs.msid_files)

filetypes = Ska.Table.read_ascii_table('filetypes.dat')
content = dict()
for filetype in filetypes:
    ft['content'] = filetype['content'].lower()
    colnames = pickle.load(open(msid_files['colnames'].abs))
    content.update((x, ft['content'].val) for x in colnames)

def main():
    (opt, args) = get_options()
    kwargs = opt.__dict__
    
    logger = logging.getLogger('fetch')
    logger.setLevel(logging.DEBUG if opt.debug else logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    
    fetch(colspecs=args, **kwargs)

def fetch(start='2000:001:00:00:00',
          stop=None,
          dt=None,
          msids=['1pdeaat', '1pin1at']):
    """
    Fetch data from the telemetry archive.

    :param start: Start date of processing
    :param stop: Stop date of processing
    :param dt: Sampling interval (sec)
    :param msids: List of MSIDs

    :rtype: headers, values = tuple, list of tuples
    """

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

    if dt:
        dt_times = numpy.arange(tstart, tstop, dt)

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
            ft['msid'] = 'TIME'
            h5 = tables.openFile(msid_files['data'].abs)
            content_times[cm] = h5.root.data[rowslice[cm]]
            content_quals[cm] = h5.root.quality[rowslice[cm]]
            h5.close()
        
        if dt:
            ok = Ska.Numpy.interpolate(numpy.arange(len(data)), content_times[cm], dt_times, 'nearest')
        else:
            ok = (content_times[cm] >= tstart) & (content_times[cm] <= tstop)

        values[msid] = data[ok]
        times[msid] = content_times[cm][ok]
        quals[msid] = qual[ok] | content_quals[cm][ok]

    return times, values, quals

def get_interval(content, tstart, tstop):
    """
    Get the approximate row and time intervals that enclose the specified ``tstart`` and
    ``tstop`` times for the ``content`` type.

    :returns: rowslice, timestart, timestop
    """
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

def write_output(columns, out_format, attr):
    values = tuple(getattr(x, attr) for x in columns)

    field_seps = {'dmascii': ' ',
                  'space': ' ',
                  'csv': ',',
                  'tab': '\t',
                  'rdb': '\t'}
    field_sep = field_seps.get(out_format)
                 
    if out_format == 'dmascii' and attr == 'name':
        print '#',
    if out_format in field_seps:
        print field_sep.join(str(x) for x in values)
    elif out_format == 'fits':
        raise RuntimeError('Sorry, FITS output format not yet supported')

    return values

def get_options():
    from optparse import OptionParser
    parser = OptionParser(usage='fetch.py [options] msid1 [msid2 ...]')
    parser.set_defaults()
    parser.add_option("--obsid",
                      type="int",
                      help="Return data for OBSID",
                      )
    parser.add_option("--outfile",
                      help="File for fetch output (default = stdout)",
                      )
    parser.add_option("--statusfile",
                      help="Write out fetch status each status-interval seconds",
                      )
    parser.add_option("--status-interval",
                      default=2,
                      type="float",
                      help="Time interval between statusfile update and file size check (sec)",
                      )
    parser.add_option("--max-size",
                      type="int",
                      help="Approximate output file size limit (default = None)",
                      )
    parser.add_option("--start",
                      help="Start date of processing",
                      )
    parser.add_option("--stop",
                      help="Stop date of processing",
                      )
    parser.add_option("--dt",
                      type='float',
                      default=32.8,
                      help="Sampling interval (sec)",
                      )
    parser.add_option("--file-format",
                      default='csv',
                      choices=['csv','rdb','space','fits','tab','dmascii'],
                      help="Output data format (csv rdb space fits tab dmascii)",
                      )
    parser.add_option("--time-format",
                      default='secs',
                      choices=['date','greta','secs','jd','mjd','fits','unix'],
                      help="Output time format (date greta secs jd mjd fits unix)",
                      )
    parser.add_option("--debug",
                      action="store_true",
                      default=False,
                      help="Enable debug output",
                      )
    (opt, args) = parser.parse_args()
    if not args:
        args = ['1pdeaat', '1pin1at']

    return opt, args

if __name__ == '__main__':
    main()
    
