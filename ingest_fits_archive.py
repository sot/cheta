import time
import re, os , sys
import glob

import numpy as np
import pexpect

import Ska.Table
from Chandra.Time import DateTime
import Ska.arc5gl as arc5gl

filetypes = Ska.Table.read_ascii_table('filetypes.dat')
if len(sys.argv) == 2:
    filetypes = filetypes[ filetypes['content'] == sys.argv[1].upper() ]

for filetype in filetypes:
    try:
        content = filetype['content'].lower()
        arc5gl_query = filetype['arc5gl_query'].lower()

        outdir = os.path.abspath(os.path.join('/data/cosmos2/tlm', content))
        if os.path.exists(outdir):
            print 'Skipping', content, 'at', time.ctime()
            continue
        else:
            os.makedirs(outdir)

        os.chdir(outdir)
        arc5 = arc5gl.Arc5gl()

        print '**********', content, time.ctime(), '***********'
        print '  cd ' + outdir
        arc5.sendline('cd ' + outdir)

        for year in range(2000, 2010):
            if os.path.exists('/pool14/wink/stoptom'):
                raise RuntimeError('Stopped by sherry')
            datestart = '%d:001:00:00:00' % year
            datestop = '%d:001:00:00:00' % (year+1)

            sys.stdout.flush()
            print '  tstart=%s' % datestart
            print '  tstop=%s' % datestop
            print '  get %s{%s}' % (arc5gl_query, content)

            arc5.sendline('tstart=%s' % datestart)
            arc5.sendline('tstop=%s;' % datestop)
            arc5.sendline('get %s{%s}' % (arc5gl_query, content))

        open('.process', 'w')

    finally:
        # explicitly close connection to archive
        if 'arc5' in globals():
            del arc5


        
