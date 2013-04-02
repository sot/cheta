#!/usr/bin/env python

"""
Regression test for fetching from the Ska engineering archive.

This reads full-resolution, 5 minute, and daily values from a representative
sample of MSIDs for each content type.

The following example shows how to run the regression test assuming that
the updated version of Ska.engarchive is installed in the Ska test
environment::

  # In window 1.  This creates fetch_regr_<ska_flight_version>
  % ska
  % ./test_fetch_regr.py

  # In window 2.  This creates fetch_regr_<ska_test_version>
  # If not on GRETA, set the ENG_ARCHIVE env var to point at the flight archive
  % setenv ENG_ARCHIVE /proj/sot/ska/data/eng_archive

  % skatest
  % ./test_fetch_regr.py

  % diff fetch_regr_<ska_flight_version> fetch_regr_<ska_test_version>

Help::

  ska-ccosmos$ ./test_fetch_regr.py --help
  usage: test_fetch_regr.py [-h] [--n-msids N_MSIDS] [--n-samp N_SAMP]
                            [--start START] [--outroot OUTROOT]

  Regression test for fetch

  optional arguments:
    -h, --help         show this help message and exit
    --n-msids N_MSIDS  Max msids per content type
    --n-samp N_SAMP    Max samples of each msid
    --start START      Start
    --outroot OUTROOT  Output file root

"""


import hashlib
import argparse
import collections

import Ska.Shell
from Chandra.Time import DateTime
import numpy as np

from Ska.engarchive import fetch
from astropy.utils.console import ProgressBar


parser = argparse.ArgumentParser(description='Regression test for fetch')
parser.add_argument('--n-msids',
                    default=4,
                    type=int,
                    help='Max msids per content type')

parser.add_argument('--n-samp',
                    default=10000,
                    type=int,
                    help='Max samples of each msid')

parser.add_argument('--start',
                    type=str,
                    default='2012:149:10:00:00',
                    help='Start')

parser.add_argument('--outroot',
                    type=str,
                    default='fetch_regr_',
                    help='Output file root')

args = parser.parse_args()

start = DateTime(args.start)

contents = collections.defaultdict(list)
for msid, content_type in fetch.content.iteritems():
    contents[content_type].append(msid)

for content_type, msids in contents.items():
    msids = sorted(msids)
    idxs = np.linspace(0, len(msids) - 1, args.n_msids).astype(int)
    contents[content_type] = [msids[idx] for idx in sorted(set(idxs))]

version = Ska.Shell.bash('ska_version')[0]
print("Writing regression results to {}".format(args.outroot + version))
with open(args.outroot + version, 'w') as fout:
    with ProgressBar(len(contents)) as bar:
        for content_type in sorted(contents):
            bar.update()
            msids = contents[content_type]
            for msid in msids:
                for stat, days in ((None, 1),
                                   ('5min', 4),
                                   ('daily', 300)):
                    md5 = hashlib.md5()
                    dat = fetch.MSID(msid, start, start + days, stat=stat)
                    n_samp = min(args.n_samp, len(dat.vals))
                    idxs = np.linspace(0, n_samp - 1, n_samp).astype(int)
                    for val in dat.vals.take(idxs):
                        md5.update(repr(val))
                    if dat.bads is not None:
                        for bad in dat.bads.take(idxs):
                            md5.update(repr(bad))
                    out = '{:6s} {:16s} {:20s} {}'.format(stat, content_type, msid, md5.hexdigest())
                    print >>fout, out
