from __future__ import print_function, division, absolute_import

import pytest
import requests
import numpy as np
from contextlib import contextmanager

from .. import remote_access
from .. import fetch

try:
    r = requests.get('http://kadi.cfa.harvard.edu/', timeout=10)
    assert r.status_code == 200
except:
    HAS_KADI = False
else:
    HAS_KADI = True


@contextmanager
def remote_access_enabled():
    remote_enabled = remote_access.KADI_REMOTE_ENABLED
    show_print = remote_access.show_print_output

    remote_access.KADI_REMOTE_ENABLED = True
    remote_access.show_print_output = True
    fetch.content._loaded = False  # Force remote reload of content

    yield

    remote_access.KADI_REMOTE_ENABLED = remote_enabled
    remote_access.show_print_output = show_print
    fetch.content._loaded = False  # Force remote reload of content


@pytest.mark.skipif('not HAS_KADI')
def test_kadi_remote_full():
    with remote_access_enabled():
        dat = fetch.Msid('aogyrct1', '2010:001:12:00:00', '2010:001:12:00:03')

    assert len(dat) == 12
    assert np.all(dat.vals == [16626, 16655, 16685, 16713, 16740, 16765, 16794, 16823, 16853,
                               16881, 16909, 16935])


@pytest.mark.skipif('not HAS_KADI')
def test_kadi_remote_stat():
    with remote_access_enabled():
        dat = fetch.Msid('aogyrct1', '2010:001:12:00:00', '2010:001:13:00:00', stat='5min')

    assert len(dat) == 11
    assert np.allclose(dat.vals, [6007.67578125, -4243.63964844, 1857.47973633, 475.9296875,
                                  -3084.60620117, 5720.10449219, -6835.83203125, 11247.36132812,
                                  -12012.2109375, 13886.24902344, -13762.67480469])


@pytest.mark.skipif('not HAS_KADI')
def test_kadi_remote_get_time_range():
    with remote_access_enabled():
        tstart, tstop = fetch.get_time_range('aopcadmd')

    assert abs(tstart - 63067297) < 2


@pytest.mark.skipif('not HAS_KADI')
def test_kadi_remote_max_rows():
    max_rows = remote_access.KADI_REMOTE_MAX_ROWS
    remote_access.KADI_REMOTE_MAX_ROWS = 10

    # Make sure kadi web remote stops because max rows exceeded
    with remote_access_enabled():
        with pytest.raises(ValueError) as err:
            fetch.Msid('aogyrct1', '2010:001', '2010:002')
        assert 'max rows' in str(err)

    remote_access.KADI_REMOTE_MAX_ROWS = max_rows
