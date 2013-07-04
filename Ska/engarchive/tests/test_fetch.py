import numpy as np

from Ska.engarchive import fetch
from Chandra.Time import DateTime

DATES_EXPECT1 = np.array(['2008:291:23:59:58.987', '2008:291:23:59:59.244',
                          '2008:291:23:59:59.500', '2008:291:23:59:59.756',
                          '2008:297:00:00:00.121', '2008:297:00:00:00.378',
                          '2008:297:00:00:00.634'])

DATES_EXPECT2 = np.array(['2008:291:23:59:54.119', '2008:291:23:59:55.144',
                          '2008:291:23:59:56.169', '2008:291:23:59:57.194',
                          '2008:291:23:59:58.219', '2008:291:23:59:59.244',
                          '2008:297:00:00:00.890', '2008:297:00:00:01.915',
                          '2008:297:00:00:02.940', '2008:297:00:00:03.965'])

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
    dat.filter_bad_times(table=BAD_TIMES)
    dates = DateTime(dat['aogyrct1'].times[168581:168588]).date
    assert np.all(dates == DATES_EXPECT1)

    dat = fetch.Msidset(['aogyrct1'], '2008:291', '2008:298')
    dat.filter_bad_times(table=BAD_TIMES)
    dates = DateTime(dat['aogyrct1'].times[168581:168588]).date
    assert np.all(dates == DATES_EXPECT1)


def test_filter_bad_times_default():
    """Test bad times that come from msid_bad_times.dat"""
    dat = fetch.MSID('aogbias1', '2008:291', '2008:298')
    dat.filter_bad_times()
    dates = DateTime(dat.times[42140:42150]).date
    assert np.all(dates == DATES_EXPECT2)


def test_interpolate():
    dat = fetch.MSIDset(['aoattqt1', 'aogyrct1', 'aopcadmd'],
                        '2008:002:21:48:00', '2008:002:21:50:00')
    dat.interpolate(10.0)

    assert np.allclose(dat['aoattqt1'].vals,
                       np.array([-0.33072645, -0.33072633, -0.33072634,
                                  -0.33072632, -0.33072705,
                                  -0.33073644, -0.33076456, -0.33081424,
                                  -0.33090285, -0.33088904,
                                  -0.33099454, -0.33128471]))

    assert np.all(dat['aopcadmd'].vals ==
                  np.array(['NPNT', 'NPNT', 'NPNT', 'NMAN', 'NMAN', 'NMAN',
                            'NMAN', 'NMAN', 'NMAN', 'NMAN', 'NMAN', 'NMAN'],
                           dtype='|S4'))

    assert np.all(dat['aogyrct1'].vals ==
                  np.array([-23261, -22131, -21000, -19878, -18714, -17301,
                             -15379, -12674, -8914, -3398, 3514, 11486],
                           dtype=np.int16))


def test_interpolate_msid():
    start = '2008:002:21:48:00'
    stop = '2008:002:21:50:00'
    dat = fetch.MSID('aoattqt1', start, stop)
    dat.interpolate(10.0, start, stop)
    assert np.allclose(dat.vals,
                       np.array([-0.33072645, -0.33072633, -0.33072634,
                                  -0.33072632, -0.33072705,
                                  -0.33073644, -0.33076456, -0.33081424,
                                  -0.33090285, -0.33088904,
                                  -0.33099454, -0.33128471]))

    dat = fetch.MSID('aogyrct1', start, stop)
    dat.interpolate(10.0, start, stop)
    assert np.all(dat.vals ==
                  np.array([-23349, -22219, -21087, -19960, -18810, -17425,
                             -15551, -12919,
                             -9252, -3887, 2943, 10858],
                           dtype=np.int16))

    dat = fetch.MSID('aopcadmd', start, stop)
    dat.interpolate(10.0, start, stop)
    assert np.all(dat.vals ==
                  np.array(['NPNT', 'NPNT', 'NPNT', 'NMAN',
                            'NMAN', 'NMAN', 'NMAN', 'NMAN',
                            'NMAN', 'NMAN', 'NMAN', 'NMAN'],
                           dtype='|S4'))


def _assert_msid_equal(msid1, msid2):
    for attr in ('tstart', 'tstop', 'datestart', 'datestop', 'units', 'unit', 'stat'):
        assert getattr(msid1, attr) == getattr(msid2, attr)
    assert np.all(msid1.times == msid2.times)
    assert np.all(msid1.vals == msid2.vals)
    assert msid1.__class__ is msid2.__class__


def test_msid_copy():
    for MsidClass in (fetch.Msid, fetch.MSID):
        msid1 = MsidClass('aogbias1', '2008:291', '2008:298')
        msid2 = msid1.copy()
        _assert_msid_equal(msid1, msid2)

    # Make sure msid data sets are independent
    msid2.filter_bad()
    assert len(msid1.vals) != len(msid2.vals)


def test_msidset_copy():
    for MsidsetClass in (fetch.MSIDset, fetch.Msidset):
        msidset1 = MsidsetClass(['aogbias1', 'aogbias2'], '2008:291', '2008:298')
        msidset2 = msidset1.copy()

        for attr in ('tstart', 'tstop', 'datestart', 'datestop'):
            assert getattr(msidset1, attr) == getattr(msidset2, attr)

        assert msidset1.keys() == msidset2.keys()
        for name in msidset1.keys():
            _assert_msid_equal(msidset1[name], msidset2[name])
