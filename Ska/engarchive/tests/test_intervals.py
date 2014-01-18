from __future__ import print_function, absolute_import, division

import numpy as np

import pytest

from Chandra.Time import DateTime
from .. import fetch, utils
try:
    from kadi import events
    HAS_KADI = True
except ImportError:
    HAS_KADI = False

# Use dwells for some interval filter tests
#
# In [2]: print events.dwells.filter('2012:001', '2012:002')
# <Dwell: start=2012:001:16:07:27.515 dur=1834>
# <Dwell: start=2012:001:17:27:28.615 dur=3182>
# <Dwell: start=2012:001:18:41:12.515 dur=29295>
# <Dwell: start=2012:002:02:58:11.817 dur=387>
# <Dwell: start=2012:002:03:23:45.217 dur=3835>
# <Dwell: start=2012:002:04:59:00.617 dur=18143>
# [('2012:001:12:00:00.000', '2012:001:15:50:03.040'),
#  ('2012:001:16:07:27.515', '2012:001:16:38:01.240'),
#  ('2012:001:17:27:28.615', '2012:001:18:20:30.215'),
#  ('2012:001:18:41:12.515', '2012:002:02:49:27.017'),
#  ('2012:002:02:58:11.817', '2012:002:03:04:39.267'),
#  ('2012:002:03:23:45.217', '2012:002:04:27:39.742'),
#  ('2012:002:04:59:00.617', '2012:002:10:01:23.118'),
#  ('2012:002:10:38:21.218', '2012:002:12:00:00.000')]


@pytest.mark.skipif('HAS_KADI is False')
def test_select_remove_interval():
    dat = fetch.MSID('tephin', '2012:002:02:00:00', '2012:002:04:00:00')
    dat_r = dat.remove_intervals(events.dwells, copy=True)
    dat_s = dat.select_intervals(events.dwells, copy=True)
    assert len(dat) == len(dat_r) + len(dat_s)
    assert len(dat) == 219
    assert len(dat_r) == 51
    assert len(dat_s) == 168
    dates_r = DateTime(dat_r.times).date
    assert dates_r[0] == '2012:002:02:49:39.317'  # First after '2012:002:02:49:27.017'
    assert dates_r[15] == '2012:002:02:57:51.317'  # Gap '2012:002:02:58:11.817'
    assert dates_r[16] == '2012:002:03:04:57.717'  # to '2012:002:03:04:39.267'
    assert dates_r[50] == '2012:002:03:23:32.917'  # last before '2012:002:03:23:45.217'
    assert set(dat_r.times).isdisjoint(dat_s.times)


@pytest.mark.skipif('HAS_KADI is False')
def test_remove_intervals_stat():
    for stat in (None, '5min'):
        dat = fetch.MSID('tephin', '2012:002', '2012:003')
        dat.remove_intervals(events.dwells)
        attrs = [attr for attr in ('vals', 'mins', 'maxes', 'means',
                                   'p01s', 'p05s', 'p16s', 'p50s',
                                   'p84s', 'p95s', 'p99s', 'midvals')
                 if hasattr(dat, attr)]

        for attr in attrs:
            assert len(dat) == len(getattr(dat, attr))


@pytest.mark.skipif('HAS_KADI is False')
def test_select_remove_all_interval():
    """
    Select or remove all data points via an event that entirely spans the MSID data.
    """
    dat = fetch.Msid('tephin', '2012:001:20:00:00', '2012:001:21:00:00')
    dat_r = dat.remove_intervals(events.dwells, copy=True)
    dat_s = dat.select_intervals(events.dwells, copy=True)
    assert len(dat) == 110
    assert len(dat_r) == 0
    assert len(dat_s) == 110


def test_msid_logical_intervals():
    """
    Test MSID.logical_intervals()
    """
    dat = fetch.Msid('aopcadmd', '2013:001:00:00:00', '2013:001:02:00:00')

    # default complete_intervals=True
    intervals = dat.logical_intervals('==', 'NPNT')
    assert len(intervals) == 1
    assert np.all(intervals['datestart'] == ['2013:001:01:03:37.032'])
    assert np.all(intervals['datestop'] == ['2013:001:01:26:13.107'])

    # Now with incomplete intervals on each end
    intervals = dat.logical_intervals('==', 'NPNT', complete_intervals=False)
    assert len(intervals) == 3
    assert np.all(intervals['datestart'] == ['2012:366:23:59:59.932',
                                             '2013:001:01:03:37.032',
                                             '2013:001:01:59:06.233'])
    assert np.all(intervals['datestop'] == ['2013:001:00:56:07.057',
                                            '2013:001:01:26:13.107',
                                            '2013:001:01:59:59.533'])


def test_util_logical_intervals():
    """
    Test utils.logical_intervals()
    """
    dat = fetch.Msidset(['3tscmove', 'aorwbias', 'coradmen'], '2012:190', '2012:205')
    dat.interpolate(32.8)  # Sample MSIDs onto 32.8 second intervals (like 3TSCMOVE)
    scs107 = ((dat['3tscmove'].vals == 'T')
              & (dat['aorwbias'].vals == 'DISA')
              & (dat['coradmen'].vals == 'DISA'))
    scs107s = utils.logical_intervals(dat.times, scs107)
    scs107s['duration'].format = '{:.1f}'
    assert (scs107s['datestart', 'datestop', 'duration'].pformat() ==
            ['      datestart              datestop       duration',
             '--------------------- --------------------- --------',
             '2012:194:20:00:48.052 2012:194:20:04:37.652    229.6',
             '2012:196:21:07:52.852 2012:196:21:11:42.452    229.6',
             '2012:201:11:46:03.252 2012:201:11:49:52.852    229.6'])


def test_util_logical_intervals_gap():
    """
    Test the max_gap functionality
    """
    times = np.array([1, 2, 3, 200, 201, 202], dtype=np.float)
    bools = np.ones(len(times), dtype=bool)
    out = utils.logical_intervals(times, bools, complete_intervals=False, max_gap=10)
    assert np.allclose(out['tstart'], [0.5, 197.5])
    assert np.allclose(out['tstop'], [5.5, 202.5])

    out = utils.logical_intervals(times, bools, complete_intervals=False)
    assert np.allclose(out['tstart'], [0.5])
    assert np.allclose(out['tstop'], [202.5])


def test_msid_state_intervals():
    """
    Test MSID.state_intervals() - basic aliveness and regression test
    """
    expected = ['      datestart              datestop       val ',
                '--------------------- --------------------- ----',
                '2012:366:23:59:59.932 2013:001:00:56:07.057 NPNT',
                '2013:001:00:56:07.057 2013:001:01:03:37.032 NMAN',
                '2013:001:01:03:37.032 2013:001:01:26:13.107 NPNT',
                '2013:001:01:26:13.107 2013:001:01:59:06.233 NMAN',
                '2013:001:01:59:06.233 2013:001:01:59:59.533 NPNT']

    dat = fetch.Msid('aopcadmd', '2013:001:00:00:00', '2013:001:02:00:00')
    intervals = dat.state_intervals()['datestart', 'datestop', 'val']
    assert intervals.pformat() == expected

    intervals = utils.state_intervals(dat.times, dat.vals)['datestart', 'datestop', 'val']
    assert intervals.pformat() == expected
