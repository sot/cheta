# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""Test that computed MSIDs work as expected."""

import numpy as np
import pytest

from ..derived.base import DerivedParameter
from ..derived.comps import ComputedMsid

try:
    import maude
    date1 = '2016:001:00:00:00.1'
    date2 = '2016:001:00:00:02.0'
    maude.get_msids(msids='ccsdsid', start=date1, stop=date2)
except Exception:
    HAS_MAUDE = False
else:
    HAS_MAUDE = True


class Comp_Plus_Five:
    """Silly base comp to add 5 to the value"""
    def get_MSID(self, start, stop):
        dat = self.fetch_eng.MSID(self.msid, start, stop)
        dat.vals = dat.vals + 5
        return dat


class Comp_TEPHIN_Plus_Five(Comp_Plus_Five, ComputedMsid):
    msid = 'tephin'


class Comp_CSS1_NPM_SUN(DerivedParameter, ComputedMsid):
    """Coarse Sun Sensor Counts 1 filtered for NPM and SA Illuminated

    Defined as CSS-1 current converted back into counts
    (AOCSSI1 * 4095 / 5.49549) when in NPM (AOPCADMD==1) and SA is illuminated
    (AOSAILLM==1).  Otherwise, "Bads" flag is set equal to one.

    """
    rootparams = ['aocssi1', 'aopcadmd', 'aosaillm']
    time_step = 1.025
    max_gap = 10.0

    def __call__(self, start, stop):
        # Get an interpolated MSIDset for rootparams
        msids = self.fetch(start, stop)

        # Do the computation and set bad values
        npm_sun = ((msids['aopcadmd'].vals == 'NPNT') &
                   (msids['aosaillm'].vals == 'ILLM'))
        msids.bads = msids.bads | ~npm_sun
        css1_npm_sun = msids['aocssi1'].vals * 4095 / 5.49549

        out = {'vals': css1_npm_sun,
               'times': msids.times,
               'bads': msids.bads}
        return out


# Need to add classes before importing fetch
from .. import fetch_eng, fetch


def test_comp_from_derived_parameter():
    """Test that on-the-fly comp gives same result as derived parameter from
    same code.
    """
    dat1 = fetch_eng.Msid('comp_css1_npm_sun', '2020:001', '2020:010')
    dat2 = fetch_eng.Msid('dp_css1_npm_sun', '2020:001', '2020:010')

    for attr in ('vals', 'times', 'bads'):
        assert np.all(getattr(dat1, attr) == getattr(dat2, attr))


def test_simple_comp():
    dat1 = fetch_eng.Msid('tephin', '2020:001', '2020:010')
    dat2 = fetch_eng.Msid('comp_tephin_plus_five', '2020:001', '2020:010')
    assert np.all(dat1.vals + 5 == dat2.vals)
    assert np.all(dat1.times == dat2.times)
    assert np.all(dat1.bads == dat2.bads)


@pytest.mark.skipif("not HAS_MAUDE")
def test_simple_comp_with_maude():
    with fetch.data_source('maude'):
        dat1 = fetch_eng.Msid('tephin', '2020:001', '2020:003')
        dat2 = fetch_eng.Msid('comp_tephin_plus_five', '2020:001', '2020:003')
        assert np.all(dat1.vals + 5 == dat2.vals)
        assert np.all(dat1.times == dat2.times)
        assert np.all(dat1.bads == dat2.bads)


def test_comp_with_stat():
    with pytest.raises(ValueError,
                       match='stats are not supported for computed MSIDs'):
        fetch_eng.Msid('comp_tephin_plus_five',
                       '2020:001', '2020:010', stat='5min')


def test_mups_valve():
    colnames = ['times', 'vals', 'bads', 'vals_raw',
                'vals_nan', 'vals_corr', 'vals_model', 'source']

    dat = fetch.MSID('comp_PM2THV1T', '2020:001', '2020:010')
    assert len(dat.vals) == 36661
    assert np.count_nonzero(dat.source != 0) == 34499
    assert dat.colnames == colnames
    for attr in colnames:
        assert len(dat.vals) == len(getattr(dat, attr))

    dat = fetch.Msid('comp_PM2THV1T', '2020:001', '2020:010')
    assert len(dat.vals) == 34499  # Some bad values
    assert dat.colnames == colnames
    for attr in colnames:
        if attr != 'bads':
            assert len(dat.vals) == len(getattr(dat, attr))

    dat = fetch.MSID('comp_PM1THV2T', '2020:001', '2020:010')
    assert len(dat.vals) == 36661  # Same as PM2THV1T
    assert dat.colnames == colnames
    for attr in colnames:
        assert len(dat.vals) == len(getattr(dat, attr))

    dat = fetch.Msid('comp_PM1THV2T', '2020:001', '2020:010')
    assert len(dat.vals) == 36240  # Some bad values
    assert len(dat.source) == 36240  # Filtering applies to sources
    assert dat.colnames == colnames
    for attr in colnames:
        if attr != 'bads':
            assert len(dat.vals) == len(getattr(dat, attr))
