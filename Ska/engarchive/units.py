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
        return vals * 1.8 - 459.67  # (vals - 273.15) * 1.8 + 32


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


def load_units(unit_system):
    """Load units definitions for unit_system if not already loaded.
    """
    if unit_system not in SYSTEMS:
        raise ValueError('unit_system must be in {}'.format(SYSTEMS))

    if unit_system not in units:
        filename = os.path.join(module_dir,
                                'units_{0}.pkl'.format(unit_system))
        units[unit_system] = pickle.load(open(filename))


def set_units(unit_system):
    """Set conversion unit system.  The input ``unit_system`` must be a string.
    """
    load_units(unit_system)
    units['system'] = unit_system


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


class Units(dict):
    """
    Provide access to units via object-oriented replacement for
    Ska.engarchive.units module.

    This class is weird because it was designed to conform to the
    existing API where units.units was a module dict that had keys
    'system', 'cxc', and possibly others.  But this implementation now
    allows for non-interacting units systems in fetch, fetch_eng, and
    fetch_sci.

    It only allows a single key "system" to be set
    """

    def __init__(self, system='cxc'):
        super(Units, self).__init__(system=system)

    def __getitem__(self, item):
        if item in SYSTEMS:
            load_units(item)
            return units[item]
        else:
            return dict.__getitem__(self, item)

    def __setitem__(self, item, val):
        if item == 'system':
            load_units(val)
            dict.__setitem__(self, item, val)
        else:
            raise KeyError('In Units object only "system" key is settable')

    def set_units(self, unit_system):
        """Set conversion unit system.  The input ``unit_system`` must be a
        string.
        """
        self['system'] = unit_system

    def get_msid_unit(self, msid):
        MSID = msid.upper()
        system = self['system']
        return self[system].get(MSID)

    def convert(self, msid, vals, delta_val=False):
        MSID = msid.upper()
        conversion = (self['cxc'].get(MSID), self.get_msid_unit(MSID))
        try:
            vals = converters[conversion](vals, delta_val)
        except KeyError:
            pass
        return vals
