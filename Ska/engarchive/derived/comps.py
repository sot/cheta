# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Support computed MSIDs in the cheta archive.

- Base class ComputedMsid for user-generated comps.
- Cleaned MUPS valve temperatures MSIDs: '(pm2thv1t|pm1thv2t)_clean'.
- Commanded states 'cmd_state_<key>_<dt>' for any kadi commanded state value.
"""

import re

import numpy as np


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

    def __call__(self, start, stop, msid):
        match = re.match(self.msid_match, msid, re.IGNORECASE)
        if not match:
            raise RuntimeError(f'unexpected mismatch of {msid} with {self.msid_match}')
        match_args = [arg.lower() for arg in match.groups()]
        msid_attrs = self.get_msid_attrs(start, stop, msid.lower(), match_args)

        if set(msid_attrs) != set(self.msid_attrs):
            raise ValueError(f'computed class did not return expected attributes')

        return msid_attrs

    def get_msid_attrs(self, start, stop, msid, msid_args):
        """Get the attributes required for this MSID.

        TODO: detailed docs here since this is the main user-defined method
        """
        raise NotImplementedError()


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
                               dt_thresh=5.0, median=7, model_spec=None)

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

    def get_msid_attrs(self, start, stop, msid, msid_args):
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
        states = get_states(start, stop, state_keys=[state_key])

        tstart = date2secs(states['datestart'][0])
        tstops = date2secs(states['datestop'])

        times = np.arange(tstart, tstops[-1], dt)
        vals = states[state_key].view(np.ndarray)

        indexes = np.searchsorted(tstops, times)

        out = {'vals': vals[indexes],
               'times': times,
               'bads': np.zeros(len(times), dtype=bool)}

        return out
