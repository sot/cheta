# Licensed under a 3-clause BSD style license - see LICENSE.rst
import sys

from . import (
    __version__,  # noqa
    fetch,
)
from .fetch import *  # noqa

# Module-level units, defaults to CXC units (e.g. Kelvins etc)
UNITS = fetch.Units("sci")


def get_units():
    return UNITS["system"]


get_units.__doc__ = fetch.get_units.__doc__


def set_units(unit_system):
    UNITS.set_units(unit_system)


set_units.__doc__ = fetch.set_units.__doc__


class MSID(fetch.MSID):
    __doc__ = fetch.MSID.__doc__
    units = UNITS
    fetch = sys.modules[__name__]


class Msid(fetch.Msid):
    __doc__ = fetch.Msid.__doc__
    units = UNITS
    fetch = sys.modules[__name__]


class MSIDset(fetch.MSIDset):
    __doc__ = fetch.MSIDset.__doc__
    MSID = MSID


class Msidset(fetch.Msidset):
    __doc__ = fetch.Msidset.__doc__
    MSID = MSID
