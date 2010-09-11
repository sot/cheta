"""
Fix overlaps within the original archive and h5 ingest.  These are due to
problems with different versioned files that cover same time range being
retrieved by the archive.
"""

import sys
import os
import shutil

import tables
from Chandra.Time import DateTime
import Ska.DBI
import Ska.Table

from context_def import datadir, ft, files

filetypes = Ska.Table.read_ascii_table('filetypes.dat')
if len(sys.argv) == 2:
    filetypes = filetypes[ filetypes['content'] == sys.argv[1].upper() ]

for filetype in filetypes:
    # Update attributes of global ContextValue "ft".  This is needed for
    # rendering of "files" ContextValue.
    print filetype.content

    ft['content'] = filetype['content'].lower()
    ft['msid'] = 'TIME'

    # archive files
    if not os.path.exists(files['archfiles'].abs) or os.path.exists(files['oldmsid'].abs + '.bak'):
        print 'Skipping', ft['content']
        continue

    # Make backup!
    print 'Copying ', files['oldmsid'].abs, files['oldmsid'].abs + '.bak'
    shutil.copy2(files['oldmsid'].abs, files['oldmsid'].abs + '.bak')

    # Read the list of archive files that were used to build the MSID h5 files
    db = Ska.DBI.DBI(dbi='sqlite', server=files['archfiles'].abs)
    archfiles = db.fetchall('select * from archfiles order by tstart asc')
    db.conn.close()
    
    # Find archive files that overlap in time (tstart : tstop).  
    overlaps = archfiles[1:].tstart - archfiles[:-1].tstop < -1
    file0s = archfiles[:-1][overlaps]
    file1s = archfiles[1:][overlaps]

    # Open the TIME.h5 file for this content type 
    h5 = tables.openFile(files['oldmsid'].abs, mode='a')

    # Iterate through overlapping files and set bad quality in TIME for rows
    # coming from the file with lower revision
    for file0, file1 in zip(file0s, file1s):
        t0 = file0.tstart
        badfile = file0 if file0.revision < file1.revision else file1
        print file0.filename, file0.revision, file1.revision, \
              '%9d %9d %9d %9d' % (file0.tstart, file0.tstop, file1.tstart, file1.tstop), \
              'Setting TIME rows', badfile.rowstart, badfile.rowstop, 'to bad quality'
        h5.root.quality[badfile.rowstart:badfile.rowstop] = True

    h5.close()

