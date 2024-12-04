# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Describe what this module does.
"""

import copy

import numpy as np
from ska_tdb import msids as tdb_msids
from ska_tdb import tables

from cheta import fetch_eng as fetch
from cheta.utils import logical_intervals, state_intervals

MNF_TIME = 0.25625  # Minor frame time (s)


def adjust_time(msid, start, stop):
    """
    Apply an offset to cheta timestamps to achieve minor frame time resolution

    Given an msid returned by fetch.MSID or fetch.Msid and a time interval,
    determine the time offset for each sample.  Time offset is based on the TDB
    and the Telemetry format at the time.  Only applies to msids retrieved with
    'cxc' as a data source

    Notes/Improvements:

    - TBD: Should accept MSIDSet in addition to MSID as input, but this could
      interfere with the current MSIDSet.interpolate() behavior
    - TBD: add an option for in-place adjustment
    - TBD: - maybe take msid as string, but manually set data source to avoid
      'maude' 'cxc' differences...
    - NOTE: Could use times from the msid.times span, but may create problems at
      the beginning and end since these are subject to adjustment.  Should use
      time query that generated the MSID

    :param msid: fetch ``MSID`` or ``Msid`` object
        MSID for which to calculate the time adjustments statistics for.
    :param start: str, ``CxoTime``, ``DateTime``
        Start time (CxoTime-compatible format)
    :param stop: str, ``CxoTime``, ``DateTime``
        Stop time (CxoTime-compatible format)

    :returns: fetch ``MSID`` or ``Msid`` object
    """
    samp_rate = tables["tsmpl"][msid.msid]["SAMPLE_RATE"]
    str_num = tables["tsmpl"][msid.msid]["STREAM_NUMBER"]
    start_minor_frame = tables["tloc"][msid.msid]["START_MINOR_FRAME"]
    # stream# to FMT name converter. Unsure if FMT6/SHuttle data needs to be handled
    fmt_dict = {
        1: "FMT1",
        2: "FMT2",
        3: "FMT3",
        4: "FMT4",
        5: "FMT5",
        72: "FMT6",
        6: "FMT6",
    }
    # for each format, generate time offset based on stream number,  sample
    # rate and  start minor frame...
    t_off = {}
    t_samp = {}
    str_num_2_idx = {}
    idx = 0

    # Build stream number to index decoder ring.  For each MSID there will be N
    # stream number entries in the table.  There's probably a list comprehension
    # way to do this
    for stream in str_num:
        str_num_2_idx[stream] = idx
        idx += 1

    for stream in str_num:
        # Now  calculate the offset and sample rate for each stream
        # off_secs = 128/samp_rate -1 # magnitude of offset. For SR = 128 it's 0,
        # for SR = 64 it's 0,1, for SR = 32, it's 0,1,2,3 &c.
        fmt = fmt_dict[stream]
        # Note this will fail for very long data sets.  Should use average mission
        # rate or clock look up table.
        off_phase = MNF_TIME * start_minor_frame[str_num_2_idx[stream]]
        t_off[fmt] = off_phase
        # 128 -> 0.25625, 64 -> 0.51250 , &c.
        t_samp[fmt] = (128 / samp_rate[str_num_2_idx[stream]]) * 0.25625

    # Get Telemetry format for the time interval in question.  CCSDSTMF is
    # updated 128x per MjF, so it's at max time resolution
    tmf = fetch.Msid("CCSDSTMF", start, stop)

    # Generate list of intervals for each format using logical intervals
    fmts = ("FMT1", "FMT2", "FMT3", "FMT4", "FMT5", "FMT6")
    tmf_intervals = {}
    for fmt in fmts:
        tmf_intervals[fmt] = logical_intervals(
            tmf.times, tmf.vals == fmt, complete_intervals=False
        )

    # Make scratchpad copy to avoid in-place effects (I think need to check by
    # ref or by val convention)
    times = msid.times.copy()
    for fmt in fmts:
        for interval in tmf_intervals[fmt]:
            # Now traverse each interval in the msid to be adjusted and add the appropriate offset.
            times[
                (msid.times >= interval["tstart"]) & (msid.times < interval["tstop"])
            ] += t_off[fmt]  # not positive on >= convention

    # This is abusing the MSID class a bit.  Not sure how to create 'empty' MSID object
    out_msid = copy.deepcopy(msid)
    out_msid.times = times
    return out_msid


def get_hi_res_times(msid, fmt_intervals=None):
    """
    Determine MSID timestamps to achieve minor frame time resolution.

    Given an msid returned by fetch.MSID or fetch.Msid determine the time offset
    for each sample. Time offset is based on the TDB and the Telemetry format
    at the time. Only applies to msids retrieved with 'cxc' as a data source

    :param msid: ``MSID`` or ``Msid`` object
        MSID for which to calculate the time adjustments statistics.
    :param fmt_intervals: TBD

    :returns: (np.array, TDB)
        Return tuple of (hi-res times, telemetry format intervals)
    """
    # TODO: check for data_source
    # TODO: check for stats MSID

    try:
        tdb_msid = tdb_msids[msid.msid]
    except KeyError:
        raise ValueError(f"msid {msid.msid} is not in TDB")

    # stream# to FMT name converter. Unsure if FMT6/SHuttle data needs to be handled
    fmt_dict = {
        1: "FMT1",
        2: "FMT2",
        3: "FMT3",
        4: "FMT4",
        5: "FMT5",
        72: "FMT6",
        6: "FMT6",
    }

    # For each format, generate time offset based on stream number
    t_off = {}
    for stream, start_minor_frame in zip(
        tdb_msid.Tloc["STREAM_NUMBER"], tdb_msid.Tloc["START_MINOR_FRAME"]
    ):
        fmt = fmt_dict[stream]
        # Note this will fail for very long data sets.  Should use average mission
        # rate or clock look up table.
        t_off[fmt] = MNF_TIME * start_minor_frame

    if fmt_intervals is None:
        msid_fmt = fetch.Msid("CCSDSTMF", msid.tstart, msid.tstop)
        fmt_intervals = state_intervals(msid_fmt.times, msid_fmt.vals)

    # This gives start/stop indices that are equivalent to:
    # (msid.times >= fmt_interval['tstart']) & (msid.times < fmt_interval['tstop'])
    # Note see: Boolean masks and np.searchsorted() in
    # https://occweb.cfa.harvard.edu/twiki/bin/view/Aspect/SkaPython#Ska_idioms_and_style
    i_starts = np.searchsorted(msid.times, fmt_intervals["tstart"])
    i_stops = np.searchsorted(msid.times, fmt_intervals["tstop"])

    times = msid.times.copy()
    for i_start, i_stop, fmt in zip(i_starts, i_stops, fmt_intervals["val"]):
        times[i_start:i_stop] += t_off[fmt]

    return times, fmt_intervals
