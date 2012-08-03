#!/usr/bin/env python

import re
import os
import sys
import glob
import time
import cPickle as pickle
import optparse
import shutil
import itertools

from Chandra.Time import DateTime
import Ska.File
import Ska.DBI
import Ska.Numpy
import pyyaks.logger
import pyyaks.context
import pyfits
import tables
import numpy as np
import scipy.stats.mstats

import Ska.engarchive.fetch as fetch
import Ska.engarchive.converters as converters
import Ska.engarchive.file_defs as file_defs
import Ska.engarchive.derived as derived
import Ska.arc5gl

# Configure fetch.MSID to cache recent results for performance in
# derived parameter updates.
fetch.CACHE = True

def get_options():
    parser = optparse.OptionParser()
    parser.add_option("--dry-run",
                      action="store_true",
                      help="Dry run (no actual file or database updatees)")
    parser.add_option("--no-full",
                      action="store_false",
                      dest="update_full",
                      default=True,
                      help="Do not fetch files from archive and update full-resolution MSID archive")
    parser.add_option("--no-stats",
                      action="store_false",
                      dest="update_stats",
                      default=True,
                      help="Do not update 5 minute and daily stats archive")
    parser.add_option("--fix-misorders",
                      action="store_true",
                      default=False,  
                      help="Fix errors in ingest file order")
    parser.add_option("--truncate",
                      help="Truncate archive after <date> (CAUTION!!)")
    parser.add_option("--max-lookback-time",
                      type='float',
                      default=60,
                      help="Maximum look back time for updating statistics (days)")
    parser.add_option("--date-now",
                      default=DateTime().date,
                      help="Set effective processing date for testing (default=NOW)")
    parser.add_option("--max-gap",
                      type='float',
                      help="Maximum time gap between archive files")
    parser.add_option("--max-arch-files",
                      type='int',
                      default=100,
                      help="Maximum number of archive files to ingest at once")
    parser.add_option("--data-root",
                      default=".",
                      help="Engineering archive root directory for MSID and arch files")
    parser.add_option("--occ",
                      action="store_true",
                      help="Running on the OCC GRETA network (no arc5gl)")
    parser.add_option("--content",
                      action='append',
                      help="Content type to process [match regex] (default = all)")
    return parser.parse_args()

opt, args = get_options()

ft = fetch.ft
msid_files = pyyaks.context.ContextDict('msid_files',
                                        basedir=(opt.data_root or file_defs.msid_root))
msid_files.update(file_defs.msid_files)
arch_files = pyyaks.context.ContextDict('arch_files',
                                        basedir=(opt.data_root or file_defs.arch_root))
arch_files.update(file_defs.arch_files)

# Set up fetch so it will first try to read from opt.data_root if that is
# provided as an option and exists, and if not fall back to the default of
# fetch.ENG_ARCHIVE.  Fetch is a read-only process so this is safe when testing.
if opt.data_root:
    fetch.msid_files.basedir = ':'.join([opt.data_root, fetch.ENG_ARCHIVE])

# Set up logging
loglevel = pyyaks.logger.VERBOSE
logger = pyyaks.logger.get_logger(name='engarchive', level=loglevel, format="%(asctime)s %(message)s")

archfiles_hdr_cols = ('tstart', 'tstop', 'startmjf', 'startmnf', 'stopmjf', 'stopmnf',   
                      'tlmver', 'ascdsver', 'revision', 'date')

def main():
    logger.info('Run time options: \n{}'.format(opt))
    logger.info('Update_archive file: {}'.format(os.path.abspath(__file__)))
    logger.info('Fetch module file: {}'.format(os.path.abspath(fetch.__file__)))
    logger.info('')

    # Get the archive content filetypes
    filetypes = fetch.filetypes
    if opt.content:
        contents = [x.upper() for x in opt.content]
        filetypes = [x for x in filetypes
                     if any(re.match(y, x.content) for y in contents)]

    # (THINK about robust error handling.  Directory cleanup?  arc5gl stopping?)
    # debug()

    for filetype in filetypes:
        # Update attributes of global ContextValue "ft".  This is needed for
        # rendering of "files" ContextValue.
        ft['content'] = filetype.content.lower()
        colnames = [x for x in pickle.load(open(msid_files['colnames'].abs))
                    if x not in fetch.IGNORE_COLNAMES]

        if not os.path.exists(msid_files['archfiles'].abs):
            logger.info('No archfiles.db3 for %s - skipping'  % ft['content'])
            continue

        logger.info('Processing %s content type', ft['content'])

        if opt.truncate:
            truncate_archive(filetype, opt.truncate)
            continue

        if opt.fix_misorders:
            misorder_time = fix_misorders(filetype)
            if misorder_time:
                for colname in colnames:
                    del_stats(colname, misorder_time, 'daily')
                    del_stats(colname, misorder_time, '5min')
            continue
        
        if opt.update_full:
            if filetype['instrum'] == 'DERIVED':
                update_derived(filetype)
            else:
                update_archive(filetype)

        if opt.update_stats:
            for colname in colnames:
                msid = update_stats(colname, 'daily')
                update_stats(colname, '5min', msid)

def fix_misorders(filetype):
    """Fix problems in the eng archive where archive files were ingested out of
    time order.  This results in a non-monotonic times in the MSID hdf5 files
    and subsequently corrupts the stats files.  This routine looks for
    discontinuities in rowstart assuming filename ordering and swaps neighbors.
    One needs to verify in advance (--dry-run --fix-misorders --content ...)
    that this will be an adequate fix.

    Example::

      update_archive.py --dry-run --fix-misorders --content misc3eng
      update_archive.py --fix-misorders --content misc3eng >& fix_misc3.log 
      update_archive.py --content misc3eng --max-lookback-time 100 >>& fix_misc3.log 

    In the --dry-run it is important to verify that the gap is really just from
    two mis-ordered files that can be swapped.  Look at the rowstart,rowstop values
    in the filename-ordered list.

    :param filetype: filetype
    :returns: minimum time for all misorders found
    """
    colnames = pickle.load(open(msid_files['colnames'].abs))
    
    # Setup db handle with autocommit=False so that error along the way aborts insert transactions
    db = Ska.DBI.DBI(dbi='sqlite', server=msid_files['archfiles'].abs, autocommit=False)

    # Get misordered archive files
    archfiles = db.fetchall('SELECT * FROM archfiles order by filename')
    bads = archfiles['rowstart'][1:] - archfiles['rowstart'][:-1] < 0

    if not np.any(bads):
        logger.info('No misorders')
        return

    for bad in np.flatnonzero(bads):
        i2_0, i1_0 = archfiles['rowstart'][bad:bad+2]
        i2_1, i1_1 = archfiles['rowstop'][bad:bad+2]

        # Update hdf5 file for each column (MSIDs + TIME, MJF, etc)
        for colname in colnames:
            ft['msid'] = colname
            logger.info('Fixing %s', msid_files['msid'].abs)
            if not opt.dry_run:
                h5 = tables.openFile(msid_files['msid'].abs, mode='a')
                hrd = h5.root.data
                hrq = h5.root.quality

                hrd1 = hrd[i1_0:i1_1]
                hrd2 = hrd[i2_0:i2_1]
                hrd[i1_0 : i1_0 + len(hrd2)] = hrd2
                hrd[i1_0 + len(hrd2): i2_1] = hrd1

                hrq1 = hrq[i1_0:i1_1]
                hrq2 = hrq[i2_0:i2_1]
                hrq[i1_0 : i1_0 + len(hrq2)] = hrq2
                hrq[i1_0 + len(hrq2): i2_1] = hrq1

                h5.close()

        # Update the archfiles table
        cmd = 'UPDATE archfiles SET '
        cols = ['rowstart', 'rowstop']
        cmd += ', '.join(['%s=?' % x for x in cols])
        cmd += ' WHERE filename=?' 
        rowstart1 = i1_0
        rowstop1 = rowstart1 + i2_1 - i2_0
        rowstart2 = rowstop1 + 1
        rowstop2 = i2_1
        vals1 = [rowstart1, rowstop1, archfiles['filename'][bad]]
        vals2 = [rowstart2, rowstop2, archfiles['filename'][bad+1]]
        logger.info('Running %s %s', cmd, vals1)
        logger.info('Running %s %s', cmd, vals2)

        logger.info('Swapping rows %s for %s', [i1_0, i1_1, i2_0, i2_1], filetype.content)
        logger.info('%s', archfiles[bad-3:bad+5])
        logger.info('')

        if not opt.dry_run:
            db.execute(cmd, [x.tolist() for x in vals1])
            db.execute(cmd, [x.tolist() for x in vals2])
            db.commit()

    return np.min(archfiles['tstart'][bads])


def del_stats(colname, time0, interval):
    """Delete all rows in ``interval`` stats file for column ``colname`` that
    occur after time ``time0`` - ``interval``.  This is used to fix problems
    that result from a file misorder.  Subsequent runs of update_stats will
    refresh the values correctly.
    """
    dt = {'5min': 328,
          'daily': 86400}[interval]

    ft['msid'] = colname
    ft['interval'] = interval
    stats_file = msid_files['stats'].abs
    logger.info('Fixing stats file %s after time %s', stats_file, DateTime(time0).date)

    stats = tables.openFile(stats_file, mode='a', 
                            filters=tables.Filters(complevel=5, complib='zlib'))
    index0 = time0 // dt - 1
    indexes = stats.root.data.col('index')[:]
    row0 = np.searchsorted(indexes, [index0])[0] - 1
    if opt.dry_run:
        n_del = len(stats.root.data) - row0
    else:
        n_del = stats.root.data.removeRows(row0, len(stats.root.data))
    logger.info('Deleted %d rows from row %s (%s) to end', n_del, row0, DateTime(indexes[row0] * dt).date)
    stats.close()


def calc_stats_vals(msid, rows, indexes, interval):
    quantiles = (1, 5, 16, 50, 84, 95, 99)
    cols_stats = ('index', 'n', 'val')
    n_out = len(rows) - 1
    msid_dtype = msid.vals.dtype
    msid_is_numeric = not msid_dtype.name.startswith('string')
    # Predeclare numpy arrays of correct type and sufficient size for accumulating results.
    out = dict(index=np.ndarray((n_out,), dtype=np.int32),
               n=np.ndarray((n_out,), dtype=np.int32),
               val=np.ndarray((n_out,), dtype=msid_dtype),
               )
    if msid_is_numeric:
        cols_stats += ('min', 'max', 'mean')
        out.update(dict(min=np.ndarray((n_out,), dtype=msid_dtype),
                        max=np.ndarray((n_out,), dtype=msid_dtype),
                        mean=np.ndarray((n_out,), dtype=np.float32),))
        if interval == 'daily':
            cols_stats += ('std',) + tuple('p%02d' % x for x in quantiles)
            out['std'] = np.ndarray((n_out,), dtype=msid_dtype)
            out.update(('p%02d' % x, np.ndarray((n_out,), dtype=msid_dtype)) for x in quantiles)
    i = 0
    for row0, row1, index in itertools.izip(rows[:-1], rows[1:], indexes[:-1]):
        vals = msid.vals[row0:row1]
        times = msid.times[row0:row1]
        n_vals = len(vals)
        if n_vals > 0:
            out['index'][i] = index
            out['n'][i] = n_vals
            out['val'][i] = vals[n_vals // 2]
            if msid_is_numeric:
                if n_vals <= 2:
                    dts = np.ones(n_vals, dtype=np.float64)
                else:
                    dts = np.empty(n_vals, dtype=np.float64)
                    dts[0] = times[1] - times[0]
                    dts[-1] = times[-1] - times[-2]
                    dts[1:-1] = ((times[1:-1] - times[:-2])
                                 + (times[2:] - times[1:-1])) / 2.0
                    negs = dts < 0.0
                    if np.any(negs):
                        times_dts = [(DateTime(t).date, dt)
                                     for t, dt in zip(times[negs], dts[negs])]
                        logger.warning('WARNING - negative dts in {} at {}'
                                       .format(msid.MSID, times_dts))

                    # Clip to range 0.001 to 300.0.  The low bound is just there
                    # for data with identical time stamps.  This shouldn't happen
                    # but in practice might.  The 300.0 represents 5 minutes and
                    # is the largest normal time interval.  Data near large gaps
                    # will get a weight of 5 mins.
                    dts.clip(0.001, 300.0, out=dts)
                sum_dts = np.sum(dts)

                out['min'][i] = np.min(vals)
                out['max'][i] = np.max(vals)
                out['mean'][i] = np.sum(dts * vals) / sum_dts
                if interval == 'daily':
                    # biased weighted estimator of variance (N should be big enough)
                    # http://en.wikipedia.org/wiki/Mean_square_weighted_deviation
                    sigma_sq = np.sum(dts * (vals - out['mean'][i]) ** 2) / sum_dts
                    out['std'][i] = np.sqrt(sigma_sq)
                    quant_vals = scipy.stats.mstats.mquantiles(vals, np.array(quantiles) / 100.0)
                    for quant_val, quantile in zip(quant_vals, quantiles):
                        out['p%02d' % quantile][i] = quant_val
            i += 1
        
    return np.rec.fromarrays([out[x][:i] for x in cols_stats], names=cols_stats)

def update_stats(colname, interval, msid=None):
    dt = {'5min': 328,
          'daily': 86400}[interval]

    ft['msid'] = colname
    ft['interval'] = interval
    stats_file = msid_files['stats'].abs
    logger.info('Updating stats file %s', stats_file)

    if not os.path.exists(msid_files['statsdir'].abs):
        os.makedirs(msid_files['statsdir'].abs)
    stats = tables.openFile(stats_file, mode='a', 
                            filters=tables.Filters(complevel=5, complib='zlib'))
    try:
        index0 = stats.root.data.cols.index[-1] + 1
    except tables.NoSuchNodeError:
        index0 = DateTime('2000:001:00:00:00').secs // dt

    # Get all new data. time0 is the fetch start time which nominally starts at
    # 500 sec before the last available record.  However some MSIDs may not
    # be sampled for years at a time so once the archive is built and kept
    # up to date then do not look back beyond a certain point.
    if msid is None:
        # fetch telemetry plus a little extra
        time0 = max(DateTime(opt.date_now).secs - opt.max_lookback_time * 86400,
                    index0 * dt - 500)  
        time1 = DateTime(opt.date_now).secs
        msid = fetch.MSID(colname, time0, time1, filter_bad=True)

    if len(msid.times) > 0:
        indexes = np.arange(index0, msid.times[-1] / dt, dtype=np.int32)
        times = indexes * dt

        if len(times) > 2:
            rows = np.searchsorted(msid.times, times)
            vals_stats = calc_stats_vals(msid, rows, indexes, interval)
            if not opt.dry_run:
                # Don't change the following logic in order to add stats data
                # on the same pass as creating the table.  Tried it and
                # something got broken so that there was a single bad record
                # after the first bunch.
                try:
                    stats.root.data.append(vals_stats)
                    logger.info('  Adding %d records', len(vals_stats))
                except tables.NoSuchNodeError:
                    table = stats.createTable(stats.root, 'data', vals_stats,
                                              "%s sampling" % interval, expectedrows=2e7)

    stats.root.data.flush()
    stats.close()

    return msid

def update_derived(filetype):
    """Update full resolution MSID archive files for derived parameters with ``filetype``
    """
    # Get the last H5 table row from archfiles table for this content type
    db = Ska.DBI.DBI(dbi='sqlite', server=msid_files['archfiles'].abs)
    last_row = db.fetchone('SELECT * FROM archfiles ORDER BY filetime DESC')

    # Set the starting index from the last row in archfiles.  This
    # uses Python slicing conventions so that the previous "end"
    # value is exactly the next "start" values, e.g. [index0:index1]
    # For derived parameters we have stopmjf <==> index1 
    index0 = last_row['stopmjf']  
    
    # Get the full set of rootparams for all colnames
    colnames = pickle.load(open(msid_files['colnames'].abs))
    colnames = [x for x in colnames if x.startswith('DP_')]
    msids = set()
    for colname in colnames:
        dp_class = getattr(derived, colname)
        dp = dp_class()
        msids = msids.union([x.upper() for x in dp.rootparams])
        time_step = dp.time_step  # will be the same for every DP

    # Find the last time in archive for each of the content types
    # occuring in the list of rootparam MSIDs.
    # fetch.content is a mapping from MSID to content type
    last_times = {}
    ft_content = ft['content'].val
    for msid in msids:
        ft['msid'] = 'TIME'
        content = ft['content'] = fetch.content[msid]
        if content not in last_times:
            h5 = tables.openFile(fetch.msid_files['msid'].abs, mode='r')
            last_times[content] = h5.root.data[-1]
            h5.close()
    last_time = min(last_times.values()) - 1000
    ft['content'] = ft_content

    # Make a list of indexes that will correspond to the index/time ranges
    # for each pseudo-"archfile".  In this context an archfile just specifies
    # the time range covered by an ingest, but is needed by fetch to roughly
    # locate rows in the H5 file for fast queries.  Each archfile is 50000 sec
    # long, and when updating the database no more than 1000000 seconds of
    # telemetry will be read at one time.  
    archfile_time_step = 200000.0
    max_archfiles = int(1000000.0 / archfile_time_step)

    # Read data out to either date_now or the last available time in telemetry.
    # opt.date_now could be set in the past for testing.
    index_step = int(round(archfile_time_step / time_step))
    time1 = min(DateTime(opt.date_now).secs, last_time)
    index1 = int(time1 / time_step)
    indexes = np.arange(index0, index1, index_step)

    archfiles = []
    for index0, index1 in zip(indexes[:-1], indexes[1:]):
        archfiles.append('{}:{}:{}'.format(filetype['content'], index0, index1))
        if len(archfiles) == max_archfiles or index1 == indexes[-1]:
            update_msid_files(filetype, archfiles)
            logger.verbose('update_msid_files(filetype={}, archfiles={})'
                           .format(str(filetype), archfiles))
            archfiles = []

def update_archive(filetype):
    """Get new CXC archive files for ``filetype`` and update the full-resolution MSID
    archive files.
    """
    if opt.occ:
        dirname = arch_files['stagedir'].abs
        if not os.path.exists(dirname):
            os.makedirs(dirname)
    else:
        tmpdir = Ska.File.TempDir(dir=file_defs.arch_root)
        dirname = tmpdir.name

    with Ska.File.chdir(dirname): 
        archfiles = get_archive_files(filetype)
        if archfiles:
            archfiles_processed = update_msid_files(filetype, archfiles)
            move_archive_files(filetype, archfiles_processed)

def append_h5_col(dats, colname, files_overlaps):
    """Append new values to an HDF5 MSID data table.

    :param dats: List of pyfits HDU data objects
    :param colname: column name
    """
    def i_colname(dat):
        """Return the index for `colname` in `dat`"""
        return list(dat.dtype.names).index(colname)

    h5 = tables.openFile(msid_files['msid'].abs, mode='a')
    stacked_data = np.hstack([x[colname] for x in dats])
    stacked_quality = np.hstack([x['QUALITY'][:, i_colname(x)] for x in dats])
    logger.verbose('Appending %d items to %s' % (len(stacked_data), msid_files['msid'].abs))
    if not opt.dry_run:
        h5.root.data.append(stacked_data)
        h5.root.quality.append(stacked_quality)

    # Remove overlaps in the archive files where file0['tstop'] > file1['tstart'].
    # Do this by setting the TIME column quality flag for the overlapping rows
    # in file0.  files_overlaps is a list of 2-tuples with consequetive files that
    # overlap.
    if colname == 'TIME':
        for file0, file1 in files_overlaps:
            times = h5.root.data[file0['rowstart']:file0['rowstop']]
            bad_rowstart = np.searchsorted(times, file1['tstart']) + file0['rowstart']
            bad_rowstop = file0['rowstop']
            if not opt.dry_run:
                logger.verbose('Removing overlapping data in rows {0}:{1}'.format(
                    bad_rowstart, bad_rowstop))
                if  bad_rowstop > bad_rowstart:
                    h5.root.quality[bad_rowstart:bad_rowstop] = True
                else:
                    logger.verbose('WARNING: Unexpected null file overlap file0=%s file1=%s'
                                   % (file0, file1))

    h5.close()


def truncate_archive(filetype, date):
    """Truncate msid and statfiles for every archive file after date (to nearest
    year:doy)
    """
    colnames = pickle.load(open(msid_files['colnames'].abs))
    
    date = DateTime(date).date
    year, doy = date[0:4], date[5:8]

    # Setup db handle with autocommit=False so that error along the way aborts insert transactions
    db = Ska.DBI.DBI(dbi='sqlite', server=msid_files['archfiles'].abs, autocommit=False)

    # Get the earliest row number from the archfiles table where year>=year and doy=>doy
    out = db.fetchall('SELECT rowstart FROM archfiles WHERE year>={0} AND doy>={1}'.format(year, doy))
    if len(out) == 0:
        return
    rowstart = out['rowstart'].min()
    time0 = DateTime("{0}:{1}:00:00:00".format(year, doy)).secs

    for colname in colnames:
        ft['msid'] = colname
        if not opt.dry_run:
            h5 = tables.openFile(msid_files['msid'].abs, mode='a')
            h5.root.data.truncate(rowstart)
            h5.root.quality.truncate(rowstart)
            h5.close()
        logger.verbose('Removed rows from {0} for filetype {1}:{2}'.format(
            rowstart, filetype['content'], colname))
        
        # Delete the 5min and daily stats, with a little extra margin
        del_stats(colname, time0, '5min')
        del_stats(colname, time0, 'daily')

    if not opt.dry_run:
        db.execute('DELETE FROM archfiles WHERE year>={0} AND doy>={1}'.format(year, doy))
        db.commit()
    logger.verbose('DELETE FROM archfiles WHERE year>={0} AND doy>={1}'.format(year, doy))


def read_archfile(i, f, filetype, row, colnames, archfiles, db):
    """Read filename ``f`` with index ``i`` (position within list of filenames).  The
    file has type ``filetype`` and will be added to MSID file at row index ``row``.
    ``colnames`` is the list of column names for the content type (not used here).
    """
    # Check if filename is already in archfiles.  If so then abort further processing.
    filename = os.path.basename(f)
    if db.fetchall('SELECT filename FROM archfiles WHERE filename=?', (filename,)):
        logger.verbose('File %s already in archfiles - unlinking and skipping' % f)
        os.unlink(f)
        return None, None

    # Read FITS archive file and accumulate data into dats list and header into headers dict
    logger.info('Reading (%d / %d) %s' % (i, len(archfiles), filename))
    hdus = pyfits.open(f)
    hdu = hdus[1]
    dat = converters.convert(hdu.data, filetype['content'])

    # Accumlate relevant info about archfile that will be ingested into
    # MSID h5 files.  Commit info before h5 ingest so if there is a failure
    # the needed info will be available to do the repair.
    archfiles_row = dict((x, hdu.header.get(x.upper())) for x in archfiles_hdr_cols)
    archfiles_row['checksum'] = hdu.header.get('checksum') or hdu._checksum
    archfiles_row['rowstart'] = row
    archfiles_row['rowstop'] = row + len(dat)
    archfiles_row['filename'] = filename
    archfiles_row['filetime'] = int(re.search(r'(\d+)', archfiles_row['filename']).group(1))
    filedate = DateTime(archfiles_row['filetime']).date
    year, doy = (int(x) for x in re.search(r'(\d\d\d\d):(\d\d\d)', filedate).groups())
    archfiles_row['year'] = year
    archfiles_row['doy'] = doy
    hdus.close()

    return dat, archfiles_row


def read_derived(i, filename, filetype, row, colnames, archfiles, db):
    """Read derived data using eng_archive and derived computation classes.
    ``filename`` has format <content>_<index0>_<index1> where <content>
    is the content type (e.g. "dp_thermal128"), <index0> is the start index for
    the new data and index1 is the end index (using Python slicing convention
    index0:index1).  Args ``i``, ``filetype``, and ``row`` are as in
    read_archive().  ``row`` must equal <index0>.  ``colnames`` is the list of
    column names for the content type.
    """
    # Check if filename is already in archfiles.  If so then abort further processing.

    if db.fetchall('SELECT filename FROM archfiles WHERE filename=?', (filename,)):
        logger.verbose('File %s already in archfiles - skipping' % filename)
        return None, None

    # f has format <content>_<index0>_<index1>
    # <content> has format dp_<content><mnf_step> e.g. dp_thermal128
    content, index0, index1 = filename.split(':')
    index0 = int(index0)
    index1 = int(index1)
    mnf_step = int(re.search(r'(\d+)$', content).group(1))
    time_step = mnf_step * derived.MNF_TIME
    times = time_step * np.arange(index0, index1)
    
    logger.info('Reading (%d / %d) %s' % (i, len(archfiles), filename))
    vals = {}
    bads = np.zeros((len(times), len(colnames)), dtype=np.bool)
    for i, colname in enumerate(colnames):
        if colname == 'TIME':
            vals[colname] = times
            bads[:, i] = False
        else:
            dp_class = getattr(Ska.engarchive.derived, colname.upper())
            dp = dp_class()
            dataset = dp.fetch(times[0] - 1000, times[-1] + 1000)
            ok = (index0 <= dataset.indexes) & (dataset.indexes < index1)
            vals[colname] = dp.calc(dataset)[ok]
            bads[:, i] = dataset.bads[ok]

    vals['QUALITY'] = bads
    dat = Ska.Numpy.structured_array(vals, list(colnames) + ['QUALITY'])

    # Accumlate relevant info about archfile that will be ingested into
    # MSID h5 files.  Commit info before h5 ingest so if there is a failure
    # the needed info will be available to do the repair.
    date = DateTime(times[0]).date
    year, doy = date[0:4], date[5:8]
    archfiles_row = dict(filename=filename,
                         filetime=int(index0 * time_step),
                         year=year,
                         doy=doy,
                         tstart=times[0],
                         tstop=times[-1],
                         rowstart=row,
                         rowstop=row + len(dat),
                         startmjf=index0,
                         stopmjf=index1,
                         date=date)

    return dat, archfiles_row


def update_msid_files(filetype, archfiles):
    colnames = pickle.load(open(msid_files['colnames'].abs))
    colnames_all = pickle.load(open(msid_files['colnames_all'].abs))
    old_colnames = colnames.copy()
    old_colnames_all = colnames_all.copy()
    
    # Setup db handle with autocommit=False so that error along the way aborts insert transactions
    db = Ska.DBI.DBI(dbi='sqlite', server=msid_files['archfiles'].abs, autocommit=False)

    # Get the last row number from the archfiles table
    out = db.fetchone('SELECT max(rowstop) FROM archfiles')
    row = out['max(rowstop)']
    last_archfile = db.fetchone('SELECT * FROM archfiles where rowstop=?', (row,))

    archfiles_overlaps = []
    archfiles_rows = []
    dats = []
    archfiles_processed = []

    content_is_derived = (filetype['instrum'] == 'DERIVED')

    for i, f in enumerate(archfiles):
        get_data = (read_derived if content_is_derived else read_archfile)
        dat, archfiles_row = get_data(i, f, filetype, row, colnames, archfiles, db)
        if dat is None:
            continue

        # Ensure that the time gap between the end of the last ingested archive
        # file and the start of this one is less than opt.max_gap (or
        # filetype-based defaults).  If this fails then break out of the
        # archfiles processing but continue on to ingest any previously
        # successful archfiles
        time_gap = archfiles_row['tstart'] - last_archfile['tstop']
        max_gap = opt.max_gap
        if max_gap is None:
            if filetype['instrum'] in ['EPHEM', 'DERIVED']:
                max_gap = 601
            elif filetype['content'] == 'ACISDEAHK':
                max_gap = 10000
                # From P.Plucinsky 2011-09-23
                # If ACIS is executing an Event Histogram run while in FMT1,
                # the telemetry stream will saturate.  The amount of time for
                # an opening in the telemetry to appear such that DEA HKP
                # packets can get out is a bit indeterminate.  The histograms
                # integrate for 5400s and then they are telemetered.  I would
                # suggest 6000s, but perhaps you would want to double that to
                # 12000s.
            else:
                max_gap = 32.9
        if time_gap > max_gap:
            logger.warning('WARNING: found gap of %.2f secs between archfiles %s and %s',
                           time_gap, last_archfile['filename'], archfiles_row['filename'])
            break
        elif time_gap < 0:
            # Overlapping archfiles - deal with this in append_h5_col
            archfiles_overlaps.append((last_archfile, archfiles_row))

        # Update the last_archfile values. 
        last_archfile = archfiles_row

        # A very small number of archive files (a few) have a problem where the
        # quality column tform is specified as 3B instead of 17X (for example).
        # This breaks things, so in this case just skip the file.  However
        # since last_archfile is set above the gap check considers this file to
        # have been ingested.
        if not content_is_derived and dat['QUALITY'].shape[1] != len(dat.dtype.names):
            logging.warning('WARNING: skipping because of quality size mismatch: %d %d' %
                            (dat['QUALITY'].shape[1], len(dat.dtype.names)))
            continue

        # Mark the archfile as ingested in the database and add to list for
        # subsequent relocation into arch_files archive.  In the case of a gap
        # where ingest is stopped before all archfiles are processed, this will
        # leave files either in a tmp dir (HEAD) or in the stage dir (OCC).
        # In the latter case this allows for successful processing later when the
        # gap gets filled.
        archfiles_processed.append(f)
        if not opt.dry_run:
            db.insert(archfiles_row, 'archfiles')

        # Capture the data for subsequent storage in the hdf5 files
        dats.append(dat)

        # Update the running list of column names.  Colnames_all is the maximal
        # (union) set giving all column names seen in any file for this content
        # type.  Colnames is the minimal (intersection) set giving the list of
        # column names seen in every file.
        colnames_all.update(dat.dtype.names)
        colnames.intersection_update(dat.dtype.names)

        row += len(dat)

    if dats:
        logger.verbose('Writing accumulated column data to h5 file at ' + time.ctime())
        for colname in colnames:
            ft['msid'] = colname
            append_h5_col(dats, colname, archfiles_overlaps)

    # Assuming everything worked now commit the db inserts that signify the
    # new archive files have been processed
    if not opt.dry_run:
        db.commit()

    # If colnames or colnames_all changed then give warning and update files.
    if colnames != old_colnames:
        logger.warning('WARNING: updating %s because colnames changed: %s'
                       % (msid_files['colnames'].abs, old_colnames ^ colnames))
        if not opt.dry_run:
            pickle.dump(colnames, open(msid_files['colnames'].abs, 'w'))
    if colnames_all != old_colnames_all:
        logger.warning('WARNING: updating %s because colnames_all changed: %s'
                       % (msid_files['colnames_all'].abs, colnames_all ^ old_colnames_all))
        if not opt.dry_run:
            pickle.dump(colnames_all, open(msid_files['colnames_all'].abs, 'w'))

    return archfiles_processed

def move_archive_files(filetype, archfiles):
    ft['content'] = filetype.content.lower()

    stagedir = arch_files['stagedir'].abs
    if not os.path.exists(stagedir):
        os.makedirs(stagedir)

    for f in archfiles:
        if not os.path.exists(f):
            continue
        ft['basename'] = os.path.basename(f)
        tstart = re.search(r'(\d+)', str(ft['basename'])).group(1)
        datestart = DateTime(tstart).date
        ft['year'], ft['doy'] = re.search(r'(\d\d\d\d):(\d\d\d)', datestart).groups()

        archdir = arch_files['archdir'].abs
        archfile = arch_files['archfile'].abs

        if not os.path.exists(archdir):
            os.makedirs(archdir)

        if not os.path.exists(archfile):
            logger.info('mv %s %s' % (os.path.abspath(f), archfile))
            if not opt.dry_run:
                if not opt.occ:
                    shutil.copy2(f, stagedir)
                shutil.move(f, archfile)

        if os.path.exists(f):
            logger.verbose('Unlinking %s' % os.path.abspath(f))
            os.unlink(f)

def get_archive_files(filetype):
    """Update FITS file archive with arc5gl and ingest files into msid (HDF5) archive"""
    
    # If running on the OCC GRETA network the cwd is a staging directory that
    # could already have files.  Also used in testing.
    # Don't return more than opt.max_arch_files files at once because of memory
    # issues on gretasot.  This only comes up when there has been some problem or stoppage.
    files = sorted(glob.glob(filetype['fileglob']))
    if opt.occ or files:
        return sorted(files)[:opt.max_arch_files]

    # Retrieve CXC archive files in a temp directory with arc5gl
    arc5 = Ska.arc5gl.Arc5gl(echo=True)

    # Get datestart as the most-recent file time from archfiles table
    db = Ska.DBI.DBI(dbi='sqlite', server=msid_files['archfiles'].abs)
    vals = db.fetchone("select max(filetime) from archfiles")
    datestart = DateTime(vals['max(filetime)'])

    # End time for archive queries (minimum of start + max_query_days and NOW)
    datestop = DateTime(opt.date_now)

    # For *ephem0 the query needs to extend well into the future
    # to guarantee getting all available files.  This is the archives fault.
    if filetype['level'] == 'L0' and filetype['instrum'] == 'EPHEM':
        datestop = datestop + 50

    # For instrum==EPHEM break queries into time ranges no longer than
    # 100000 sec each.  EPHEM files are at least 7 days long and generated
    # no more often than every ~3 days so this should work.
    n_queries = (1 if filetype['instrum'] != 'EPHEM'
          else 1 + round((datestop.secs - datestart.secs) / 100000.))
    times = np.linspace(datestart.secs, datestop.secs, n_queries + 1)

    logger.info('********** %s %s **********' % (ft['content'], time.ctime()))

    for t0, t1 in zip(times[:-1], times[1:]):
        arc5.sendline('tstart=%s' % DateTime(t0).date)
        arc5.sendline('tstop=%s' % DateTime(t1).date)
        arc5.sendline('get %s' % filetype['arc5gl_query'].lower())

    return sorted(glob.glob(filetype['fileglob']))

if __name__ == '__main__':
    main()
