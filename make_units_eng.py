"""
Make a unit_system consistent with usual OCC/FOT engineering units via P009.
"""

import pickle

import Ska.engarchive.converters
import Ska.tdb

dat = Ska.tdb.tables['tmsrment']

units_cxc = pickle.load(open('units_cxc.pkl'))

units_eng = dict((msid.upper(), unit)
                 for msid, unit in zip(dat['MSID'], dat['ENG_UNIT'])
                 if unit and msid.upper() in units_cxc)

# Use info about DEA HK telemetry from converters to add units
for col in Ska.engarchive.converters._get_deahk_cols():
    if 'unit' in col and col['unit'] == 'K':
        units_eng[col['name'].upper()] = 'DEGC'

# Make STEP unique for SIM MSIDs
units_eng['3LDRTPOS'] = 'TSCSTEP'
units_eng['3TSCPOS'] = 'TSCSTEP'
units_eng['3FAPOS'] = 'FASTEP'
units_eng['3MRMMXMV'] = 'PWMSTEP'

units_eng['HKEBOXTEMP'] = 'DEGF'

pickle.dump(units_eng, open('units_eng.pkl', 'w'))
