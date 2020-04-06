# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Support computed MSIDs in the cheta archive.

- Base class ComputedMsid for user-generated comps.
- Cleaned MUPS valve temperatures MSIDs: '(pm2thv1t|pm1thv2t)_clean'.
- Commanded states 'cmd_state_<key>_<dt>' for any kadi commanded state value.
"""

import re

import numpy as np

from Chandra.Time import DateTime


def calc_stats_vals(msid, rows, indexes, interval):
    """
    Compute statistics values for ``msid`` over specified intervals.
    This is a very slightly modified version of the same function from
    update_archive.py.  However, cannot directly import that because
    it has side effects that break everything, probably related to
    enabling caching.

    The mods here are basically to take out handling of state codes
    and turn a warning about negative dts into an exception.

    :param msid: Msid object (filter_bad=True)
    :param rows: Msid row indices corresponding to stat boundaries
    :param indexes: Universal index values for stat (row times // dt)
    :param interval: interval name (5min or daily)
    """
    import scipy.stats

    quantiles = (1, 5, 16, 50, 84, 95, 99)
    n_out = len(rows) - 1

    # Check if data type is "numeric".  Boolean values count as numeric,
    # partly for historical reasons, in that they support funcs like
    # mean (with implicit conversion to float).
    msid_dtype = msid.vals.dtype
    msid_is_numeric = issubclass(msid_dtype.type, (np.number, np.bool_))

    # If MSID data is unicode, then for stats purposes cast back to bytes
    # by creating the output array as a like-sized S-type array.
    if msid_dtype.kind == 'U':
        msid_dtype = re.sub(r'U', 'S', msid.vals.dtype.str)

    # Predeclare numpy arrays of correct type and sufficient size for accumulating results.
    out = {}
    out['index'] = np.ndarray((n_out,), dtype=np.int32)
    out['n'] = np.ndarray((n_out,), dtype=np.int32)
    out['val'] = np.ndarray((n_out,), dtype=msid_dtype)

    if msid_is_numeric:
        out['min'] = np.ndarray((n_out,), dtype=msid_dtype)
        out['max'] = np.ndarray((n_out,), dtype=msid_dtype)
        out['mean'] = np.ndarray((n_out,), dtype=np.float32)

        if interval == 'daily':
            out['std'] = np.ndarray((n_out,), dtype=msid_dtype)
            for quantile in quantiles:
                out['p{:02d}'.format(quantile)] = np.ndarray((n_out,), dtype=msid_dtype)

    i = 0
    for row0, row1, index in zip(rows[:-1], rows[1:], indexes[:-1]):
        vals = msid.vals[row0:row1]
        times = msid.times[row0:row1]

        n_vals = len(vals)
        if n_vals > 0:
            out['index'][i] = index
            out['n'][i] = n_vals
            out['val'][i] = vals[n_vals // 2]
            if msid_is_numeric:
                if n_vals <= 2:
                    dts = np.ones(n_vals, dtype=np.float64)
                else:
                    dts = np.empty(n_vals, dtype=np.float64)
                    dts[0] = times[1] - times[0]
                    dts[-1] = times[-1] - times[-2]
                    dts[1:-1] = ((times[1:-1] - times[:-2]) +
                                 (times[2:] - times[1:-1])) / 2.0
                    negs = dts < 0.0
                    if np.any(negs):
                        times_dts = [(DateTime(t).date, dt)
                                     for t, dt in zip(times[negs], dts[negs])]
                        raise ValueError('WARNING - negative dts in {} at {}'
                                         .format(msid.MSID, times_dts))

                    # Clip to range 0.001 to 300.0.  The low bound is just there
                    # for data with identical time stamps.  This shouldn't happen
                    # but in practice might.  The 300.0 represents 5 minutes and
                    # is the largest normal time interval.  Data near large gaps
                    # will get a weight of 5 mins.
                    dts.clip(0.001, 300.0, out=dts)
                sum_dts = np.sum(dts)

                out['min'][i] = np.min(vals)
                out['max'][i] = np.max(vals)
                out['mean'][i] = np.sum(dts * vals) / sum_dts
                if interval == 'daily':
                    # biased weighted estimator of variance (N should be big enough)
                    # http://en.wikipedia.org/wiki/Mean_square_weighted_deviation
                    sigma_sq = np.sum(dts * (vals - out['mean'][i]) ** 2) / sum_dts
                    out['std'][i] = np.sqrt(sigma_sq)
                    quant_vals = scipy.stats.mstats.mquantiles(vals, np.array(quantiles) / 100.0)
                    for quant_val, quantile in zip(quant_vals, quantiles):
                        out['p%02d' % quantile][i] = quant_val

            i += 1

    return np.rec.fromarrays([x[:i] for x in out.values()], names=list(out.keys()))


class ComputedMsid:
    # Global dict of registered computed MSIDs
    msid_classes = []

    # Standard base MSID attributes that must be provided
    msid_attrs = ('times', 'vals', 'bads')

    # Extra MSID attributes that are provided beyond times, vals, bads
    extra_msid_attrs = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        cls.msid_attrs = ComputedMsid.msid_attrs + cls.extra_msid_attrs

        if not hasattr(cls, 'msid_match'):
            raise ValueError(f'comp {cls.__name__} must define msid_match')

        cls.msid_classes.append(cls)

    @classmethod
    def get_matching_comp_cls(cls, msid):
        for comp_cls in ComputedMsid.msid_classes:
            match = re.match(comp_cls.msid_match + '$', msid, re.IGNORECASE)
            if match:
                return comp_cls

        return None

    @property
    def fetch_eng(self):
        from .. import fetch_eng
        return fetch_eng

    @property
    def fetch_sci(self):
        from .. import fetch_sci
        return fetch_sci

    @property
    def fetch_cxc(self):
        from .. import fetch_cxc
        return fetch_cxc

    def __call__(self, tstart, tstop, msid, interval=None):
        match = re.match(self.msid_match, msid, re.IGNORECASE)
        if not match:
            raise RuntimeError(f'unexpected mismatch of {msid} with {self.msid_match}')
        match_args = [arg.lower() for arg in match.groups()]

        if interval is None:
            msid_attrs = self.get_msid_attrs(tstart, tstop, msid.lower(), match_args)
        else:
            msid_attrs = self.get_stats_attrs(tstart, tstop, msid.lower(), match_args, interval)

        return msid_attrs

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        """Get the attributes required for this MSID.

        TODO: detailed docs here since this is the main user-defined method
        """
        raise NotImplementedError()

    def get_stats_attrs(self, tstart, tstop, msid, match_args, interval):
        from ..fetch import _plural

        # Replicate a stripped-down version of processing in update_archive.
        # This produces a recarray with columns that correspond to the raw
        # stats HDF5 files.
        dt = {'5min': 328,
              'daily': 86400}[interval]
        index0 = int(np.floor(tstart / dt))
        index1 = int(np.ceil(tstop / dt))
        tstart = (index0 - 1) * dt
        tstop = (index1 + 1) * dt
        msid_obj = self.fetch_eng.Msid(msid, tstart, tstop)
        indexes = np.arange(index0, index1 + 1)
        times = indexes * dt  # This is the *start* time of each bin

        if len(times) > 0:
            rows = np.searchsorted(msid_obj.times, times)
            vals_stats = calc_stats_vals(msid_obj, rows, indexes, interval)
        else:
            raise ValueError()

        # Replicate the name munging that fetch does going from the HDF5 columns
        # to what is seen in a stats fetch query.
        out = {}
        for key in vals_stats.dtype.names:
            out_key = _plural(key) if key != 'n' else 'samples'
            out[out_key] = vals_stats[key]
        out['times'] = (vals_stats['index'] + 0.5) * dt
        out['bads'] = np.zeros(len(vals_stats), dtype=bool)
        out['midvals'] = out['vals']
        out['vals'] = out['means']

        return out


class Comp_MUPS_Valve_Temp_Clean(ComputedMsid):
    """Computed MSID for cleaned MUPS valve temps PM2THV1T, PM1THV2T

    This uses the cleaning method demonstrated in the following notebook
    to return a version of the MUPS valve temperature comprised of
    telemetry values that are consistent with a thermal model.

    https://nbviewer.jupyter.org/urls/cxc.cfa.harvard.edu/mta/ASPECT/ipynb/misc/mups-valve-xija-filtering.ipynb

    Allowed MSIDs are 'pm2thv1t_clean' and 'pm1thv2t_clean' (as always case is
    not important).
    """
    msid_match = r'(pm2thv1t|pm1thv2t)_clean'
    extra_msid_attrs = ('vals_raw', 'vals_nan', 'vals_corr', 'vals_model', 'source')

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        """Get attributes for computed MSID: ``vals``, ``bads``, ``times``

        :param tstart: start time (CXC secs)
        :param tstop: stop time (CXC secs)
        :param msid: full MSID name e.g. pm2thv1t_clean
        :param msid_args: tuple of regex match groups (msid_name,)

        :returns: dict of MSID attributes
        """
        from .mups_valve import fetch_clean_msid

        # Get cleaned MUPS valve temperature data as an MSID object
        dat = fetch_clean_msid(msid_args[0], tstart, tstop,
                               dt_thresh=5.0, median=7, model_spec=None, unit='degc')

        # Convert to dict as required by the get_msids_attrs API
        msid_attrs = {attr: getattr(dat, attr) for attr in self.msid_attrs}

        return msid_attrs


class Comp_KadiCommandState(ComputedMsid):
    """Computed MSID for kadi dynamic commanded states.

    The MSID here takes the form ``cmd_state_<state_key>_<dt>`` where:
    - ``state_key`` is a valid commanded state key such as ``pitch`` or
      ``pcad_mode`` or ``acisfp_temp``.
    - ``dt`` is the sampling time expressed as a multiple of 1.025 sec
      frames.

    Example MSID names::

      'cmd_state_pcad_mode_1': sample ``pcad_mode`` every 1.025 secs
      'cmd_state_acisfp_temp_32': sample ``acisfp_temp`` every 32.8 secs
    """
    msid_match = r'cmd_state_(\w+)_(\d+)'

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        """Get attributes for computed MSID: ``vals``, ``bads``, ``times``

        :param tstart: start time (CXC secs)
        :param tstop: stop time (CXC secs)
        :param msid: full MSID name e.g. cmd_state_pitch_clean
        :param msid_args: tuple of regex match groups: (state_key, dt)

        :returns: dict of MSID attributes
        """
        from kadi.commands.states import get_states
        from Chandra.Time import date2secs

        state_key = msid_args[0]
        dt = 1.025 * int(msid_args[1])
        states = get_states(tstart, tstop, state_keys=[state_key])

        tstart = date2secs(states['datestart'][0])
        tstops = date2secs(states['datestop'])

        times = np.arange(tstart, tstops[-1], dt)
        vals = states[state_key].view(np.ndarray)

        indexes = np.searchsorted(tstops, times)

        out = {'vals': vals[indexes],
               'times': times,
               'bads': np.zeros(len(times), dtype=bool)}

        return out
