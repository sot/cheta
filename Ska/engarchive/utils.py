"""
Utilities for the engineering archive.
"""
from __future__ import print_function, absolute_import, division

import numpy as np
from Chandra.Time import DateTime


def ss_vector(start, stop=None, obj='Earth'):
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

      from Ska.engarchive.utils import ss_vector
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
        raise ValueError('obj parameter must be one of {0}'
                         .format(list(sign.keys())))

    tstart = DateTime(start).secs
    tstop = DateTime(stop).secs
    q_att_msids = ['aoattqt1', 'aoattqt2', 'aoattqt3', 'aoattqt4']
    q_atts = fetch.MSIDset(q_att_msids, tstart, tstop, stat='5min')

    q_atts_times = set(len(q_atts[x].times) for x in q_att_msids)
    if len(q_atts_times) != 1:
        raise ValueError('Inconsistency in sampling for aoattqt<N>')

    axes = ['x', 'y', 'z']
    prefixes = {'earth': 'orbitephem1',
                'sun': 'solarephem1',
                'moon': 'lunarephem1'}
    objs = set(['earth', obj])
    msids = ['{0}_{1}'.format(prefixes[y], x) for x in axes for y in objs]

    # Pad the fetch so interp always works
    ephem = fetch.MSIDset(msids, tstart - 1000, tstop + 1000, filter_bad=True)
    times = q_atts['aoattqt1'].times
    times0 = times - tstart
    obj_ecis = np.zeros(shape=(len(times0), 3), dtype=float)
    for i, axis in enumerate(axes):
        for obj in objs:
            msid = '{0}_{1}'.format(prefixes[obj], axis)
            ephem_interp = interp1d(ephem[msid].times - tstart,
                                    ephem[msid].vals, kind='linear')
            obj_ecis[:, i] += sign[obj] * ephem_interp(times0)

    distances = np.sqrt(np.sum(obj_ecis * obj_ecis, 1))

    bad_q_atts = []  # List of inconsistent quaternion values in telemetry
    p_obj_body = np.ndarray((len(times0), 3), dtype=float)
    for i, obj_eci, distance, time, q1, q2, q3, q4 in zip(
        count(), obj_ecis, distances, times0, q_atts['aoattqt1'].midvals,
        q_atts['aoattqt2'].midvals, q_atts['aoattqt3'].midvals,
        q_atts['aoattqt4'].midvals):
        try:
            q_att = Quat([q1, q2, q3, q4])
        except ValueError:
            bad_q_atts.append(i)
            continue
        p_obj_eci = obj_eci / distance
        p_obj_body[i, :] = np.dot(q_att.transform.transpose(), p_obj_eci)

    out = np.rec.fromarrays([times,
                             distances / 1000.0,
                             p_obj_body[:, 0],
                             p_obj_body[:, 1],
                             p_obj_body[:, 2],
                             obj_ecis[:, 0] / distances,
                             obj_ecis[:, 1] / distances,
                             obj_ecis[:, 2] / distances,
                             q_atts['aoattqt1'].midvals,
                             q_atts['aoattqt2'].midvals,
                             q_atts['aoattqt3'].midvals,
                             q_atts['aoattqt4'].midvals],
                            names=['times', 'distance',
                                   'body_x', 'body_y', 'body_z',
                                   'eci_x', 'eci_y', 'eci_z',
                                   'q1', 'q2', 'q3', 'q4'])
    if bad_q_atts:
        ok = np.ones(len(out), dtype=bool)
        ok[bad_q_atts] = False
        out = out[ok]

    return out


def _pad_long_gaps(times, bools, max_gap):
    dts = np.diff(times)
    i_long_gaps = np.flatnonzero(dts > max_gap)
    print(i_long_gaps)
    if len(i_long_gaps) > 0:
        for i in i_long_gaps[::-1]:
            times = np.concatenate([times[:i + 1],
                                    [times[i] + max_gap / 2.0, times[i + 1] - max_gap / 2.0],
                                    times[i + 1:]])
            bools = np.concatenate([bools[:i + 1],
                                    [False, False],
                                    bools[i + 1:]])
    return times, bools


def logical_intervals(times, bools, complete_intervals=True, max_gap=None):
    """Determine contiguous intervals during which `bools` is True.

    If ``complete_intervals`` is True (default) then the intervals are guaranteed to
    be complete so that the all reported intervals had a transition before and after
    within the telemetry interval.

    If ``max_gap`` is specified then any time gaps longer than ``max_gap`` are
    filled with a fictitious False value to create an artificial interval
    boundary at ``max_gap / 2`` seconds from the nearest data value.

    Returns an astropy Table with a row for each interval.  Columns are:

    * datestart: date of interval start
    * datestop: date of interval stop
    * duration: duration of interval (sec)
    * tstart: time of interval start (CXC sec)
    * tstop: time of interval stop (CXC sec)

    Example (find SCS107 runs via telemetry)::

      >>> from Ska.engarchive import utils, fetch
      >>> dat = fetch.Msidset(['3tscmove', 'aorwbias', 'coradmen'], '2012:190', '2012:205')
      >>> dat.interpolate(32.8)  # Sample MSIDs onto 32.8 second intervals (like 3TSCMOVE)
      >>> scs107 = ((dat['3tscmove'].vals == 'T')
                    & (dat['aorwbias'].vals == 'DISA')
                    & (dat['coradmen'].vals == 'DISA'))
      >>> scs107s = utils.logical_intervals(dat.times, scs107)
      >>> print scs107s['datestart', 'datestop', 'duration']
            datestart              datestop          duration
      --------------------- --------------------- -------------
      2012:194:20:00:31.652 2012:194:20:04:21.252 229.600000083
      2012:196:21:07:36.452 2012:196:21:11:26.052 229.600000083
      2012:201:11:45:46.852 2012:201:11:49:36.452 229.600000083

    :param times: array of time stamps in CXC seconds
    :param bools: array of logical True/False values
    :param complete_intervals: return only complete intervals (default=True)
    :param max_gap: max allowed gap between time stamps (sec, default=None)
    :returns: Table of intervals
    """
    if max_gap is not None:
        times, bools = _pad_long_gaps(times, bools, max_gap)

    intervals = state_intervals(times, bools)

    if complete_intervals:
        if len(intervals) > 0 and intervals['val'][0]:
            intervals = intervals[1:]
        if len(intervals) > 0 and intervals['val'][-1]:
            intervals = intervals[:-1]

    ok = intervals['val']  # Intervals where bools is True
    del intervals['val']
    return intervals[ok]


def state_intervals(times, vals):
    """
    Determine contiguous intervals during which the ``vals`` is unchanged.

    Returns an Astropy Table with a row for each interval.  Columns are:

    * datestart: date of interval start
    * datestop: date of interval stop
    * duration: duration of interval (sec)
    * tstart: time of interval start (CXC sec)
    * tstop: time of interval stop (CXC sec)
    * val: MSID value during the interval

    Example::

      >>> from Ska.engarchive import fetch, utils
      >>> dat = fetch.Msid('cobsrqid', '2010:003', '2010:004')
      >>> obsids = utils.state_intervals(dat.times, dat.vals)
      >>> print obsids['datestart', 'datestop', 'val']
            datestart              datestop         val
      --------------------- --------------------- -------
      2010:003:12:00:00.976 2010:004:09:07:44.180 11011.0
      2010:004:09:07:44.180 2010:004:09:40:52.680 56548.0
      2010:004:09:40:52.680 2010:004:12:00:00.280 12068.0

    :param times: times (CXC seconds)
    :param vals: state values for which intervals are returned.
    :returns: structured array table of intervals
    """
    from astropy.table import Table

    if len(vals) < 2:
        raise ValueError('Filtered data length must be at least 2')

    transitions = np.hstack([[True], vals[:-1] != vals[1:], [True]])
    t0 = times[0] - (times[1] - times[0]) / 2
    t1 = times[-1] + (times[-1] - times[-2]) / 2
    midtimes = np.hstack([[t0], (times[:-1] + times[1:]) / 2, [t1]])

    state_vals = vals[transitions[1:]]
    state_times = midtimes[transitions]

    intervals = {'datestart': DateTime(state_times[:-1]).date,
                 'datestop': DateTime(state_times[1:]).date,
                 'tstart': state_times[:-1],
                 'tstop': state_times[1:],
                 'duration': state_times[1:] - state_times[:-1],
                 'val': state_vals}

    return Table(intervals, names=sorted(intervals))
