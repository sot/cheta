#!/usr/bin/env python

"""
Fix bad values that are in the engineering archive.

Typically this is needed because of bad telemetry that is not marked
as such in the CXC archive.  This code will mark a single value or
range of values as bad (via the quality flag) and re-run the statistics
computations.  The database (HDF5 file) values are updated in place.
"""

import argparse

import numpy as np
import tables

import pyyaks.context
import pyyaks.logger
from Ska.engarchive import fetch
import Ska.engarchive.file_defs as file_defs
from Chandra.Time import DateTime


def get_opt():
    parser = argparse.ArgumentParser(description='Fix bad values in eng archive')
    parser.add_argument('--msid',
                        default='aorate3',
                        type=str,
                        help='MSID name')
    parser.add_argument('--start',
                        default='2013:146:16:12:44.600',
                        help='Start time of bad values')
    parser.add_argument('--stop',
                        help='Stop time of bad values')
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Dry run (no actual file or database updatees)")
    parser.add_argument("--data-root",
                        default=".",
                        help="Engineering archive root directory for MSID and arch files")

    args = parser.parse_args()
    return args

opt = get_opt()

# Set up infrastructure to directly access HDF5 files
ft = fetch.ft
msid_files = pyyaks.context.ContextDict('msid_files',
                                        basedir=(opt.data_root or file_defs.msid_root))
msid_files.update(file_defs.msid_files)

# Set up fetch so it reads from opt.data_root
fetch.msid_files.basedir = opt.data_root

# Set up logging
loglevel = pyyaks.logger.INFO
logger = pyyaks.logger.get_logger(name='fix_bad_values', level=loglevel,
                                  format="%(asctime)s %(message)s")

msid = opt.msid.lower()
MSID = opt.msid.upper()
ft['content'] = fetch.content[MSID]

# Get the relevant row slice covering the requested time span for this content type
tstart = DateTime(opt.start).secs - 0.001
stop = DateTime(opt.stop or opt.start)
tstop = stop.secs + 0.001
row_slice = fetch.get_interval(ft['content'].val, tstart, tstop)


# Load the time values and find indexes corresponding to start / stop times
ft['msid'] = 'TIME'

filename = msid_files['data'].abs
logger.info('Reading TIME file {}'.format(filename))

h5 = tables.openFile(filename)
times = h5.root.data[row_slice]
h5.close()

# Index values that need to be fixed are those within the specified time range, offset by
# the beginning index of the row slice.
fix_idxs = np.flatnonzero((tstart <= times) & (times <= tstop)) + row_slice.start

# Open the MSID HDF5 data file and set the corresponding quality flags to True (=> bad)
ft['msid'] = MSID
filename = msid_files['msid'].abs
logger.info('Reading MSID file {}'.format(filename))

h5 = tables.openFile(filename, 'a')
try:
    for idx in fix_idxs:
        logger.info('{}.data[{}] = {}'.format(msid, idx, h5.root.data[idx]))
        logger.info('Changing {}.quality[{}] from {} to True'
                    .format(msid, idx, h5.root.quality[idx]))
        if not opt.dry_run:
            h5.root.quality[idx] = True
finally:
    h5.close()
