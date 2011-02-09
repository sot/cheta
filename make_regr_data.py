#! /usr/bin/env python

import re, os , sys
import optparse
import shutil

from Chandra.Time import DateTime
import Ska.engarchive.fetch as fetch
import Ska.engarchive.file_defs as file_defs
import Ska.DBI
import pyyaks.context
import pyyaks.logger

loglevel = pyyaks.logger.VERBOSE
logger = pyyaks.logger.get_logger(name='make_regr_data', level=loglevel, format="%(asctime)s %(message)s")

# Globals related to Ska (flight) eng_archive
ft = fetch.ft
msid_files = pyyaks.context.ContextDict('msid_files', basedir=file_defs.msid_root)
msid_files.update(file_defs.msid_files)
arch_files = pyyaks.context.ContextDict('arch_files', basedir=file_defs.arch_root)
arch_files.update(file_defs.arch_files)

def get_options():
    parser = optparse.OptionParser()
    parser.add_option("--dry-run",
                      action="store_true",
                      help="Dry run (no actual file or database updatees)")
    parser.add_option("--start",
                      default='2010:001',
                      help="Start time")
    parser.add_option("--stop",
                      default='2010:002',
                      help="Stop time")
    parser.add_option("--data-root",
                      default="test",
                      help="Engineering archive root directory for MSID files")
    parser.add_option("--contents",
                      # default="acis2eng,acisdeahk,orbitephem0,simcoor,thm1eng",
                      default="acis2eng",
                      help="Content type to process (default = all)")
    return parser.parse_args()

def get_interval_files(content, tstart, tstop):

    ft['content'] = content
    db = Ska.DBI.DBI(dbi='sqlite', server=msid_files['archfiles'].abs)

    files = db.fetchall('SELECT * FROM archfiles '
                        'WHERE filetime >= ? AND filetime <= ? '
                        'ORDER BY filetime ASC',
                        (DateTime(tstart).secs, DateTime(tstop).secs))
    return files

def get_arch_filename(content, arch_files, filename):
    ft['content'] = content.lower()
    ft['basename'] = os.path.basename(filename)
    tstart = re.search(r'(\d+)', str(ft['basename'])).group(1)
    datestart = DateTime(tstart).date
    ft['year'], ft['doy'] = re.search(r'(\d\d\d\d):(\d\d\d)', datestart).groups()

    return arch_files['archfile'].abs


opt, args = get_options()

test_msid_files = pyyaks.context.ContextDict('msid_files', basedir=opt.data_root)
test_msid_files.update(file_defs.msid_files)
test_arch_files = pyyaks.context.ContextDict('arch_files', basedir=opt.data_root)
test_arch_files.update(file_defs.arch_files)

for content in opt.contents.split(','):
    file_records = get_interval_files(content, opt.start, opt.stop)
    tstart = file_records[0]['tstart']
    tstop = file_records[-1]['tstop']
    rowstart = file_records[0]['rowstart']
    rowstop = file_records[-1]['rowstop']
    arch_filenames = [get_arch_filename(content, arch_files, x['filename'])
                       for x in file_records]
    test_arch_filenames = [get_arch_filename(content, test_arch_files, x['filename'])
                            for x in file_records]
    for infile, outfile in zip(arch_filenames, test_arch_filenames):
        if not os.path.exists(outfile):
            test_archdir = os.path.dirname(outfile)
            if not os.path.exists(test_archdir):
                logger.info('makedirs %s' % test_archdir)
                if not opt.dry_run:
                    os.makedirs(test_archdir)
            logger.info('cp %s %s' % (infile, outfile))
            if not opt.dry_run:
                shutil.copy2(infile, outfile)

        
