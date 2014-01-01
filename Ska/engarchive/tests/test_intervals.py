from Chandra.Time import DateTime
from .. import fetch
from kadi import events

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
