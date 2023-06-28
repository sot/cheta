# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Utilities for the engineering archive.
"""
import functools
import re
from contextlib import contextmanager

import astropy.units as u
import numpy as np
import six
from astropy.table import Table
from Chandra.Time import DateTime
from cxotime import CxoTime, CxoTimeLike
from ska_helpers import intervals

# Cache the results of fetching 3 days of telemetry keyed by MSID
FETCH_SIZES = {}

# Standard intervals for 5min and daily telemetry
STATS_DT = {"5min": 328, "daily": 86400}


class NoTelemetryError(Exception):
    """No telemetry available for the specified interval"""


# Make these functions available in this namespace after moving them to ska_helpers.
logical_intervals = intervals.logical_intervals
state_intervals = intervals.state_intervals

def get_fetch_size(msids, start, stop, stat=None, interpolate_dt=None, fast=True):
    """
    Estimate the memory size required to fetch the ``msids`` between ``start`` and
    ``stop``.  This is generally intended for limiting queries to be less than ~100 Mb and
    allows for making some assumptions for improved performance (see below).

    Returns a tuple of the estimated megabytes of memory for the raw fetch and megabytes
    for the final output (which is different only in the case of interpolating).  This is
    done by fetching 3 days of telemetry (2010:001 to 2010:004) and scaling appropriately.

    If ``fast`` is True (default) then if either of the conditions below apply a result of
    (-1, -1) is returned, indicating that the fetch will probably be less than ~100 Mb and
    should be OK.  (This does not account for the number of MSIDs passed in ``msids``).

      - Fetch duration (stop - start) is less than 30 days
      - Fetch ``stat`` is '5min' or 'daily'

    :param msids: list of MSIDs or a single MSID
    :param start: start time
    :param stop: stop time
    :param stat: fetch stat (None|'5min'|'daily', default=None)
    :param interpolate_dt: interpolate the output to uniform time steps (default=None)
    :param fast: return (-1, -1) if conditions on duration / stat (default=True)

    :returns: fetch_Mb, interpolated_Mb
    """

    start = DateTime(start)
    stop = DateTime(stop)

    # Short circuit in the case of a short fetch or not full-resolution telemetry
    if fast and (stop - start < 30 or stat is not None):
        return -1, -1

    from . import fetch

    # Allow for a single MSID input and make all values lower-case
    if isinstance(msids, six.string_types):
        msids = [msids]
    msids = [msid.lower() for msid in msids]

    for msid in msids:
        if (msid, stat) in FETCH_SIZES:
            fetch_bytes, fetch_rows = FETCH_SIZES[msid, stat]
        else:
            dat = fetch.MSID(msid, "2010:001:00:00:01", "2010:004:00:00:01", stat=stat)
            fetch_bytes = sum(getattr(dat, attr).nbytes for attr in dat.colnames)
            fetch_rows = len(dat.vals)
            FETCH_SIZES[msid, stat] = (fetch_bytes, fetch_rows)

    scale = (stop - start) / 3.0
    fetch_bytes = sum(FETCH_SIZES[msid, stat][0] * scale for msid in msids)

    # Number of output rows = total fetch time (days) / interpolate interval in days
    if interpolate_dt is None:
        out_bytes = fetch_bytes
    else:
        n_rows_out = (stop - start) / (interpolate_dt / 86400)
        out_bytes = sum(
            FETCH_SIZES[msid, stat][0] * n_rows_out / FETCH_SIZES[msid, stat][1]
            for msid in msids
        )

    return round(fetch_bytes / 1e6, 2), round(out_bytes / 1e6, 2)


def ss_vector(start, stop=None, obj="Earth"):
    """Calculate vector to Earth, Sun, or Moon in Chandra body coordinates
    between ``start`` and ``stop`` dates at 5 minute (328 sec) intervals.

    The return value in a NumPy structured array table (see below) which
    contains the distance in km from Chandra to the the solar system object
    along with the corresponding direction vectors in Chandra body coordinates
    and in the ECI frame.  For convenience the attitude quaternion components
    are also provided.

    Output table columns:

    * times: time in CXC seconds
    * distance: Distance to object (km)
    * body_x: X component of object in Chandra body coordinates
    * body_y: Y component of object in Chandra body coordinates
    * body_z: Z component of object in Chandra body coordinates
    * eci_x: X component of object relative to Chandra in ECI coordinates
    * eci_y: Y component of object relative to Chandra in ECI coordinates
    * eci_z: Z component of object relative to Chandra in ECI coordinates
    * q1: component 1 of the attitude quaternion
    * q2: component 2 of the attitude quaternion
    * q3: component 3 of the attitude quaternion
    * q4: component 4 of the attitude quaternion

    Example::

      from cheta.utils import ss_vector
      from Ska.Matplotlib import plot_cxctime
      vec = ss_vector('2010:001', '2010:030', obj='Sun')
      figure(1)
      clf()
      subplot(2, 1, 1)
      plot_cxctime(vec['times'], vec['body_x'], '-b')
      plot_cxctime(vec['times'], vec['body_y'], '-r')
      plot_cxctime(vec['times'], vec['body_z'], '-g')
      subplot(2, 1, 2)
      plot_cxctime(vec['times'], vec['distance'])

    :param start: start time (DateTime format)
    :param stop: stop time (DateTime format)
    :param obj: solar system object ('Earth', 'Moon', 'Sun')

    :returns: table of vector values
    """
    from itertools import count

    from Quaternion import Quat
    from scipy.interpolate import interp1d

    from . import fetch

    sign = dict(earth=-1, sun=1, moon=1)
    obj = obj.lower()
    if obj not in sign:
        raise ValueError("obj parameter must be one of {0}".format(list(sign.keys())))

    tstart = DateTime(start).secs
    tstop = DateTime(stop).secs
    q_att_msids = ["aoattqt1", "aoattqt2", "aoattqt3", "aoattqt4"]
    q_atts = fetch.MSIDset(q_att_msids, tstart, tstop, stat="5min")

    q_atts_times = set(len(q_atts[x].times) for x in q_att_msids)
    if len(q_atts_times) != 1:
        raise ValueError("Inconsistency in sampling for aoattqt<N>")

    axes = ["x", "y", "z"]
    prefixes = {"earth": "orbitephem1", "sun": "solarephem1", "moon": "lunarephem1"}
    objs = set(["earth", obj])
    msids = ["{0}_{1}".format(prefixes[y], x) for x in axes for y in objs]

    # Pad the fetch so interp always works
    ephem = fetch.MSIDset(msids, tstart - 1000, tstop + 1000, filter_bad=True)
    times = q_atts["aoattqt1"].times
    times0 = times - tstart
    obj_ecis = np.zeros(shape=(len(times0), 3), dtype=float)
    for i, axis in enumerate(axes):
        for obj in objs:
            msid = "{0}_{1}".format(prefixes[obj], axis)
            ephem_interp = interp1d(
                ephem[msid].times - tstart, ephem[msid].vals, kind="linear"
            )
            obj_ecis[:, i] += sign[obj] * ephem_interp(times0)

    distances = np.sqrt(np.sum(obj_ecis * obj_ecis, 1))

    bad_q_atts = []  # List of inconsistent quaternion values in telemetry
    p_obj_body = np.ndarray((len(times0), 3), dtype=float)
    for i, obj_eci, distance, time, q1, q2, q3, q4 in zip(
        count(),
        obj_ecis,
        distances,
        times0,
        q_atts["aoattqt1"].midvals,
        q_atts["aoattqt2"].midvals,
        q_atts["aoattqt3"].midvals,
        q_atts["aoattqt4"].midvals,
    ):
        try:
            q_att = Quat([q1, q2, q3, q4])
        except ValueError:
            bad_q_atts.append(i)
            continue
        p_obj_eci = obj_eci / distance
        p_obj_body[i, :] = np.dot(q_att.transform.transpose(), p_obj_eci)

    out = np.rec.fromarrays(
        [
            times,
            distances / 1000.0,
            p_obj_body[:, 0],
            p_obj_body[:, 1],
            p_obj_body[:, 2],
            obj_ecis[:, 0] / distances,
            obj_ecis[:, 1] / distances,
            obj_ecis[:, 2] / distances,
            q_atts["aoattqt1"].midvals,
            q_atts["aoattqt2"].midvals,
            q_atts["aoattqt3"].midvals,
            q_atts["aoattqt4"].midvals,
        ],
        names=[
            "times",
            "distance",
            "body_x",
            "body_y",
            "body_z",
            "eci_x",
            "eci_y",
            "eci_z",
            "q1",
            "q2",
            "q3",
            "q4",
        ],
    )
    if bad_q_atts:
        ok = np.ones(len(out), dtype=bool)
        ok[bad_q_atts] = False
        out = out[ok]

    return out


def get_telem_table(
    msids: list,
    start: CxoTimeLike,
    stop: CxoTimeLike,
    time_pad: u.Quantity = 15 * u.min,
    unit_system: str = "eng",
) -> Table:
    """
    Fetch telemetry for a list of MSIDs and return as an Astropy Table.

    This interpolates all the MSIDs to the time base of the first MSID in the list. It
    also fetches ``time_pad`` more than requested to ensure that the samples are
    complete (e.g. if the interval is between MSID samples).

    If no telemetry is available for the requested interval then an empty table is
    returned with all float columns.

    :param msids: fetch msids list
    :param start: start time for telemetry (CxoTime-like)
    :param stop: stop time for telemetry (CxoTime-like)
    :param time_pad: Quantity time pad on each end for fetch (default=15 min)
    :param unit_system: unit system for fetch ("eng" | "cxc" | "sci", default="eng")

    :returns: Table of requested telemetry values from fetch
    """
    from cheta import fetch, fetch_eng, fetch_sci

    start = CxoTime(start)
    stop = CxoTime(stop)
    names = ["time"] + msids
    fetch_module = {"eng": fetch_eng, "cxc": fetch, "sci": fetch_sci}[unit_system]

    # Get the MSIDset for the requested MSIDs and time range with some padding to
    # ensure samples even for slow MSIDS like ephemeris at 5-min cadence.
    msidset = fetch_module.MSIDset(msids, start - time_pad, stop + time_pad)

    if any(len(msidset[msid]) == 0 for msid in msids):
        # If no telemetry was found then return an empty table with the expected names
        # but all float64 columns.
        out = Table(names=names)
        return out

    # Use the first MSID as the primary one to set the time base
    msid0 = msidset[msids[0]]
    times = msid0.times
    i0, i1 = np.searchsorted(times, [start.secs, stop.secs])
    times = times[i0:i1]

    msidset.interpolate(times=times, bad_union=True)

    out = Table([msidset.times] + [msidset[x].vals for x in msids], names=names)
    out["time"].info.format = ".3f"

    return out


@functools.lru_cache(maxsize=1)
def get_ofp_states(start, stop):
    """Get the Onboard Flight Program (OFP) states between ``start`` and ``stop`.

    This is normally "NRML" but in safe mode it is "SAFE" or other values. State codes:
    ['NNRM' 'STDB' 'STBS' 'NRML' 'NSTB' 'SUOF' 'SYON' 'DPLY' 'SYSF' 'STUP' 'SAFE']

    :param start: start time (CxoTimeLike)
    :param stop: stop time (CxoTimeLike)
    :returns: astropy Table of OFP state intervals
    """
    from astropy.table import vstack

    start = CxoTime(start)
    stop = CxoTime(stop)

    msid = "conlofp"
    tlm = get_telem_table([msid], start - 30 * u.s, stop + 30 * u.s)

    if len(tlm) == 0:
        raise NoTelemetryError(f"No telemetry for {msid} between {start} and {stop}")

    states_list = []
    for state_code in np.unique(tlm[msid]):
        states = logical_intervals(
            tlm["time"],
            tlm[msid] == state_code,
            max_gap=2.1,
            complete_intervals=False,
            start=start,
            stop=stop,
        )
        states["val"] = state_code
        states_list.append(states)

    states = vstack(states_list)
    states.sort("datestart")

    return states


def get_date_id(date):
    """
    Get date_id format used in sync repo index.

    :param date:
    :return: date_id
    """
    date_id = DateTime(date).fits
    date_id = re.sub(":", "", date_id[:16]) + "z"
    return date_id


@contextmanager
def set_fetch_basedir(basedir):
    """
    Temporarily override the base directory that fetch uses for telemetry data.

    Example to use local data::

      >>> with set_fetch_basedir('.'):
      ...     dat = fetch.Msid('aacccdpt', '2018:001', '2018:100')

    :param basedir: str or os.PathLike, base directory for cheta data
    """
    from . import fetch

    orig_basedir = fetch.msid_files.basedir
    fetch.msid_files.basedir = str(basedir)
    try:
        yield
    finally:
        fetch.msid_files.basedir = orig_basedir
