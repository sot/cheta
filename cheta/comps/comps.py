# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Support computed MSIDs in the cheta archive.

- :class:`~cheta.comps.ComputedMsid`: base class for user-generated comps.
- :class:`~cheta.comps.Comp_MUPS_Valve_Temp_Clean`:
  Cleaned MUPS valve temperatures MSIDs ``(pm2thv1t|pm1thv2t)_clean``.
- :class:`~cheta.comps.Comp_KadiCommandState`:
  Commanded states ``cmd_state_<key>_<dt>`` for any kadi commanded state value.
- :class:`~cheta.comps.Comp_Quat`:
  Quaternions
    - ``quat_aoattqt`` = ``AOATTQT[1-4]``
    - ``quat_aoatupq`` = ``AOATUPQ[1-3]``
    - ``quat_aocmdqt`` = ``AOCMDQT[1-3]``
    - ``quat_aotarqt`` = ``AOTARQT[1-3]``
- :class:`~cheta.comps.Comp_Pitch_Roll_OBC_Safe`:
  Sun Pitch ``pitch_comp`` and off-nominal roll ``roll_comp`` which are valid in NPNT,
  NMAN, NSUN and safe mode.

See: https://nbviewer.jupyter.org/urls/cxc.harvard.edu/mta/ASPECT/ipynb/misc/DAWG-mups-valve-xija-filtering.ipynb
"""  # noqa

import functools
import warnings

import astropy.table as tbl
import numpy as np
from cxotime import CxoTime

from .computed_msid import ComputedMsid
from .ephem_stk import Comp_EphemSTK

__all__ = [
    "ComputedMsid",
    "Comp_EphemSTK",
    "Comp_KadiCommandState",
    "Comp_MUPS_Valve_Temp_Clean",
    "Comp_Pitch_Roll_OBC_Safe",
    "Comp_Quat",
]


class Comp_Quat(ComputedMsid):
    """Computed MSID for returning the quaternion telemetry as a Quat object

    This defines the following computed MSIDs based on the corresponding
    TDB MSIDs:

    - ``quat_aoattqt`` = ``AOATTQT[1-4]``
    - ``quat_aoatupq`` = ``AOATUPQ[1-3]``
    - ``quat_aocmdqt`` = ``AOCMDQT[1-3]``
    - ``quat_aotarqt`` = ``AOTARQT[1-3]``

    Example::

      >>> from cheta import fetch
      >>> qatt = fetch.Msid('quat_aoattqt', '2022:001:00:00:00', '2022:001:00:00:04')
      >>> qatt.vals
      Quat(array([[-0.07434856, -0.55918674, -0.80432653,  0.18665828],
                  [-0.07434854, -0.55918679, -0.8043265 ,  0.18665825],
                  [-0.07434849, -0.55918674, -0.80432653,  0.18665829],
                  [-0.07434849, -0.55918667, -0.80432653,  0.18665852]]))
      >>> qatt.vals.equatorial
      array([[193.28905806,  19.16894296,  67.36207683],
             [193.28905485,  19.1689407 ,  67.36208471],
             [193.28906329,  19.16893787,  67.36207699],
             [193.28908839,  19.16895134,  67.36206404]])

    This computed MSID can be used with the MAUDE data source. Be aware that if the
    telemetry has a missing VCDU then there is a risk of getting a slightly incorrect
    quaternion. This would occur since the code uses nearest-neighbor interpolation to
    associate the four components of the quaternion with a single time. For back-orbit
    data this is rare, but for real-time data it is more likely.
    """

    msid_match = r"quat_(aoattqt|aoatupq|aocmdqt|aotarqt)"

    def get_msid_attrs(self, tstart: float, tstop: float, msid: str, msid_args: tuple):
        from Quaternion import Quat, normalize

        msid_root = msid_args[0]
        n_comp = 4 if msid_root == "aoattqt" else 3
        msids = [f"{msid_root}{ii}" for ii in range(1, n_comp + 1)]

        # Get the raw MSIDs. Fetch a bit extra to avoid edge effects, in particular a
        # MAUDE query with a start time that lands between components of a quaternion.
        # E.g. aocmdqt* are spread over about 0.5 sec, but aoattqt seems to be within
        # the same minor frame.
        dat = self.fetch_sys.MSIDset(msids, tstart - 35, tstop + 35)

        # Interpolate to a common time base, leaving in flagged bad data and
        # marking data bad if any of the set at each time are bad. Note that this uses
        # nearest-neighbor interpolation. Empirically for these MSIDs that will work to
        # correctly bin the components together. See:
        # https://sot.github.io/eng_archive/fetch_tutorial.html#filtering-and-bad-values
        times = dat[msids[0]].times
        ok = (times >= tstart) & (times < tstop)
        dat.interpolate(times=times[ok], filter_bad=False, bad_union=True)

        q1 = dat[msids[0]].vals.astype(np.float64)
        q2 = dat[msids[1]].vals.astype(np.float64)
        q3 = dat[msids[2]].vals.astype(np.float64)
        if n_comp == 4:
            q4 = dat[msids[3]].vals.astype(np.float64)
        else:
            q4 = np.sqrt((1.0 - q1**2 - q2**2 - q3**2).clip(0.0))

        q = np.array([q1, q2, q3, q4]).transpose()
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="Normalizing quaternion with zero norm"
            )
            quat = Quat(q=normalize(q))
        bads = np.zeros_like(q1, dtype=bool)
        for msid_ in msids:
            bads |= dat[msid_].bads

        out = {"vals": quat, "bads": bads, "times": dat.times, "unit": None}
        return out


class Comp_MUPS_Valve_Temp_Clean(ComputedMsid):
    """Computed MSID for cleaned MUPS valve temps PM2THV1T, PM1THV2T

    This uses the cleaning method demonstrated in the following notebook
    to return a version of the MUPS valve temperature comprised of
    telemetry values that are consistent with a thermal model.

    https://nbviewer.jupyter.org/urls/cxc.cfa.harvard.edu/mta/ASPECT/ipynb/misc/mups-valve-xija-filtering.ipynb
    https://nbviewer.jupyter.org/urls/cxc.harvard.edu/mta/ASPECT/ipynb/misc/DAWG-mups-valve-xija-filtering.ipynb

    Allowed MSIDs are 'pm2thv1t_clean' and 'pm1thv2t_clean' (as always case is
    not important). Optionally one can include the ``chandra_models`` branch name,
    tag or commit hash to used for reading the MUPS 1B and MUPS 2A thermal model
    specifications. For example you can use 'pm1thv2t_clean_3.28' to get the model
    from release 3.28 of chandra_models.
    """

    msid_match = r"(pm2thv1t|pm1thv2t)_clean(_[\w\.]+)?"

    units = {
        "internal_system": "eng",  # Unit system for attrs from get_msid_attrs()
        "eng": "DEGF",  # Units for eng, sci, cxc systems
        "sci": "DEGC",
        "cxc": "K",
        # Attributes that need conversion
        "convert_attrs": ["vals", "vals_raw", "vals_nan", "vals_corr", "vals_model"],
    }

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        """Get attributes for computed MSID: ``vals``, ``bads``, ``times``, ``unit``

        :param tstart: start time (CXC secs)
        :param tstop: stop time (CXC secs)
        :param msid: full MSID name e.g. pm2thv1t_clean
        :param msid_args: tuple of regex match groups (msid_name,)

        :returns: dict of MSID attributes
        """
        from ..derived.mups_valve import fetch_clean_msid

        # Git version of chandra_models to use for MUPS model spec from 2nd match group.
        # If not supplied it will be None so use default main version.
        version = None if msid_args[1] is None else msid_args[1][1:]

        # Get cleaned MUPS valve temperature data as an MSID object
        dat = fetch_clean_msid(
            msid_args[0],
            tstart,
            tstop,
            dt_thresh=5.0,
            median=7,
            model_spec=None,
            version=version,
        )

        # Convert to dict as required by the get_msids_attrs API.  `fetch_clean_msid`
        # returns an MSID object with the following attrs.
        attrs = (
            "vals",
            "times",
            "bads",
            "vals_raw",
            "vals_nan",
            "vals_corr",
            "vals_model",
            "source",
        )
        msid_attrs = {attr: getattr(dat, attr) for attr in attrs}
        msid_attrs["unit"] = "DEGF"

        return msid_attrs


class Comp_KadiCommandState(ComputedMsid):
    """Computed MSID for kadi dynamic commanded states.

    The MSID here takes the form ``cmd_state_<state_key>_<dt>`` where:

    * ``state_key`` is a valid commanded state key such as ``pitch`` or
      ``pcad_mode`` or ``acisfp_temp``.
    * ``dt`` is the sampling time expressed as a multiple of 1.025 sec
      frames.

    Example MSID names::

      'cmd_state_pcad_mode_1': sample ``pcad_mode`` every 1.025 secs
      'cmd_state_acisfp_temp_32': sample ``acisfp_temp`` every 32.8 secs
    """

    msid_match = r"cmd_state_(\w+)_(\d+)"

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        """Get attributes for computed MSID: ``vals``, ``bads``, ``times``

        :param tstart: start time (CXC secs)
        :param tstop: stop time (CXC secs)
        :param msid: full MSID name e.g. cmd_state_pitch_clean
        :param msid_args: tuple of regex match groups: (state_key, dt)

        :returns: dict of MSID attributes
        """
        from Chandra.Time import date2secs
        from kadi.commands.states import get_states

        state_key = msid_args[0]
        dt = 1.025 * int(msid_args[1])
        states = get_states(tstart, tstop, state_keys=[state_key])

        tstart = date2secs(states["datestart"][0])
        tstops = date2secs(states["datestop"])

        times = np.arange(tstart, tstops[-1], dt)
        vals = states[state_key].view(np.ndarray)

        indexes = np.searchsorted(tstops, times)

        out = {
            "vals": vals[indexes],
            "times": times,
            "bads": np.zeros(len(times), dtype=bool),
            "unit": None,
        }

        return out


@functools.lru_cache(maxsize=1)
def get_roll_pitch_tlm_safe_table(start, stop):
    """Get telemetry values to compute pitch and roll in safe mode"""
    from cheta.utils import get_telem_table

    msids = ["6sares1", "6sares2", "6sunsa1", "6sunsa2", "6sunsa3"]
    dat = get_telem_table(msids, start, stop)

    # Filter out of range values. This happens just at the beginning of safe mode.
    bads = np.zeros(len(dat), dtype=bool)
    for msid in msids:
        x0, x1 = 0, 180 if ("6sares" in msid) else -1, 1
        bads |= (dat[msid].vals < x0) | (dat[msid].vals > x1)
    if np.any(bads):
        dat = dat[~bads]

    return dat


@functools.lru_cache(maxsize=1)
def get_roll_pitch_tlm_safe(start, stop):
    """Get telemetry values to compute pitch and roll in safe mode.

    This uses the OBC-computed sun position in the solar array frame from CSS data."""
    from cheta import fetch

    msids = ["6sares1", "6sares2", "6sunsa1", "6sunsa2", "6sunsa3"]
    dat = fetch.MSIDset(msids, start, stop)

    # Filter out of range values. This happens just at the beginning of safe mode.
    for msid in msids:
        if "6sares" in msid:
            x0, x1 = 0, 180
        else:
            x0, x1 = -1, 1
        dat[msid].bads |= (dat[msid].vals < x0) | (dat[msid].vals > x1)

    if any(len(dat[msid]) == 0 for msid in msids):
        dat.times = np.array([], dtype=float)
        for msid in msids:
            dat[msid].times = np.array([], dtype=float)
            dat[msid].vals = np.array([], dtype=float)
            dat[msid].bads = np.array([], dtype=bool)
    else:
        dat.interpolate(times=dat[msids[0]].times, bad_union=True)

    return dat


def calc_css_pitch_safe(start, stop):
    from ..derived.pcad import arccos_clip, calc_sun_vec_body_css

    # Get the raw telemetry value in user-requested unit system
    dat = get_roll_pitch_tlm_safe(start, stop)

    sun_vec_norm, bads = calc_sun_vec_body_css(dat, safe_mode=True)
    vals = np.degrees(arccos_clip(sun_vec_norm[0]))
    ok = ~bads
    vals = vals[ok]
    times = dat.times[ok]

    return times, vals


def calc_css_roll_safe(start, stop):
    """Off-Nominal Roll Angle from CSS Data in ACA Frame [Deg]

    Defined as the rotation about the ACA X-axis required to align the sun
    vector with the ACA X/Z plane.

    Calculated by rotating the CSS sun vector from the SA-1 frame to ACA frame
    based on the solar array angles 6SARES1 and 6SARES2.

    """
    from ..derived.pcad import calc_sun_vec_body_css

    # Get the raw telemetry value in user-requested unit system
    data = get_roll_pitch_tlm_safe(start, stop)

    sun_vec_norm, bads = calc_sun_vec_body_css(data, safe_mode=True)
    vals = np.degrees(np.arctan2(-sun_vec_norm[1, :], -sun_vec_norm[2, :]))
    ok = ~bads
    vals = vals[ok]
    times = data.times[ok]

    return times, vals


def calc_pitch_roll_obc(tstart: float, tstop: float, pitch_roll: str):
    """Use the code in the PCAD derived parameter classes to get the pitch and off
    nominal roll from OBC quaternion data.

    :param tstart: start time (CXC seconds)
    :param tstop: stop time (CXC seconds)
    :param pitch_roll: 'pitch' or 'roll'
    """
    from ..derived.pcad import DP_PITCH, DP_ROLL

    dp = DP_PITCH() if pitch_roll == "pitch" else DP_ROLL()
    # Pad by 12 minutes on each side to ensure ephemeris data are available.
    tlm = dp.fetch(tstart - 720, tstop + 720)

    # Filter bad data values. The `dp.fetch` above sets bad over intervals where any of
    # the inputs are missing and calling interpolate like below will cut those out.
    # See PR #250 for more details.
    tlm.interpolate(times=tlm.times)
    tlm.bads = np.zeros(len(tlm.times), dtype=bool)

    vals = dp.calc(tlm)
    i0, i1 = np.searchsorted(tlm.times, [tstart, tstop])
    return tlm.times[i0:i1], vals[i0:i1]


# Class name is arbitrary, but by convention start with `Comp_`
class Comp_Pitch_Roll_OBC_Safe(ComputedMsid):
    """
    Computed MSID to return pitch or off-nominal roll angle which is valid in NPNT,
    NMAN, NSUN, and Safe Mode.

    MSID names are ``pitch_comp`` and ``roll_comp``.

    The computation logic is shown below::

      On OBC control (CONLOFP == "NRML"):
        - AOPCADMD in ["NPNT", "NMAN"] => compute pitch/roll from AOATTQT[1234]
          (MAUDE or CXC) and predictive ephemeris ORBITEPHEM0_[XYZ] and
          SOLAREPHEM0_[XYZ] (CXC only but always available)
        - AOPCADMD == "NSUN" => get pitch/roll from PITCH/ROLL_CSS derived params.
          These are also in MAUDE.

      On CPE control (CONLOFP == "SAFE"):
        - Compute pitch/roll from 6SUNSA[123] + 6SARES[12] via calc_pitch/roll_css_safe()

      Intervals for other CONLOFP values are ignored.

    """

    msid_match = r"(roll|pitch)_comp"

    # `msid_match` is a class attribute that defines a regular expresion to
    # match for this computed MSID.  This must be defined and it must be
    # unambiguous (not matching an existing MSID or other computed MSID).
    #
    # The two groups in parentheses specify the arguments <MSID> and <offset>.
    # These are passed to `get_msid_attrs` as msid_args[0] and msid_args[1].
    # The \w symbol means to match a-z, A-Z, 0-9 and underscore (_).
    # The \d symbol means to match digits 0-9.

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        """
        Get attributes for computed MSID: ``vals``, ``bads``, ``times``,
        ``unit``, ``raw_vals``, and ``offset``.  The first four must always
        be provided.

        :param tstart: start time (CXC secs)
        :param tstop: stop time (CXC secs)
        :param msid: full MSID name e.g. tephin_plus_5
        :param msid_args: tuple of regex match groups (msid_name,)
        :returns: dict of MSID attributes
        """
        from cheta.utils import get_ofp_states

        from .. import fetch
        from ..utils import logical_intervals

        start = CxoTime(tstart)
        stop = CxoTime(tstop)

        # Whether we are computing "pitch" or "roll", parsed from MSID name
        pitch_roll: str = msid_args[0]

        ofp_states = get_ofp_states(start, stop)

        tlms = []
        for ofp_state in ofp_states:
            if ofp_state["val"] == "NRML":
                dat = fetch.Msid("aopcadmd", ofp_state["tstart"], ofp_state["tstop"])
                if len(dat) == 0:
                    # For an interval with no samples put in empty arrays so that
                    # subsequent processing succeeds.
                    tlms.append((np.array([], dtype=float), np.array([], dtype=float)))
                    continue

                # Get states of either NPNT / NMAN or NSUN which cover exactly the
                # time span of the ofp_state interval.
                vals = np.isin(dat.vals, ["NPNT", "NMAN"])
                states_npnt_nman = logical_intervals(
                    dat.times,
                    vals,
                    complete_intervals=False,
                    max_gap=2.1,
                    start=ofp_state["tstart"],
                    stop=ofp_state["tstop"],
                )
                states_npnt_nman["val"] = np.repeat("NPNT_NMAN", len(states_npnt_nman))

                states_nsun = logical_intervals(
                    dat.times,
                    dat.vals == "NSUN",
                    max_gap=2.1,
                    complete_intervals=False,
                    start=ofp_state["tstart"],
                    stop=ofp_state["tstop"],
                )
                states_nsun["val"] = np.repeat("NSUN", len(states_nsun))
                states = tbl.vstack([states_npnt_nman, states_nsun])
                states.sort("tstart")

                for state in states:
                    if state["val"] == "NPNT_NMAN":
                        times, vals = calc_pitch_roll_obc(
                            state["tstart"], state["tstop"], pitch_roll
                        )
                        tlms.append((times, vals))
                    elif state["val"] == "NSUN":
                        tlm = fetch.Msid(
                            f"{pitch_roll}_css", state["tstart"], state["tstop"]
                        )
                        tlms.append((tlm.times, tlm.vals))

            elif ofp_state["val"] == "SAFE":
                calc_func = globals()[f"calc_css_{pitch_roll}_safe"]
                tlm = calc_func(ofp_state["datestart"], ofp_state["datestop"])
                tlms.append(tlm)

        times = np.concatenate([tlm[0] for tlm in tlms])
        vals = np.concatenate([tlm[1] for tlm in tlms])

        # Return a dict with at least `vals`, `times`, `bads`, and `unit`.
        # Additional attributes are allowed and will be set on the
        # final MSID object.
        out = {
            "vals": vals,
            "bads": np.zeros(len(vals), dtype=bool),
            "times": times,
            "unit": "DEG",
        }
        return out
