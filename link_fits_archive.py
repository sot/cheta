import re, os , sys
import glob
import time
import shutil
# from IPython.Debugger import Tracer; set_trace = Tracer()

from Chandra.Time import DateTime
import Ska.Table
import pyyaks.logger

from file_defs import ft, files, ofiles, OFILES
# import arc5gl

def main():
    filetypes = Ska.Table.read_ascii_table('filetypes.dat')
    filetypes = filetypes[filetypes.pipe == 'ENG0']
    # filetypes = filetypes[filetypes.content == 'ACIS4ENG']

    datestop = DateTime(time.time(), format='unix').date

    # set_trace()
    loglevel = pyyaks.logger.INFO
    logger = pyyaks.logger.get_logger(level=loglevel, format="%(message)s")

    for filetype in filetypes:
        ft.content = filetype.content.lower()

        if not os.path.exists(files.msiddir):
            os.makedirs(files.msiddir)
            
        for f in glob.glob(os.path.join(OFILES['contentdir'].abs, '*.fits.gz')):
            ft.basename = os.path.basename(f)
            tstart = re.search(r'(\d+)', ft.basename).group(1)
            datestart = DateTime(tstart).date
            ft.year, ft.doy = re.search(r'(\d\d\d\d):(\d\d\d)', datestart).groups()

            if not os.path.exists(files.archdir):
                os.makedirs(files.archdir)
                
            if not os.path.exists(files.archfile):
                logger.info('ln -s %s %s' % (f, files.archfile))
                os.symlink(f, files.archfile)

if __name__ == '__main__':
    main()
