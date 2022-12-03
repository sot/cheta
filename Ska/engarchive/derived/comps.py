# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Support computed MSIDs in the cheta archive.

- Base class ComputedMsid for user-generated comps.
- Cleaned MUPS valve temperatures MSIDs: '(pm2thv1t|pm1thv2t)_clean'.
- Commanded states 'cmd_state_<key>_<dt>' for any kadi commanded state value.

See: https://nbviewer.jupyter.org/urls/cxc.harvard.edu/mta/ASPECT/ipynb/misc/DAWG-mups-valve-xija-filtering.ipynb
"""  # noqa

import re

import numpy as np
from Chandra.Time import DateTime

from ..units import converters as unit_converter_funcs

__all__ = ["ComputedMsid", "Comp_MUPS_Valve_Temp_Clean", "Comp_KadiCommandState"]


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

    :returns: np.recarray of stats values
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
    if msid_dtype.kind == "U":
        msid_dtype = re.sub(r"U", "S", msid.vals.dtype.str)

    # Predeclare numpy arrays of correct type and sufficient size for accumulating results.
    out = {}
    out["index"] = np.ndarray((n_out,), dtype=np.int32)
    out["n"] = np.ndarray((n_out,), dtype=np.int32)
    out["val"] = np.ndarray((n_out,), dtype=msid_dtype)

    if msid_is_numeric:
        out["min"] = np.ndarray((n_out,), dtype=msid_dtype)
        out["max"] = np.ndarray((n_out,), dtype=msid_dtype)
        out["mean"] = np.ndarray((n_out,), dtype=np.float32)

        if interval == "daily":
            out["std"] = np.ndarray((n_out,), dtype=msid_dtype)
            for quantile in quantiles:
                out["p{:02d}".format(quantile)] = np.ndarray((n_out,), dtype=msid_dtype)

    i = 0
    for row0, row1, index in zip(rows[:-1], rows[1:], indexes[:-1]):
        vals = msid.vals[row0:row1]
        times = msid.times[row0:row1]

        n_vals = len(vals)
        if n_vals > 0:
            out["index"][i] = index
            out["n"][i] = n_vals
            out["val"][i] = vals[n_vals // 2]
            if msid_is_numeric:
                if n_vals <= 2:
                    dts = np.ones(n_vals, dtype=np.float64)
                else:
                    dts = np.empty(n_vals, dtype=np.float64)
                    dts[0] = times[1] - times[0]
                    dts[-1] = times[-1] - times[-2]
                    dts[1:-1] = (
                        (times[1:-1] - times[:-2]) + (times[2:] - times[1:-1])
                    ) / 2.0
                    negs = dts < 0.0
                    if np.any(negs):
                        times_dts = [
                            (DateTime(t).date, dt)
                            for t, dt in zip(times[negs], dts[negs])
                        ]
                        raise ValueError(
                            "WARNING - negative dts in {} at {}".format(
                                msid.MSID, times_dts
                            )
                        )

                    # Clip to range 0.001 to 300.0.  The low bound is just there
                    # for data with identical time stamps.  This shouldn't happen
                    # but in practice might.  The 300.0 represents 5 minutes and
                    # is the largest normal time interval.  Data near large gaps
                    # will get a weight of 5 mins.
                    dts.clip(0.001, 300.0, out=dts)
                sum_dts = np.sum(dts)

                out["min"][i] = np.min(vals)
                out["max"][i] = np.max(vals)
                out["mean"][i] = np.sum(dts * vals) / sum_dts
                if interval == "daily":
                    # biased weighted estimator of variance (N should be big enough)
                    # http://en.wikipedia.org/wiki/Mean_square_weighted_deviation
                    sigma_sq = np.sum(dts * (vals - out["mean"][i]) ** 2) / sum_dts
                    out["std"][i] = np.sqrt(sigma_sq)
                    quant_vals = scipy.stats.mstats.mquantiles(
                        vals, np.array(quantiles) / 100.0
                    )
                    for quant_val, quantile in zip(quant_vals, quantiles):
                        out["p%02d" % quantile][i] = quant_val

            i += 1

    return np.rec.fromarrays([x[:i] for x in out.values()], names=list(out.keys()))


class ComputedMsid:
    """Base class for cheta computed MSID.

    Sub-classes must define at least the following:

    * ``msid_match`` class attribute as a regex to match for the MSID.
    * ``get_msid_attrs()`` method to perform the computation and return
      a dict with the result.

    Optionally:

    * ``units`` attribute to specify unit handling.

    See the fetch tutorial Computed MSIDs section for details.
    """

    # Global dict of registered computed MSIDs
    msid_classes = []

    # Base units specification (None implies no unit handling)
    units = None

    def __init__(self, unit_system="eng"):
        self.unit_system = unit_system

    def __init_subclass__(cls, **kwargs):
        """Validate and register ComputedMSID subclass."""
        super().__init_subclass__(**kwargs)

        if not hasattr(cls, "msid_match"):
            raise ValueError(f"comp {cls.__name__} must define msid_match")

        cls.msid_classes.append(cls)

    @classmethod
    def get_matching_comp_cls(cls, msid):
        """Get computed classes that match ``msid``

        :param msid: str, input msid
        :returns: first ComputedMsid subclass that matches ``msid`` or None
        """
        for comp_cls in ComputedMsid.msid_classes:
            match = re.match(comp_cls.msid_match + "$", msid, re.IGNORECASE)
            if match:
                return comp_cls

        return None

    # These four properties are provided as a convenience because the module
    # itself cannot import fetch because this is circular.
    @property
    def fetch_eng(self):
        """Fetch in TDB engineering units like DEGF"""
        from .. import fetch_eng

        return fetch_eng

    @property
    def fetch_sci(self):
        """Fetch in scientific units like DEGC"""
        from .. import fetch_sci

        return fetch_sci

    @property
    def fetch_cxc(self):
        """Fetch in CXC (FITS standard) units like K"""
        from .. import fetch

        return fetch

    @property
    def fetch_sys(self):
        """Fetch in the unit system specified for the class"""
        fetch = getattr(self, f"fetch_{self.unit_system}")
        return fetch

    def __call__(self, tstart, tstop, msid, interval=None):
        """Emulate the fetch.MSID() API, but return a dict of MSID attributes.

        The returned dict turned into a proper MSID object by the upstream caller
        `fetch.MSID._get_comp_data()`.

        :param tstart: float, start time (CXC seconds)
        :param tstop: float, stop time (CXC seconds)
        :param msid: str, MSID name
        :param interval: str or None, stats interval (None, '5min', 'daily')

        :returns: dict of MSID attributes including 'times', 'vals', 'bads'
        """
        # Parse any arguments from the input `msid`
        match = re.match(self.msid_match, msid, re.IGNORECASE)
        if not match:
            raise RuntimeError(f"unexpected mismatch of {msid} with {self.msid_match}")
        match_args = [
            arg.lower() if isinstance(arg, str) else arg for arg in match.groups()
        ]

        if interval is None:
            # Call the actual user-supplied work method to compute the MSID values
            msid_attrs = self.get_msid_attrs(tstart, tstop, msid.lower(), match_args)

            for attr in ("vals", "bads", "times", "unit"):
                if attr not in msid_attrs:
                    raise ValueError(
                        f"computed MSID {self.__class__.__name__} failed "
                        f"to set required attribute {attr}"
                    )

            # Presence of a non-None `units` class attribute means that the MSID has
            # units that should be converted to `self.unit_system` if required, where
            # unit_system is 'cxc', 'sci', or 'eng'.
            if self.units is not None:
                msid_attrs = self.convert_units(msid_attrs)
        else:
            msid_attrs = self.get_stats_attrs(
                tstart, tstop, msid.lower(), match_args, interval
            )

        return msid_attrs

    def convert_units(self, msid_attrs):
        """
        Convert required elements of ``msid_attrs`` to ``self.unit_system``.

        Unit_system can be one of 'cxc', 'sci', 'eng'.

        :param msid_attrs: dict, input MSID attributes
        :param unit_system: str, unit system

        :returns: dict, converted MSID attributes
        """
        unit_current = self.units[self.units["internal_system"]]
        unit_new = self.units[self.unit_system]

        out = msid_attrs.copy()
        out["unit"] = unit_new

        if unit_current != unit_new:
            for attr in self.units["convert_attrs"]:
                out[attr] = unit_converter_funcs[unit_current, unit_new](
                    msid_attrs[attr]
                )

        return out

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        """Get the attributes required for this MSID.

        Get attributes for computed MSID, which must include at least
        ``vals``, ``bads``, ``times``, and may include additional attributes.

        This MUST be supplied by sub-classes.

        :param tstart: start time (CXC secs)
        :param tstop: stop time (CXC secs)
        :param msid: full MSID name e.g. tephin_plus_5
        :param msid_args: tuple of regex match groups (msid_name,)
        :returns: dict of MSID attributes
        """
        raise NotImplementedError("sub-class must implement get_msid_attrs()")

    def get_stats_attrs(self, tstart, tstop, msid, match_args, interval):
        """Get 5-min or daily stats attributes.

        This is normally not overridden by sub-classes.

        :param tstart: start time (CXC secs)
        :param tstop: stop time (CXC secs)
        :param msid: full MSID name e.g. tephin_plus_5
        :param msid_args: tuple of regex match groups (msid_name,)
        :returns: dict of MSID attributes
        """
        from ..fetch import _plural

        # Replicate a stripped-down version of processing in update_archive.
        # This produces a recarray with columns that correspond to the raw
        # stats HDF5 files.
        dt = {"5min": 328, "daily": 86400}[interval]
        index0 = int(np.floor(tstart / dt))
        index1 = int(np.ceil(tstop / dt))
        tstart = (index0 - 1) * dt
        tstop = (index1 + 1) * dt

        msid_obj = self.fetch_sys.Msid(msid, tstart, tstop)

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
            out_key = _plural(key) if key != "n" else "samples"
            out[out_key] = vals_stats[key]
        out["times"] = (vals_stats["index"] + 0.5) * dt
        out["bads"] = np.zeros(len(vals_stats), dtype=bool)
        out["midvals"] = out["vals"]
        out["vals"] = out["means"]
        out["unit"] = msid_obj.unit

        return out


############################################################################
#  Built-in computed MSIDs
############################################################################


class Comp_Quat(ComputedMsid):
    """Computed MSID for returning the quaternion telemetry as a Quat object

    This defines the following computed MSIDs based on the corresponding
    TDB MSIDs:

    - quat_aoattqt = AOATTQT[1-4]
    - quat_aoatupq = AOATUPQ[1-3]
    - quat_aocmdqt = AOCMDQT[1-3]
    - quat_aotarqt = AOTARQT[1-3]

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
    """

    msid_match = r"quat_(aoattqt|aoatupq|aocmdqt|aotarqt)"

    def get_msid_attrs(self, tstart, tstop, msid, msid_args):
        from Quaternion import Quat, normalize

        if "maude" in self.fetch_sys.data_source.sources():
            raise ValueError(
                f"{msid} is not available from MAUDE due to issues aligning telemetry"
            )

        msid_root = msid_args[0]
        n_comp = 4 if msid_root == "aoattqt" else 3
        msids = [f"{msid_root}{ii}" for ii in range(1, n_comp + 1)]
        dat = self.fetch_sys.MSIDset(msids, tstart, tstop)

        # Interpolate to a common time base, leaving in flagged bad data and
        # marking data bad if any of the set at each time are bad. See:
        # https://sot.github.io/eng_archive/fetch_tutorial.html#filtering-and-bad-values
        dat.interpolate(times=dat[msids[0]].times, filter_bad=False, bad_union=True)

        q1 = dat[msids[0]].vals.astype(np.float64)
        q2 = dat[msids[1]].vals.astype(np.float64)
        q3 = dat[msids[2]].vals.astype(np.float64)
        if n_comp == 4:
            q4 = dat[msids[3]].vals.astype(np.float64)
        else:
            q4 = np.sqrt((1.0 - q1**2 - q2**2 - q3**2).clip(0.0))

        q = np.array([q1, q2, q3, q4]).transpose()
        quat = Quat(q=normalize(q))
        bads = np.zeros_like(q1, dtype=bool)
        for msid in msids:
            bads |= dat[msid].bads

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
        from .mups_valve import fetch_clean_msid

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
