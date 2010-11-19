"""
Create the default unit system as found in the CXC telemetry FITS files.
"""
import glob
import cPickle as pickle
import os
import pyfits

units = {}
dirs = glob.glob('/data/cosmos2/eng_archive/data/*/arch/2010/001')
for dir_ in dirs:
    files = glob.glob(os.path.join(dir_, '*.fits.gz'))
    if not files:
        print 'No files in', dir_
        continue

    print 'Reading', files[0]
    hdus = pyfits.open(files[0])
    cols = hdus[1].columns
    for msid, unit in zip(cols.names, cols.units):
        unit = unit.strip()
        if unit:
            units[msid.upper()] = unit
    hdus.close()

# AFAIK these are the only temperature MSIDs that are actually temperature
# differences and which require special handling on conversion.
relative_temp_msids = (
    'OHRMGRD3', # RT 500 TO RT 502: CAP GRADIENT MONITOR
    'OHRMGRD6', # RT 503 TO RT 501: CAP GRADIENT MONITOR
    'OOBAGRD3', # RT 505 TO RT 504: PERISCOPE GRADIENT MONITOR
    'OOBAGRD6', # RT 507 TO RT 506: PERISCOPE GRADIENT MONITOR
    )

for msid in relative_temp_msids:
    units[msid] = 'deltaK'

pickle.dump(units, open('units_cxc.pkl', 'w'))
