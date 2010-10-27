"""
Utilities for the engineering archive.
"""
from itertools import count, izip
from Quaternion import Quat
import numpy as np
from Chandra.Time import DateTime
from scipy.interpolate import interp1d
from Ska.engarchive import fetch

def ss_vector(start, stop=None, obj='Earth'):
    """Calculate vector to Earth, Sun, or Moon in Chandra body coordinates
    between ``start`` and ``stop`` dates at 5 minute (328 sec) intervals.

    The return value in a NumPy structured array table (see below) which contains the
    distance in km from Chandra to the the solar system object along with the
    corresponding direction vectors in Chandra body coordinates and in the ECI
    frame.  For convenience the attitude quaternion components are also provided.

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
    sign = dict(earth=-1, sun=1, moon=1)
    obj = obj.lower()
    if obj not in sign:
        raise ValueError('obj parameter must be one of {0}'.format(sign.keys()))

    tstart = DateTime(start).secs
    tstop = DateTime(stop).secs
    q_atts = fetch.MSIDset(['aoattqt1', 'aoattqt2', 'aoattqt3', 'aoattqt4'],
                           tstart, tstop, stat='5min')
    axes = ['x', 'y', 'z']
    prefixes = {'earth': 'orbitephem1',
                'sun': 'solarephem1',
                'moon': 'lunarephem1'}
    objs = set(['earth', obj])
    msids = ['{0}_{1}'.format(prefixes[y], x) for x in axes for y in objs]
    
    ephem = fetch.MSIDset(msids, tstart-1000, tstop+1000, filter_bad=True)  # pad so interp always works
    times = q_atts['aoattqt1'].times
    times0 = times - tstart
    obj_ecis = np.zeros(shape=(len(times0), 3), dtype=float)
    for i, axis in enumerate(axes):
        for obj in objs:
            msid = '{0}_{1}'.format(prefixes[obj], axis)
            ephem_interp = interp1d(ephem[msid].times - tstart, ephem[msid].vals, kind='linear')
            obj_ecis[:, i] += sign[obj] * ephem_interp(times0)

    distances = np.sqrt(np.sum(obj_ecis * obj_ecis, 1))

    p_obj_body = np.ndarray((len(times0), 3), dtype=float)
    for i, obj_eci, distance, time, q1, q2, q3, q4 in izip(
                                       count(), obj_ecis, distances, times0,
                                       q_atts['aoattqt1'].vals, q_atts['aoattqt2'].vals,
                                       q_atts['aoattqt3'].vals, q_atts['aoattqt4'].vals):
        q_att = Quat([q1, q2, q3, q4])
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
                             q_atts['aoattqt1'].vals, 
                             q_atts['aoattqt2'].vals, 
                             q_atts['aoattqt3'].vals, 
                             q_atts['aoattqt4'].vals],
                            names = ['times', 'distance',
                                     'body_x', 'body_y', 'body_z',
                                     'eci_x', 'eci_y', 'eci_z',
                                     'q1', 'q2', 'q3', 'q4'])
    return out

