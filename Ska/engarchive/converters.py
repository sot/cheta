from itertools import izip
import logging
import os
import numpy
import sys

MODULE = sys.modules[__name__]
logger = logging.getLogger('engarchive')

class NoValidDataError(Exception):
    pass

def convert(dat, content):
    try:
        converter = getattr(MODULE, content.lower())
    except AttributeError:
        converter = lambda x: x.copy()

    return converter(dat)

def generic_converter(prefix=None, add_quality=False):
    """Convert an input FITS recarray assuming that it has a TIME column.
    If ``add_prefix`` is set then add ``content_`` as a prefix
    to the data column names.  If ``add_quality`` is set then add a QUALITY
    column with all values False.
    """
    def _convert(dat):
        colnames = dat.dtype.names
        colnames_out = [x.upper() for x in colnames]
        if prefix:
            # Note to self: never change an enclosed reference, i.e. don't do
            # prefix = prefix.upper() + '_'
            # You will lose an hour again figuring this out if so.
            PREFIX = prefix.upper() + '_'
            colnames_out = [(x if x in ('TIME', 'QUALITY') else PREFIX + x)
                            for x in colnames_out]

        descrs = [(x,) +  y[1:] for x, y in zip(colnames_out, dat.dtype.descr)]
        arrays = [dat.field(x) for x in colnames]

        if add_quality:
            quals = numpy.zeros((len(dat), len(colnames) + 1), dtype=numpy.bool)
            descrs += [('QUALITY', numpy.bool, (len(colnames) + 1,))]
            arrays += [quals]

        return numpy.rec.fromarrays(arrays, dtype=descrs)

    return _convert

orbitephem0 = generic_converter('orbitephem0', add_quality=True)
lunarephem0 = generic_converter('lunarephem0', add_quality=True)
solarephem0 = generic_converter('solarephem0', add_quality=True)
orbitephem1 = generic_converter('orbitephem1', add_quality=True)
lunarephem1 = generic_converter('lunarephem1', add_quality=True)
solarephem1 = generic_converter('solarephem1', add_quality=True)
angleephem = generic_converter(add_quality=True)

def acisdeahk(dat):
    """Take the archive ACIS-0 DEA HKP data and convert to a format that is 
    consistent with normal eng0 files.  ACIS-0 housekeeping has data stored
    in query-records, one row per DEA statistic query.  Gather all the 
    time-synced queries corresponding to columns for the acis0hkp table
    and put into a single row.  Write out to temp files and modify self->{arch_files}.
    """
    
    logger.info('Converting acisdeahk data to eng0 format')

    cols = _get_deahk_cols()
    col_query_ids = tuple(x['query_id'] for x in cols)
    col_names = tuple(x['name'].upper() for x in cols)

    # Filter only entries with ccd_id >= 10 which indicates data from the I/F control
    dat = pyfits_to_recarray(dat)
    rows = dat[dat['CCD_ID'] >= 10]
    if len(rows) == 0:
        raise NoValidDataError()
    
    # Go through input data one row (query) at a time and assemble contemporaneous
    # queries into a single row with a column for each query value.
    # Collect each assembled row into %data_out for writing to a FITS bin table
    block_idxs = 1 + numpy.flatnonzero(numpy.abs(rows['TIME'][1:] - rows['TIME'][:-1]) > 0.001)
    block_idxs = numpy.hstack([[0], block_idxs, [len(rows)]])
    query_val_tus = rows['QUERY_VAL_TU']
    query_vals = rows['QUERY_VAL']
    query_ids = rows['QUERY_ID']
    times = rows['TIME']

    outs = []
    for i0, i1 in izip(block_idxs[:-1], block_idxs[1:]):
        # Map query_id to an index into rows for each row in the block
        id_idxs = dict((query_ids[i], i) for i in range(i0, i1))

        # Make tuples of the values and qual flags corresponding to each DEAHK_COLUMN
        bads = tuple(query_id not in id_idxs for query_id in col_query_ids)
        vals = tuple((0.0 if bad else query_vals[id_idxs[query_id]])
                     for bad, query_id in izip(bads, col_query_ids))
        val_tus = tuple((0 if bad else query_val_tus[id_idxs[query_id]])
                     for bad, query_id in izip(bads, col_query_ids))

        # Now have another pass at finding bad values.  Take these out now so the
        # 5min and daily stats are not frequently corrupted.
        bads = tuple(True if (val_tu == 65535 or numpy.isnan(val)) else bad
                     for bad, val, val_tu in izip(bads, vals, val_tus))

        quality = (False, False) + bads
        outs.append((times[i0], quality) + vals)

    dtype = [('TIME', numpy.float64),
              ('QUALITY', numpy.bool, (len(col_names) + 2,))]
    dtype += [(col_name, numpy.float32) for col_name in col_names]
    
    return numpy.rec.fromrecords(outs, dtype=dtype)

def _get_deahk_cols():
    out = [
        {
            "query_id": 1, 
            "name": "tmp_bep_pcb", 
            "unit": "K", 
            "descr": "DPA Thermistor 1 - BEP PC Board"
        }, 
        {
            "query_id": 2, 
            "name": "tmp_bep_osc", 
            "unit": "K", 
            "descr": "DPA Thermistor 2 - BEP Oscillator"
        }, 
        {
            "query_id": 3, 
            "name": "tmp_fep0_mong", 
            "unit": "K", 
            "descr": "DPA Thermistor 3 - FEP 0 Mongoose"
        }, 
        {
            "query_id": 4, 
            "name": "tmp_fep0_pcb", 
            "unit": "K", 
            "descr": "DPA Thermistor 4 - FEP 0 PC Board"
        }, 
        {
            "query_id": 5, 
            "name": "tmp_fep0_actel", 
            "unit": "K", 
            "descr": "DPA Thermistor 5 - FEP 0 ACTEL"
        }, 
        {
            "query_id": 6, 
            "name": "tmp_fep0_ram", 
            "unit": "K", 
            "descr": "DPA Thermistor 6 - FEP 0 RAM"
        }, 
        {
            "query_id": 7, 
            "name": "tmp_fep0_fb", 
            "unit": "K", 
            "descr": "DPA Thermistor 7 - FEP 0 Frame Buf"
        }, 
        {
            "query_id": 8, 
            "name": "tmp_fep1_mong", 
            "unit": "K", 
            "descr": "DPA Thermistor 8 - FEP 1 Mongoose"
        }, 
        {
            "query_id": 9, 
            "name": "tmp_fep1_pcb", 
            "unit": "K", 
            "descr": "DPA Thermistor 9 - FEP 1 PC Board"
        }, 
        {
            "query_id": 10, 
            "name": "tmp_fep1_actel", 
            "unit": "K", 
            "descr": "DPA Thermistor 10 - FEP 1 ACTEL"
        }, 
        {
            "query_id": 11, 
            "name": "tmp_fep1_ram", 
            "unit": "K", 
            "descr": "DPA Thermistor 11 - FEP 1 RAM"
        }, 
        {
            "query_id": 12, 
            "name": "tmp_fep1_fb", 
            "unit": "K", 
            "descr": "DPA Thermistor 12 - FEP 1 Frame Buf"
        }, 
        {
            "query_id": 15, 
            "name": "fptemp_12", 
            "unit": "K", 
            "descr": "Focal Plane Temp. Board 12"
        }, 
        {
            "query_id": 16, 
            "name": "fptemp_11", 
            "unit": "K", 
            "descr": "Focal Plane Temp. Board 11"
        }, 
        {
            "query_id": 17, 
            "name": "dpagndref1", 
            "unit": "V", 
            "descr": "DPA Ground Reference 1"
        }, 
        {
            "query_id": 18, 
            "name": "dpa5vhka", 
            "unit": "V", 
            "descr": "DPA 5V Housekeeping A"
        }, 
        {
            "query_id": 19, 
            "name": "dpagndref2", 
            "unit": "V", 
            "descr": "DPA Ground Reference 2"
        }, 
        {
            "query_id": 20, 
            "name": "dpa5vhkb", 
            "unit": "V", 
            "descr": "DPA 5V Housekeeping B"
        }, 
        {
            "query_id": 25, 
            "name": "dea28volta", 
            "unit": "V", 
            "descr": "Primary Raw DEA 28V DC"
        }, 
        {
            "query_id": 26, 
            "name": "dea24volta", 
            "unit": "V", 
            "descr": "Primary Raw DEA 24V DC"
        }, 
        {
            "query_id": 27, 
            "name": "deam15volta", 
            "unit": "V", 
            "descr": "Primary Raw DEA -15.5V"
        }, 
        {
            "query_id": 28, 
            "name": "deap15volta", 
            "unit": "V", 
            "descr": "Primary Raw DEA +15.5V"
        }, 
        {
            "query_id": 29, 
            "name": "deam6volta", 
            "unit": "V", 
            "descr": "Primary Raw DEA -6V DC"
        }, 
        {
            "query_id": 30, 
            "name": "deap6volta", 
            "unit": "V", 
            "descr": "Primary Raw DEA +6V DC"
        }, 
        {
            "query_id": 31, 
            "name": "rad_pcb_a", 
            "descr": "Relative Dose Rad. Monitor Side A"
        }, 
        {
            "query_id": 32, 
            "name": "gnd_1", 
            "unit": "V", 
            "descr": "Interface Ground Reference"
        }, 
        {
            "query_id": 33, 
            "name": "dea28voltb", 
            "unit": "V", 
            "descr": "Backup Raw DEA 28V DC"
        }, 
        {
            "query_id": 34, 
            "name": "dea24voltb", 
            "unit": "V", 
            "descr": "Backup DEA 24V DC"
        }, 
        {
            "query_id": 35, 
            "name": "deam15voltb", 
            "unit": "V", 
            "descr": "Backup DEA -15.5V DC"
        }, 
        {
            "query_id": 36, 
            "name": "deap15voltb", 
            "unit": "V", 
            "descr": "Backup DEA +15.5V DC"
        }, 
        {
            "query_id": 37, 
            "name": "deam6voltb", 
            "unit": "V", 
            "descr": "Backup DEA -6V DC"
        }, 
        {
            "query_id": 38, 
            "name": "deap6voltb", 
            "unit": "V", 
            "descr": "Backup DEA +6V DC"
        }, 
        {
            "query_id": 39, 
            "name": "rad_pcb_b", 
            "descr": "Relative Dose Rad. Monitor Side B"
        }, 
        {
            "query_id": 40, 
            "name": "gnd_2", 
            "unit": "V", 
            "descr": "Ground"
        }
        ]
    return out

def pyfits_to_recarray(dat):
    dtypes = []
    colnames = dat.dtype.names
    for colname in colnames:
        col = dat.field(colname)
        if col.dtype.isnative:
            dtype = (colname, col.dtype)
        else:
            dtype = (colname, col.dtype.type) 
        if len(col.shape) > 1:
            dtype = dtype + tuple(col.shape[1:])
        dtypes.append(dtype)

    # Now define a new recarray and copy the original data
    # Note: could use numpy.empty to generate a structured array.
    out = numpy.recarray(len(dat), dtype=dtypes)
    for colname in colnames:
        out[colname][:] = dat.field(colname)

    return out


