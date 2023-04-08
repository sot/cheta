# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""Test that computed MSIDs work as expected."""

import numpy as np
import pytest
from cxotime import CxoTime
from Quaternion import Quat

from .. import fetch as fetch_cxc
from .. import fetch_eng, fetch_sci
from ..derived.base import DerivedParameter
from ..derived.comps import ComputedMsid

try:
    import maude

    date1 = "2016:001:00:00:00.1"
    date2 = "2016:001:00:00:02.0"
    maude.get_msids(msids="ccsdsid", start=date1, stop=date2)
except Exception:
    HAS_MAUDE = False
else:
    HAS_MAUDE = True


class Comp_Passthru(ComputedMsid):
    """Pass MSID through unchanged (for checking that stats work)"""

    msid_match = r"passthru_(\w+)"

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        dat = self.fetch_eng.MSID(msid_args[0], tstart, tstop)

        out = {"vals": dat.vals, "bads": dat.bads, "times": dat.times, "unit": dat.unit}
        return out


class Comp_Val_Plus_Five(ComputedMsid):
    """Silly base comp to add 5 to the value"""

    msid_match = r"comp_(\w+)_plus_five"

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        dat = self.fetch_sys.MSID(msid_args[0], tstart, tstop)

        out = {
            "vals": dat.vals + 5,
            "bads": dat.bads,
            "times": dat.times,
            "unit": dat.unit,
        }
        return out


class Comp_CSS1_NPM_SUN(ComputedMsid, DerivedParameter):
    """Coarse Sun Sensor Counts 1 filtered for NPM and SA Illuminated

    Defined as CSS-1 current converted back into counts
    (AOCSSI1 * 4095 / 5.49549) when in NPM (AOPCADMD==1) and SA is illuminated
    (AOSAILLM==1).  Otherwise, "Bads" flag is set equal to one.

    """

    rootparams = ["aocssi1", "aopcadmd", "aosaillm"]
    time_step = 1.025
    max_gap = 10.0
    msid_match = "comp_css1_npm_sun"

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        # Get an interpolated MSIDset for rootparams
        msids = self.fetch(tstart, tstop)

        # Do the computation and set bad values
        npm_sun = (msids["aopcadmd"].vals == "NPNT") & (
            msids["aosaillm"].vals == "ILLM"
        )
        msids.bads = msids.bads | ~npm_sun
        css1_npm_sun = msids["aocssi1"].vals * 4095 / 5.49549

        out = {
            "vals": css1_npm_sun,
            "times": msids.times,
            "bads": msids.bads,
            "unit": None,
        }
        return out


def test_comp_from_derived_parameter():
    """Test that on-the-fly comp gives same result as derived parameter from
    same code.
    """
    dat1 = fetch_eng.Msid("comp_css1_npm_sun", "2020:001", "2020:010")
    dat2 = fetch_eng.Msid("dp_css1_npm_sun", "2020:001", "2020:010")

    for attr in ("vals", "times", "bads", "unit"):
        assert np.all(getattr(dat1, attr) == getattr(dat2, attr))


@pytest.mark.parametrize(
    "fetch,unit", [(fetch_eng, "DEGF"), (fetch_sci, "DEGC"), (fetch_cxc, "K")]
)
def test_simple_comp(fetch, unit):
    dat1 = fetch.Msid("tephin", "2020:001", "2020:010")
    dat2 = fetch.Msid("comp_tephin_plus_five", "2020:001", "2020:010")
    assert np.all(dat1.vals + 5 == dat2.vals)
    assert np.all(dat1.times == dat2.times)
    assert np.all(dat1.bads == dat2.bads)
    assert dat1.unit == dat2.unit
    assert dat2.unit == unit


@pytest.mark.skipif("not HAS_MAUDE")
@pytest.mark.parametrize(
    "fetch,unit", [(fetch_eng, "DEGF"), (fetch_sci, "DEGC"), (fetch_cxc, "K")]
)
def test_simple_comp_with_maude(fetch, unit):
    with fetch.data_source("maude"):
        dat1 = fetch.Msid("tephin", "2020:001", "2020:003")
        dat2 = fetch.Msid("comp_tephin_plus_five", "2020:001", "2020:003")
        assert np.all(dat1.vals + 5 == dat2.vals)
        assert np.all(dat1.times == dat2.times)
        assert np.all(dat1.bads == dat2.bads)
        assert dat1.unit == dat2.unit
        assert dat2.unit == unit


def test_mups_valve():
    colnames = [
        "vals",
        "times",
        "bads",
        "vals_raw",
        "vals_nan",
        "vals_corr",
        "vals_model",
        "source",
    ]

    # Use the chandra_models 6854df4d commit for testing. This is a commit of
    # chandra_models that has the epoch dates changes to fully-qualified values
    # like 2017:123:12:00:00 (instead of 2017:123). This allows these regression
    # tests to pass with Chandra.Time 3.x or 4.0+.
    dat = fetch_eng.MSID(
        "PM2THV1T_clean_6854df4d", "2020:001:12:00:00", "2020:010:12:00:00"
    )
    assert dat.unit == "DEGF"
    assert len(dat.vals) == 36661
    ok = dat.source != 0
    # Temps are reasonable for degF
    assert np.all((dat.vals[ok] > 55) & (dat.vals[ok] < 220))
    assert np.count_nonzero(ok) == 31524
    assert dat.colnames == colnames
    for attr in colnames:
        assert len(dat.vals) == len(getattr(dat, attr))

    dat = fetch_sci.Msid(
        "PM2THV1T_clean_6854df4d", "2020:001:12:00:00", "2020:010:12:00:00"
    )
    assert dat.unit == "DEGC"
    ok = dat.source != 0
    # Temps are reasonable for degC
    assert np.all((dat.vals[ok] > 10) & (dat.vals[ok] < 110))
    assert len(dat.vals) == 31524  # Some bad values
    assert dat.colnames == colnames
    for attr in colnames:
        if attr != "bads":
            assert len(dat.vals) == len(getattr(dat, attr))

    dat = fetch_cxc.MSID(
        "PM1THV2T_clean_6854df4d", "2020:001:12:00:00", "2020:010:12:00:00"
    )
    ok = dat.source != 0
    # Temps are reasonable for K
    assert np.all((dat.vals[ok] > 280) & (dat.vals[ok] < 380))
    assert len(dat.vals) == 36661  # Same as PM2THV1T
    assert dat.colnames == colnames
    for attr in colnames:
        assert len(dat.vals) == len(getattr(dat, attr))

    # Check using default master branch
    dat = fetch_eng.Msid("pm1thv2t_clean", "2020:001:12:00:00", "2020:010:12:00:00")
    assert len(dat.vals) < 36661  # Some bad values (36661 is number of raw samples)
    assert len(dat.source) == len(dat.vals)  # Filtering applies to sources
    assert dat.colnames == colnames
    for attr in colnames:
        if attr != "bads":
            assert len(dat.vals) == len(getattr(dat, attr))


def test_cmd_states():
    start, stop = "2020:002:08:00:00", "2020:002:10:00:00"
    dat = fetch_eng.Msid("cmd_state_pitch_1000", start, stop)
    exp_vals = np.array(
        [
            55.99128956,
            55.8747053,
            55.8747053,
            90.66266599,
            159.06945155,
            173.11528258,
            173.11528258,
            173.11528258,
        ]
    )
    assert np.allclose(dat.vals, exp_vals)
    assert type(dat.vals) is np.ndarray
    assert np.allclose(np.diff(dat.times), 1025.0)
    assert not np.any(dat.bads)
    assert dat.unit is None

    dat = fetch_eng.Msid("cmd_state_pcad_mode_1000", start, stop)
    exp_vals = np.array(
        ["NPNT", "NPNT", "NPNT", "NMAN", "NMAN", "NPNT", "NPNT", "NPNT"]
    )
    assert np.all(dat.vals == exp_vals)
    assert type(dat.vals) is np.ndarray
    assert np.allclose(np.diff(dat.times), 1025.0)


@pytest.mark.parametrize("stat", ["5min", "daily"])
def test_stats(stat):
    start, stop = "2020:001:12:00:00", "2020:010:12:00:00"

    dat = fetch_eng.Msid("pitch", start, stop, stat=stat)
    datc = fetch_eng.Msid("passthru_pitch", start, stop, stat=stat)

    for attr in datc.colnames:
        val = getattr(dat, attr)
        valc = getattr(datc, attr)
        if attr == "bads":
            assert val == valc
            continue
        assert val.dtype == valc.dtype
        if val.dtype.kind == "f":
            assert np.allclose(val, valc)
        else:
            assert np.all(val == valc)


@pytest.mark.parametrize("msid", ["aoattqt", "aoatupq", "aocmdqt", "aotarqt"])
@pytest.mark.parametrize("maude", [False, True])
@pytest.mark.parametrize("offset", [0, 2, 4, 6])
def test_quat_comp(msid, maude, offset):
    tstart0 = 761356871.0
    tstart = tstart0 + offset * 8.0
    tstop = tstart + 60.0

    data_source = ("maude allow_subset=False" if maude else "cxc")
    with fetch_eng.data_source(data_source):
        datq = fetch_eng.MSID(f"quat_{msid}", tstart, tstop)
        dats = fetch_eng.MSIDset([f"{msid}*"], tstart - 40, tstop + 40)

    msids = sorted(dats)
    times = dats[msids[0]].times
    ok = (times >= tstart) & (times < tstop)
    dats.interpolate(times=times[ok], filter_bad=False, bad_union=True)

    n_comp = len(dats)
    for ii in range(n_comp):
        vq = datq.vals.q[:, ii]
        vn = dats[f"{msid}{ii + 1}"].vals
        # Code handles q1**2 + q2**2 + q3**2 > 1 by clipping the norm and renormalizing
        # the quaternion. This generates a significant difference for the cmd quat.
        ok = np.isclose(vq, vn, rtol=0, atol=(1e-4 if msid == "aocmdqt" else 1e-8))
        assert np.all(ok)
    assert isinstance(datq.vals, Quat)


def test_pitch_comp():
    """Test pitch_comp during a time with NPNT, NMAN, NSUN and Safe Sun"""
    start = "2022:293"
    stop = "2022:297"
    dat = fetch_eng.Msid("pitch_comp", start, stop)
    dat.interpolate(dt=10000)
    # fmt: off
    exp = np.array(
        [
            60.8, 167.26, 159.54, 60.84, 60.86, 167.38, 144., 90.1 ,
            90.12, 90.12, 90.05, 90.12, 90.1 , 90.1 , 90.12, 90.09,
            90.07, 90.14, 90.02, 90.04, 90.02, 90.02, 90.02, 90.02,
            90.15, 90.23, 90.18, 90.18, 90.18, 90.21, 90.21, 90.21,
            90.21, 89.94, 153.9
        ]
    )
    # fmt: on
    assert np.allclose(dat.vals, exp, rtol=0, atol=2e-2)


@pytest.mark.parametrize("pitch_roll", ["pitch", "roll"])
def test_pitch_roll_comp_short_npnt(pitch_roll):
    """Test pitch_comp and roll_comp during a time with NPNT"""
    # Sampled each 1.025 seconds
    start = "2022:200:00:00:00.000"
    stop = "2022:200:00:00:04.000"

    dat = fetch_eng.Msid(f"{pitch_roll}_comp", start, stop)
    if pitch_roll == "pitch":
        exp_vals = [156.00595556, 156.00595083, 156.00595562, 156.00594386]
    else:
        exp_vals = [0.03759918, 0.03763989, 0.03770095, 0.03773727]
    exp_dates = [
        "2022:200:00:00:00.066",
        "2022:200:00:00:01.091",
        "2022:200:00:00:02.116",
        "2022:200:00:00:03.141",
    ]
    assert np.all(CxoTime(dat.times).date == exp_dates)
    assert np.allclose(dat.vals, exp_vals, rtol=0, atol=1e-4)


@pytest.mark.parametrize("pitch_roll", ["pitch", "roll"])
def test_pitch_roll_comp_short_nsun(pitch_roll):
    """Test pitch/roll_comp during a time with NSUN"""
    # Sampled each 4.1 seconds
    start = "2022:295:18:00:00.000"
    stop = "2022:295:18:00:16.000"

    dat = fetch_eng.Msid(f"{pitch_roll}_comp", start, stop)
    if pitch_roll == "pitch":
        exp_vals = [90.15486, 90.1576, 90.178665, 90.18141]
    else:
        exp_vals = [-0.10997535, -0.10997537, -0.09622853, -0.09622855]
    exp_dates = [
        "2022:295:18:00:01.716",
        "2022:295:18:00:05.816",
        "2022:295:18:00:09.916",
        "2022:295:18:00:14.016",
    ]
    assert np.all(CxoTime(dat.times).date == exp_dates)
    assert np.allclose(dat.vals, exp_vals, rtol=0, atol=1e-4)


@pytest.mark.parametrize("pitch_roll", ["pitch", "roll"])
def test_pitch_roll_comp_short_safe_mode(pitch_roll):
    """Test pitch/roll_comp during a time with NPNT"""
    # Sampled each 0.25625 seconds
    start = "2022:295:00:00:00.000"
    stop = "2022:295:00:00:01.000"

    dat = fetch_eng.Msid(f"{pitch_roll}_comp", start, stop)
    if pitch_roll == "pitch":
        exp_vals = [90.127625, 90.14162, 90.14162, 90.14162]
    else:
        exp_vals = [0.21003094, 0.20195293, 0.20195293, 0.20195293]
    exp_dates = [
        "2022:295:00:00:00.165",
        "2022:295:00:00:00.421",
        "2022:295:00:00:00.677",
        "2022:295:00:00:00.934",
    ]
    assert np.all(CxoTime(dat.times).date == exp_dates)
    assert np.allclose(dat.vals, exp_vals, rtol=0, atol=1e-4)


def test_roll_comp():
    """Test roll_comp during a time with NPNT, NMAN, NSUN and Safe Sun"""
    start = "2022:293"
    stop = "2022:297"
    dat = fetch_eng.Msid("roll_comp", start, stop)
    dat.interpolate(dt=10000)
    # fmt: off
    exp = np.array(
        [
            7.32, 4.61, 7.51, 7.7, 7.84, 6.61, 0.02, -0.08, -0.1, -0.1, -0.08, -0.1,
            -0.11, -0.11, -0.1, -0.41, -0.37, -0.41, -0.19, -0.32, -0.32, -0.34, -0.34,
            -0.34, -0.08, -0.1, -0.07, -0.04, -0.1, -0.08, -0.08, -0.08, -0.08, 0.03,
            0.11
        ]
    )
    # fmt: on
    assert np.allclose(dat.vals, exp, rtol=0, atol=2e-2)


def test_dp_pitch_css():
    """Test dp_roll_css_derived during a time with NPNT, NMAN, NSUN"""
    from cheta.derived import pcad

    start = "2022:292"
    stop = "2022:294"
    dp = pcad.DP_PITCH_CSS()
    tlm = dp.fetch(start, stop)
    vals = dp.calc(tlm)
    vals = np.round(vals[::1000], 4)
    # fmt: off
    exp = np.array(
        [
           125.1838, 125.1838, 125.1811, 125.2076,  47.6423,  48.248 ,  # noqa
           100.2035, 100.0847, 112.813 , 171.7346, 171.697 ,  52.9446,  # noqa
            48.1135,  50.0441, 167.0614, 167.0853, 167.0853, 167.1091,  # noqa
            61.0159,  61.0188,  60.9992,  61.0245, 150.7093, 167.196 ,  # noqa
           167.2436, 167.2436, 148.7973,  61.0963,  61.1217,  61.0996,  # noqa
            61.1278,  92.0449, 167.3727, 167.4203, 167.8648, 171.0578,  # noqa
            90.8391,  90.122 ,  90.0533,  90.122 ,  90.0744,  90.0506,  # noqa
            90.0506  # noqa
        ]
    )
    # fmt: on
    assert np.allclose(vals, exp, rtol=0, atol=2e-4)


def test_dp_roll_css():
    """Test dp_roll_css_derived during a time with NPNT, NMAN, NSUN"""
    from cheta.derived import pcad

    start = "2022:292"
    stop = "2022:294"
    dp = pcad.DP_ROLL_CSS()
    tlm = dp.fetch(start, stop)
    vals = dp.calc(tlm)
    vals = np.round(vals[::1000], 4)
    # fmt: off
    exp = np.array(
        [
            -0.1177, -0.1177, -0.0841, -0.1009, -0.1116, -0.1474, -0.0838,  # noqa
             1.5221, -0.7457, -1.9128, -1.2376, -0.1206, -0.1477, -0.1614,  # noqa
            -0.2456, -0.1845, -0.1845, -0.    ,  4.0894,  4.1838,  4.2319,  # noqa
             4.2781,  3.4863,  0.1241,  0.1245,  0.1245,  3.9834,  4.5902,  # noqa
             4.6363,  4.6845,  4.7305,  6.936 ,  0.6917,  0.6943, -0.1962,  # noqa
            -0.6191, -0.1237, -0.0962, -0.0825, -0.0962, -0.0962, -0.0825,  # noqa
            -0.0825  # noqa
        ]
    )
    # fmt: on
    assert np.allclose(vals, exp, rtol=0, atol=2e-4)
