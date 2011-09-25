import os
import cPickle as pickle
import logging

class NullHandler(logging.Handler):
    def emit(self, record):
        pass
logger = logging.getLogger('Ska.engarchive.units')
logger.addHandler(NullHandler())
logger.propagate = False

# This is effectively a singleton class
SYSTEMS = set(('cxc', 'eng', 'sci'))
module_dir = os.path.dirname(__file__)

units = {}
units['system'] = 'cxc'
units['cxc'] = pickle.load(open(os.path.join(module_dir, 'units_cxc.pkl')))


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

converters = {
    ('J', 'FTLB'): mult(0.7376),
    ('J*s', 'FTLBSEC'): mult(0.7376),
    ('K', 'DEGC'): K_to_C,
    ('K', 'DEGF'): K_to_F,
    ('deltaK', 'DEGF'): mult(1.8),
    ('kPa', 'PSIA'): mult(0.145),
    ('kPa', 'TORR'): mult(7.501),
    }

def set_units(unit_system):
    """Set conversion unit system.  The input ``unit_system`` must be a string.
    """
    if unit_system not in SYSTEMS:
        raise ValueError('unit_system must be in {}'.format(SYSTEMS))

    units['system'] = unit_system
    if unit_system not in units:
        filename = os.path.join(module_dir, 'units_{0}.pkl'.format(unit_system))
        units[unit_system] = pickle.load(open(filename))

def get_msid_unit(msid):
    MSID = msid.upper()
    return units[units['system']].get(MSID)
     
def convert(msid, vals, delta_val=False):
    MSID = msid.upper()
    conversion = (units['cxc'].get(MSID), get_msid_unit(MSID))
    try:
        vals = converters[conversion](vals, delta_val)
    except KeyError:
        pass
    return vals

