"""
Convert dict of archive files and associated info from headers.pickle to
sqlite3 'archfiles' table.  This is a one-off after ingest_h5_archive.py
to correct an original hasty decision about storing file info.
"""
import re, os , sys
import cPickle as pickle
import collections

import Ska.Table
import Ska.DBI
from context_def import datadir, ft, files

from Chandra.Time import DateTime
import Ska.Table

filetypes = Ska.Table.read_ascii_table('filetypes.dat')

cols_map = dict(TSTART =   'tstart',    
                TSTOP =    'tstop',     
                row0 = 'rowstart',  
                row1 =  'rowstop',   
                STARTMJF = 'startmjf',  
                STARTMNF = 'startmnf',  
                STOPMJF =  'stopmjf',   
                STOPMNF =  'stopmnf',   
                CHECKSUM = 'checksum',  
                TLMVER =   'tlmver',    
                ASCDSVER = 'ascdsver',  
                REVISION = 'revision',  
                DATE =     'date')

archfiles_def = open('archfiles_def.sql').read()

for filetype in filetypes:
    ft.val.content = filetype.content.lower()

    if not os.path.exists(files.abs.contentdir) or os.path.exists(files.abs.archfiles):
        print 'Skipping', ft.val.content
        continue

    print 'Processing', ft.val.content

    print 'Creating db', files.abs.archfiles
    db = Ska.DBI.DBI(dbi='sqlite', server=files.abs.archfiles, autocommit=False)
    db.execute(archfiles_def)
    db.commit()
    
    print 'Reading', files.abs.headers
    headers = pickle.load(open(files.abs.headers))

    
    filetime_counts = collections.defaultdict(int)
    
    n = len(headers)
    for i, filename in enumerate(sorted(headers)):
        header = headers[filename]
        out = dict((outkey, header[inkey]) for inkey, outkey in cols_map.items())
        out['filename'] = filename
        filetime = int(re.search(r'(\d+)', filename).group(1))
        out['filetime'] = filetime
        filedate = DateTime(filetime).date
        out['year'], out['doy'] = re.search(r'(\d\d\d\d):(\d\d\d)', filedate).groups()
        
        filetime_counts[filetime] += 1
        if i % 100 == 0:
            print i, n, filetime, filename, header['row0'], header['row1'], '\r',
        
        db.insert(out, 'archfiles')

    db.commit()

    print
    print 'Repeats', [(k, v) for k, v in filetime_counts.items() if v > 1]
    
