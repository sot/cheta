import numpy as np
from cxotime import secs2date

from cheta import fetch
from cheta.time_offsets import MNF_TIME, adjust_time, get_hi_res_times


def test_time_adjust_adjust_time():
    cpa2pwr = fetch.Msid("cpa2pwr", "2020:230:00:00:01", "2020:230:00:00:04")
    cpa2pwr_adj = adjust_time(cpa2pwr, "2020:230:00:00:01", "2020:230:00:00:04")
    for t, t_adj in zip(cpa2pwr.times, cpa2pwr_adj.times):
        assert np.isclose(t_adj - t, MNF_TIME)  # MNF offset is 1 for this MSID


def test_time_adjust_get_hi_res_times():
    # Cover an interval that has formats 1, 2, and 4.
    start = "2020:030:03:00:00"
    stop = "2020:030:05:00:00"
    dat = fetch.Msid("tephin", start, stop)
    with fetch.data_source("maude allow_subset=False"):
        dat_maude = fetch.Msid("tephin", start, stop)

    dat_adj = adjust_time(dat, start, stop)
    dates_maude = secs2date(dat_maude.times)
    dates_adj = secs2date(dat_adj.times)
    assert np.all(dates_maude == dates_adj)

    times_adj, fmt_intervals = get_hi_res_times(dat)

    # Test re-using fmt_intervals
    times_adj2, fmt_intervals = get_hi_res_times(dat, fmt_intervals)

    assert np.all(times_adj == dat_adj.times)
    assert np.all(times_adj2 == times_adj)

    offsets = times_adj - dat.times
    assert np.allclose(offsets[:115], 59 * MNF_TIME)  # Format 2 MNF offset is 59
    assert np.allclose(offsets[115:1011], 0 * MNF_TIME)  # Format 4 MNF offset is 0
    assert np.allclose(offsets[1011:], 59 * MNF_TIME)  # Format 1 MNF offset is 59


def test_time_adjust_set_hi_res_times():
    start, stop = "2020:030:03:00:00", "2020:030:05:00:00"
    tephin = fetch.Msid("tephin", start, stop)
    times_adj, _ = get_hi_res_times(tephin)

    tephin.set_hi_res_times()
    assert np.all(tephin.times == times_adj)


def test_time_adjust_msidset_set_hi_res_times():
    start, stop = "2020:030:03:00:00", "2020:030:05:00:00"

    msids = fetch.Msidset(["tephin", "tcylaft6"], start, stop)
    msids.set_hi_res_times()

    for msid_name in ("tephin", "tcylaft6"):
        msid = fetch.Msid(msid_name, start, stop)
        times_adj, _ = get_hi_res_times(msid)
        assert np.all(msids[msid_name].times == times_adj)
