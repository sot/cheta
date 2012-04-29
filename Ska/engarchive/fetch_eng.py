from .fetch import *
from . import fetch
from .version import version as __version__

# Module-level units, defaults to CXC units (e.g. Kelvins etc)
UNITS = Units('eng')


def get_units():
    """Get the unit system currently being used for conversions.
    """
    return UNITS['system']


def set_units(unit_system):
    """Set the unit system used for output telemetry values.  The default
    is "cxc".  Allowed values for ``unit_system``  are:

    ====  ==============================================================
    cxc   FITS standard units used in CXC archive files (basically MKS)
    sci   Same as "cxc" but with temperatures in degC instead of Kelvins
    eng   OCC engineering units (TDB P009, e.g. degF, ft-lb-sec, PSI)
    ====  ==============================================================

    :param unit_system: system of units (cxc, sci, eng)
    """
    UNITS.set_units(unit_system)


class MSID(fetch.MSID):
    __doc__ = fetch.MSID.__doc__

    def __init__(self, msid, start, stop=None, filter_bad=True, stat=None,
                 units=UNITS):
        super(MSID, self).__init__(msid, start, stop=stop,
                                   filter_bad=filter_bad, stat=stat,
                                   units=units)


class Msid(fetch.Msid):
    __doc__ = fetch.Msid.__doc__

    def __init__(self, msid, start, stop=None, filter_bad=True, stat=None,
                 units=UNITS):
        super(Msid, self).__init__(msid, start, stop=stop,
                                   filter_bad=filter_bad, stat=stat,
                                   units=units)


class MSIDset(fetch.MSIDset):
    __doc__ = fetch.MSIDset.__doc__

    def __init__(self, msids, start, stop=None, filter_bad=True, stat=None,
                 units=UNITS):
        super(MSIDset, self).__init__(msids, start, stop=stop,
                                      filter_bad=filter_bad, stat=stat,
                                      units=units)


class Msidset(fetch.Msidset):
    __doc__ = fetch.Msidset.__doc__

    def __init__(self, msids, start, stop=None, filter_bad=True, stat=None,
                 units=UNITS):
        super(Msidset, self).__init__(msids, start, stop=stop,
                                      filter_bad=filter_bad, stat=stat,
                                      units=units)
