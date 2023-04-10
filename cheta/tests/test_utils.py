# Licensed under a 3-clause BSD style license - see LICENSE.rst
import astropy.units as u
import numpy as np
import pytest
from cxotime import CxoTime

from cheta import fetch
from cheta.utils import (
    get_fetch_size,
    get_ofp_states,
    get_telem_table,
)


def test_get_fetch_size_functionality():
    """
    Various functionality tests for estimating fetch memory usage.
    """
    fetch_mb, out_mb = get_fetch_size("aopcadmd", "2010:001", "2011:001")
    assert fetch_mb, out_mb == (399.97, 399.97)

    fetch_mb, out_mb = get_fetch_size(
        "aopcadmd", "2010:001", "2011:001", interpolate_dt=1.025 * 10
    )
    assert fetch_mb, out_mb == (399.97, 40.0)

    fetch_mb, out_mb = get_fetch_size(
        "aopcadmd", "2010:001", "2011:001", fast=False, stat="5min"
    )
    assert fetch_mb, out_mb == (1.92, 1.92)

    # 5min stat
    fetch_mb, out_mb = get_fetch_size("aopcadmd", "2010:001", "2011:001", stat="5min")
    assert fetch_mb, out_mb == (-1, -1)

    # Too short
    fetch_mb, out_mb = get_fetch_size("aopcadmd", "2010:001", "2010:030")
    assert fetch_mb, out_mb == (-1, -1)


def test_get_fetch_size_accuracy():
    """
    Does it give the right answer?
    """
    # By hand for stat
    dat = fetch.MSID("aopcadmd", "2010:001", "2011:001", stat="5min")
    fetch_bytes = sum(getattr(dat, attr).nbytes for attr in dat.colnames)

    fetch_mb, out_mb = get_fetch_size(
        "aopcadmd",
        "2010:001",
        "2011:001",
        stat="5min",
        interpolate_dt=328 * 2,
        fast=False,
    )
    assert np.isclose(fetch_mb, fetch_bytes / 1e6, rtol=0.0, atol=0.01)

    # Now interpolate to 10 minute intervals
    dat.interpolate(328.0 * 2)
    fetch_bytes = sum(getattr(dat, attr).nbytes for attr in dat.colnames)
    assert np.isclose(out_mb, fetch_bytes / 1e6, rtol=0.0, atol=0.01)

    # By hand for full resolution
    dat = fetch.MSID("aopcadmd", "2011:001", "2011:010")
    fetch_bytes = sum(getattr(dat, attr).nbytes for attr in dat.colnames)

    fetch_mb, out_mb = get_fetch_size(
        "aopcadmd", "2011:001", "2011:010", interpolate_dt=328 * 2, fast=False
    )
    assert np.isclose(fetch_mb, fetch_bytes / 1e6, rtol=0.0, atol=0.01)

    # Now interpolate to 10 minute intervals
    dat.interpolate(328.0 * 2)
    fetch_bytes = sum(getattr(dat, attr).nbytes for attr in dat.colnames)
    assert np.isclose(out_mb, fetch_bytes / 1e6, rtol=0.0, atol=0.01)


def test_get_ofp_states():
    out = get_ofp_states("2022:292", "2022:297")
    # Reference values take from original implementation of get_ofp_states in kadi.utils
    # *except* that start and stop values now match the supplied start/stop.
    exp = [
        "      datestart              datestop       val ",
        "--------------------- --------------------- ----",
        "2022:292:00:00:00.000 2022:293:16:27:57.429 NRML",
        "2022:293:16:27:57.429 2022:293:16:27:59.479 STUP",
        "2022:293:16:27:59.479 2022:293:16:28:00.504 SYON",
        "2022:293:16:28:00.504 2022:294:16:32:25.285 NRML",
        "2022:294:16:32:25.285 2022:294:16:32:27.347 STUP",
        "2022:294:16:33:01.794 2022:295:16:48:09.260 SAFE",
        "2022:295:16:48:09.260 2022:295:16:49:49.722 STUP",
        "2022:295:16:50:22.339 2022:295:17:22:56.002 STUP",
        "2022:295:17:22:56.002 2022:295:17:22:57.027 SYSF",
        "2022:295:17:22:57.027 2022:295:17:41:01.477 SAFE",
        "2022:295:17:41:01.477 2022:297:00:00:00.000 NRML",
    ]

    assert out["datestart", "datestop", "val"].pformat_all() == exp


@pytest.mark.parametrize("dt", [0.001, 1.0])
def test_get_ofp_states_safe_mode_short(dt):
    """Test getting OFP states where the time range is within the SAFE mode and
    there is zero or one sample of CONLOFP in the range."""
    start = CxoTime("2022:295")
    stop = start + dt * u.s
    out = get_ofp_states(start, stop)
    secs = {0.001: "00.001", 1.0: "01.000"}[dt]
    exp = [
        "      datestart              datestop       val ",
        "--------------------- --------------------- ----",
        f"2022:295:00:00:00.000 2022:295:00:00:{secs} SAFE",
    ]

    assert out["datestart", "datestop", "val"].pformat_all() == exp


@pytest.mark.parametrize("dt", [0.001, 1.0])
def test_get_telem_table(dt):
    """Test getting telemetry where the time range is within the sampling of one
    of the secondary MSIDs."""
    start = CxoTime("2022:295:00:00:00.000")
    stop = start + dt * u.s
    dat = get_telem_table(["conlofp", "orbitephem0_x"], start, stop)
    dat["orbitephem0_x"].info.format = ".2f"

    exp = {
        1.0: [  # One sample in primary MSID
            "     time     conlofp orbitephem0_x",
            "------------- ------- -------------",
            "782784069.605    SAFE  -13267583.62",
        ],
        0.001: [  # No samples in primary MSID
            "time conlofp orbitephem0_x",
            "---- ------- -------------",
        ],
    }

    assert dat.pformat_all() == exp[dt]
