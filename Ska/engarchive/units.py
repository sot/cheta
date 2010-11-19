import os
import cPickle as pickle
import logging

class NullHandler(logging.Handler):
    def emit(self, record):
        pass
logger = logging.getLogger('Ska.engarchive.units')
logger.addHandler(NullHandler())
logger.propagate = False

def K_to_C(vals, delta_val=False):
    if delta_val:
        return vals
    else:
        return vals - 273.15

def K_to_F(vals, delta_val=False):
    if delta_val:
        return vals * 1.8
    else:
        return vals * 1.8  - 459.67  # (vals - 273.15) * 1.8 + 32

def mult(scale_factor):
    def convert(vals, delta_val=False):
        return vals * scale_factor
    return convert

def set_units(unit_system):
    units_out.clear()
    units_out.update(units_cxc)
    try:
        units_out.update(unit_system)
    except ValueError:
        filename = os.path.join(module_dir, 'units_{0}.pkl'.format(unit_system))
        units_out.update(pickle.load(open(filename)))

def convert(msid, vals, delta_val=False):
    MSID = msid.upper()
    conversion = (units_cxc.get(MSID), units_out.get(MSID))
    try:
        vals = converters[conversion](vals, delta_val)
        logger.info('Converted {0} units: {1} (delta_val={2})'.format(msid, conversion, delta_val))
    except KeyError:
        logger.info('No conversion for {0}: {1}'.format(msid, conversion))
        pass
    return vals

module_dir = os.path.dirname(__file__)
units_cxc = pickle.load(open(os.path.join(module_dir, 'units_cxc.pkl')))
units_out = units_cxc.copy()

converters = {
    ('J', 'FTLB'): mult(0.7376),
    ('J*s', 'FTLBSEC'): mult(0.7376),
    ('K', 'DEGC'): K_to_C,
    ('K', 'DEGF'): K_to_F,
    ('deltaK', 'DEGF'): mult(1.8),
    ('kPa', 'PSIA'): mult(0.145),
    ('kPa', 'TORR'): mult(7.501),
    }

