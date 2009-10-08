from __future__ import with_statement

import re, os , sys
import glob
import time
import cPickle as pickle

try:
    from IPython.Debugger import Tracer
except ImportError:
    debug = lambda : None
else:
    debug = Tracer()

from Chandra.Time import DateTime
import Ska.File
import Ska.Table
import Ska.DBI
import pyyaks.logger
import pyyaks.context
import pyfits
import tables
import numpy as np

import arc5gl

FT = pyyaks.context.ContextDict('ft')
ft = FT.accessor()

datadir = 'testdata'
FILES = pyyaks.context.ContextDict('files', basedir=datadir)
FILES.update({'contentdir':   '{{ft.content}}/',
              'headers':      '{{ft.content}}/headers.pickle',
              'msiddir':      '{{ft.content}}/msid/',
              'archfiles':    '{{ft.content}}/msid/archfiles.db3',
              'colnames':      '{{ft.content}}/msid/colnames.pickle',
              'colnames_all':  '{{ft.content}}/msid/colnames_all.pickle',
              'msid':         '{{ft.content}}/msid/{{ft.msid}}.h5',
              'archdir':      '{{ft.content}}/arch/{{ft.year}}/{{ft.doy}}/',
              'archfile':     '{{ft.content}}/arch/{{ft.year}}/{{ft.doy}}/{{ft.basename}}',
              })
files = FILES.accessor()

# Set up logging
loglevel = pyyaks.logger.VERBOSE
logger = pyyaks.logger.get_logger(level=loglevel, format="%(message)s")


def main():
    # Get the archive content filetypes
    filetypes = Ska.Table.read_ascii_table('filetypes.dat')
    filetypes = filetypes[filetypes.content == 'ACIS2ENG']

    # (THINK about robust error handling.  Directory cleanup?  arc5gl stopping?)
    # debug()

    for filetype in filetypes:
        # Update attributes of global ContextValue "ft".  This is needed for
        # rendering of "files" ContextValue.
        ft.content = filetype.content.lower()
        ft.instrum = filetype.instrum.lower()

        if not os.path.exists(files.archfiles):
            logger.info('No archfiles.db3 for %s - skipping'  % ft.content)
            continue

        tmpdir = Ska.File.TempDir(dir=datadir)
        logger.verbose('Created tmpdir ' + tmpdir.name)

        with Ska.File.chdir(tmpdir.name):
            archfiles = get_archive_files(filetype)
            if archfiles:
                update_msid_files(filetype, archfiles)
        del tmpdir

def append_h5_col(dats, content, colname):
    """Append new values to an HDF5 MSID data table.

    :param dats: List of pyfits HDU data objects
    :param content: content type
    :param colname: column name
    """
    def i_colname(dat):
        """Return the index for `colname` in `dat`"""
        return list(dat.dtype.names).index(colname)

    h5 = tables.openFile(FILES['msid'].abs, mode='a')
    stacked_data = np.hstack([x.field(colname) for x in dats])
    stacked_quality = np.hstack([x.field('QUALITY')[:,i_colname(x)] for x in dats])
    logger.verbose('Appending %d items to %s' % (len(stacked_data), FILES['msid'].abs))
    h5.root.data.append(stacked_data)
    h5.root.quality.append(stacked_quality)
    h5.close()


def update_msid_files(filetype, archfiles):
    archfiles_hdr_cols = ('tstart', 'tstop', 'startmjf', 'startmnf', 'stopmjf', 'stopmnf',   
                          'checksum', 'tlmver', 'ascdsver', 'revision', 'date')
    colnames = pickle.load(open(files.colnames))
    colnames_all = pickle.load(open(files.colnames_all))
    old_colnames = colnames.copy()
    old_colnames_all = colnames_all.copy()
    
    db = Ska.DBI.DBI(dbi='sqlite', server=files.archfiles, autocommit=True)
    out = db.fetchall('SELECT max(rowstop) FROM archfiles')
    row = out[0]['max(rowstop)']

    archfiles_rows = []
    dats = []

    for i, f in enumerate(archfiles):
        # Check if filename is already in archfiles.  If so then abort further processing.
        filename = os.path.basename(f)
        if db.fetchall('SELECT filename FROM archfiles WHERE filename=?', (filename,)):
            logger.verbose('File %s already in archfiles - skipping' % filename)
            continue

        # Read FITS archive file and accumulate data into dats list and header into headers dict
        logger.info('Reading (%d / %d) %s' % (i, len(archfiles), filename))
        hdus = pyfits.open(f)
        hdu = hdus[1]
        dat = hdu.data.copy()

        # Accumlate relevant info about archfile that will be ingested into
        # MSID h5 files.  Commit info before h5 ingest so if there is a failure
        # the needed info will be available to do the repair.
        archfiles_row = dict((x, hdu.header[x.upper()]) for x in archfiles_hdr_cols)
        archfiles_row['rowstart'] = row
        archfiles_row['rowstop'] = row + len(dat)
        archfiles_row['filename'] = filename
        archfiles_row['filetime'] = int(re.search(r'(\d+)', archfiles_row['filename']).group(1))
        filedate = DateTime(archfiles_row['filetime']).date
        year, doy = (int(x) for x in re.search(r'(\d\d\d\d):(\d\d\d)', filedate).groups())
        archfiles_row['year'] = year
        archfiles_row['doy'] = doy

        hdus.close()

        # A very small number of archive files (a few) have a problem where the quality
        # column tform is specified as 3B instead of 17X (for example).  This breaks
        # things, so in this case just skip the file.
        if dat.field('QUALITY').shape[1] != len(dat.dtype.names):
            logging.warning('WARNING: skipping because of quality size mismatch: %d %d' %
                            (dat.field('QUALITY').shape[1], len(dat.dtype.names)))
            continue

        db.insert(archfiles_row, 'archfiles')
        dats.append(dat)

        # Update the running list of column names.  Colnames_all is the maximal
        # (union) set giving all column names seen in any file for this content
        # type.  Colnames is the minimal (intersection) set giving the list of
        # column names seen in every file.
        colnames_all.update(dat.dtype.names)
        colnames.intersection_update(dat.dtype.names)

        row += len(dat)

    if dats:
        logger.info('Writing accumulated column data to h5 file at ' + time.ctime())
        for colname in colnames:
            ft.msid = colname
            append_h5_col(dats, ft.content, colname)

    # If colnames or colnames_all changed then give warning and update files.
    if colnames != old_colnames:
        logger.warning('WARNING: updating %s because colnames changed: %s'
                       % (files.colnames, old_colnames ^ colnames))
        pickle.dump(colnames, open(files.colnames, 'w'))
    if colnames_all != old_colnames_all:
        logger.warning('WARNING: updating %s because colnames_all changed: %s'
                       % (files.colnames_all, colnames_all ^ old_colnames_all))
        pickle.dump(colnames_all, open(files.colnames_all, 'w'))


def get_archive_files(filetype):
    """Update FITS file archive with arc5gl and ingest files into msid (HDF5) archive"""
    
    # Retrieve CXC archive files in a temp directory with arc5gl
    arc5 = arc5gl.Arc5gl(echo=True)

    # Get datestart as the most-recent file time from archfiles table
    db = Ska.DBI.DBI(dbi='sqlite', server=files.archfiles)
    vals = db.fetchone("select max(filetime) from archfiles")
    datestart = DateTime(vals['max(filetime)']).date

    # End time (now) for archive queries
    datestop = DateTime(time.time(), format='unix').date
    # datestop = DateTime(vals['max(filetime)'] + 100000).date

    print '********** %s %s **********' % (ft.content, time.ctime())

    arc5.sendline('tstart=%s' % datestart)
    arc5.sendline('tstop=%s;' % datestop)
    arc5.sendline('get %s_eng_0{%s}' % (ft.instrum, ft.content))

    return sorted(glob.glob('*.fits.gz'))

if __name__ == '__main__':
    main()
