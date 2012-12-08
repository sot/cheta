"""
Create the default unit system as found in the CXC telemetry FITS files.
"""
import re
import glob
import argparse
import cPickle as pickle
import os
import pyfits

from Ska.engarchive.converters import _get_deahk_cols, ALIASES


def get_options(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Dry run (no actual file or database updates)")
    return parser.parse_args(args)

opt = get_options()

units = {}
dirs = glob.glob('/data/cosmos2/eng_archive/data/*/arch')
for dir_ in dirs:
    content = os.path.basename(os.path.split(dir_)[0])
    print 'Finding units in', dir_
    for dirpath, dirnames, filenames in os.walk(dir_, topdown=False):
        files = [f for f in filenames if f.endswith('.fits.gz')]
        if not files:
            print 'No fits files in', dirpath
            continue

        print 'Reading', files[0]
        hdus = pyfits.open(os.path.join(dirpath, files[0]))
        cols = hdus[1].columns
        for msid, unit in zip(cols.names, cols.units):
            unit = unit.strip()
            if unit:
                msid = msid.upper()
                if content in ALIASES:
                    msid = ALIASES[content].get(msid, msid)
                if re.match(r'(orbit|lunar|solar|angle)ephem', content):
                    msid = '{}_{}'.format(content.upper(), msid)
                units[msid.upper()] = unit
        hdus.close()
        break

# AFAIK these are the only temperature MSIDs that are actually temperature
# differences and which require special handling on conversion.
relative_temp_msids = (
    'OHRMGRD3',  # RT 500 TO RT 502: CAP GRADIENT MONITOR
    'OHRMGRD6',  # RT 503 TO RT 501: CAP GRADIENT MONITOR
    'OOBAGRD3',  # RT 505 TO RT 504: PERISCOPE GRADIENT MONITOR
    'OOBAGRD6',  # RT 507 TO RT 506: PERISCOPE GRADIENT MONITOR
    )

for msid in relative_temp_msids:
    units[msid] = 'deltaK'

units['3MRMMXMV'] = 'PWM'

# Use info about DEA HK telemetry from converters to add units
for col in _get_deahk_cols():
    if 'unit' in col:
        units[col['name'].upper()] = col['unit']

if not opt.dry_run:
    pickle.dump(units, open('units_cxc.pkl', 'w'))
else:
    print repr(units)
