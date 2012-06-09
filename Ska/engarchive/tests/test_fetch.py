import numpy as np

import Ska.engarchive.fetch_eng as fetch
from Chandra.Time import DateTime

print
print fetch.__version__
print fetch.__file__

DATES_EXPECT1 = np.array(['2008:291:23:59:58.987', '2008:291:23:59:59.244',
                          '2008:291:23:59:59.500', '2008:291:23:59:59.756',
                          '2008:297:00:00:00.121', '2008:297:00:00:00.378',
                          '2008:297:00:00:00.634'])

DATES_EXPECT2 = np.array(['2008:291:23:59:58.987', '2008:291:23:59:59.244',
                         '2008:291:23:59:59.500', '2008:291:23:59:59.756',
                         '2008:296:00:00:00.048', '2008:296:00:00:00.304',
                         '2008:296:00:00:00.561'])

BAD_TIMES = ['2008:292:00:00:00 2008:297:00:00:00',
             '2008:305:00:12:00 2008:305:00:12:03',
             '2010:101:00:01:12 2010:101:00:01:25']


def test_filter_bad_times_list():
    dat = fetch.MSID('aogyrct1', '2008:291', '2008:298')
    dat.filter_bad_times(table=BAD_TIMES)
    dates = DateTime(dat.times[168581:168588]).date
    assert np.all(dates == DATES_EXPECT1)

    dat = fetch.Msid('aogyrct1', '2008:291', '2008:298')
    dat.filter_bad_times(table=BAD_TIMES)
    dates = DateTime(dat.times[168581:168588]).date
    assert np.all(dates == DATES_EXPECT1)


def test_msidset_filter_bad_times_list():
    dat = fetch.MSIDset(['aogyrct1'], '2008:291', '2008:298')
    dat.filter_bad_times()
    dates = DateTime(dat['aogyrct1'].times[168581:168588]).date
    assert np.all(dates == DATES_EXPECT2)

    dat = fetch.Msidset(['aogyrct1'], '2008:291', '2008:298')
    dat.filter_bad_times()
    dates = DateTime(dat['aogyrct1'].times[168581:168588]).date
    assert np.all(dates == DATES_EXPECT2)


def test_filter_bad_times_default():
    """Test bad times that come from msid_bad_times.dat"""
    dat = fetch.MSID('aogyrct1', '2008:291', '2008:298')
    dat.filter_bad_times()
    dates = DateTime(dat.times[168581:168588]).date
    assert np.all(dates == DATES_EXPECT2)


def test_interpolate():
    dat = fetch.MSIDset(['aoattqt1', 'aogyrct1', 'aopcadmd'],
                        '2008:002:21:48:00', '2008:002:21:50:00')
    dat.interpolate(10.0)

    assert np.allclose(dat['aoattqt1'].vals,
                       np.array([-0.33072645, -0.33072634, -0.33072637,
                                  -0.33072674, -0.33072665,
                                  -0.33073477, -0.330761, -0.33080694,
                                  -0.33089434, -0.33089264,
                                  -0.33097442, -0.33123678]))

    assert np.all(dat['aopcadmd'].vals ==
                  np.array(['NPNT', 'NPNT', 'NPNT', 'NMAN',
                            'NMAN', 'NMAN', 'NMAN', 'NMAN',
                            'NMAN', 'NMAN', 'NMAN', 'NMAN'],
                           dtype='|S4'))

    assert np.all(dat['aogyrct1'].vals ==
                  np.array([-23349, -22247, -21117, -19988,
                             -18839, -17468, -15605, -13000,
                             -9360, -4052, 2752, 10648],
                           dtype=np.int16))


def test_interpolate_msid():
    start = '2008:002:21:48:00'
    stop = '2008:002:21:50:00'
    dat = fetch.MSID('aoattqt1', start, stop)
    dat.interpolate(10.0, start, stop)
    assert np.allclose(dat.vals,
                       np.array([-0.33072645, -0.33072634, -0.33072637,
                                  -0.33072674, -0.33072665,
                                  -0.33073477, -0.330761, -0.33080694,
                                  -0.33089434, -0.33089264,
                                  -0.33097442, -0.33123678]))

    dat = fetch.MSID('aogyrct1', start, stop)
    dat.interpolate(10.0, start, stop)
    assert np.all(dat.vals ==
                  np.array([-23349, -22247, -21117, -19988,
                             -18839, -17468, -15605, -13000,
                             -9360, -4052, 2752, 10648],
                           dtype=np.int16))

    dat = fetch.MSID('aopcadmd', start, stop)
    dat.interpolate(10.0, start, stop)
    assert np.all(dat.vals ==
                  np.array(['NPNT', 'NPNT', 'NPNT', 'NMAN',
                            'NMAN', 'NMAN', 'NMAN', 'NMAN',
                            'NMAN', 'NMAN', 'NMAN', 'NMAN'],
                           dtype='|S4'))
