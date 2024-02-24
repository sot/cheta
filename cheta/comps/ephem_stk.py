# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
STK orbit ephemeris computed MSIDs
"""

import calendar
import functools
import logging
import re
from pathlib import Path

import numpy as np
from astropy.table import Column, Table
from cxotime import CxoTime, CxoTimeLike
from kadi import occweb

from .computed_msid import ComputedMsid

logger = logging.getLogger("cheta.fetch")


EPHEM_STK_RECENT_DIR = "FOT/mission_planning/Backstop/Ephemeris"
EPHEM_STK_ARCHIVE_DIR = "FOT/mission_planning/Backstop/Ephemeris/ArchiveMCC"

MONTH_NAME_TO_NUM = {
    mon: f"{ii + 1:02d}" for ii, mon in enumerate(calendar.month_abbr[1:])
}


def read_stk_file(path, format="stk", **kwargs):
    """Read a STK ephemeris file from OCCweb and return an astropy table.

    For format "stk" the table is the same as the file with columns:

           name     dtype
      ----------- -------
      Time (UTCG)   str23
           x (km) float64
           y (km) float64
           z (km) float64
      vx (km/sec) float64
      vy (km/sec) float64
      vz (km/sec) float64

    For format "cxc" the table has the same columns as ephemeris files in the CXC
    archive::

      name  dtype   unit
      ---- ------- -----
      time float64
         x float64     m
         y float64     m
         z float64     m
        vx float64 m / s
        vy float64 m / s
        vz float64 m / s

    Parameters
    ----------
    path : str
        Path on OCCweb of the STK ephemeris file, for example
        "FOT/mission_planning/Backstop/Ephemeris/Chandra_23177_24026.stk"
    format : str
        Format of the file ("stk" or "cxc")
    **kwargs :
        Additional args passed to get_occweb_page()

    Returns
    -------
    astropy.table.Table :
        Table of ephemeris data.
    """
    logger.info(f"Reading OCCweb STK file {path}")
    text = occweb.get_occweb_page(path, **kwargs)
    dat = Table.read(
        text, format="ascii.fixed_width_two_line", header_start=2, position_line=3
    )
    if format == "stk":
        return dat
    elif format != "cxc":
        raise ValueError(f"Unknown format {format!r} (allowed: 'stk', 'cxc')")

    isos = []
    for date in dat["Time (UTCG)"]:
        vals = date.split()
        month = MONTH_NAME_TO_NUM[vals[1]]
        day = vals[0]
        year = vals[2]
        time = vals[3]
        iso = f"{year}-{month}-{day}T{time}"
        isos.append(iso)
    out = {
        # Round time to nearest millisecond for later float comparison
        "time": np.round(CxoTime(isos, format="isot").secs, 3),
        "x": Column(dat["x (km)"] * 1000, unit="m"),
        "y": Column(dat["y (km)"] * 1000, unit="m"),
        "z": Column(dat["z (km)"] * 1000, unit="m"),
        "vx": Column(dat["vx (km/sec)"] * 1000, unit="m/s"),
        "vy": Column(dat["vy (km/sec)"] * 1000, unit="m/s"),
        "zz": Column(dat["vz (km/sec)"] * 1000, unit="m/s"),
    }
    return Table(out)


def _read_stk_file_cxc_cached(path_occweb: str) -> np.ndarray:
    """Read a STK ephemeris file from OCCweb and return an astropy table."""
    name = Path(path_occweb).name
    cache_file = Path.home() / ".cheta" / "cache" / f"{name}.npz"
    if cache_file.exists():
        logger.info(f"Reading cached STK file {path_occweb} from {cache_file}")
        out = np.load(cache_file)["arr_0"]
    else:
        out = read_stk_file(path_occweb, format="cxc").as_array()
        logger.info(f"Caching STK file {path_occweb} to {cache_file}")
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cache_file, out)
    return out


def get_ephem_stk_occweb_paths(
    start: CxoTimeLike,
    stop: CxoTimeLike = None,
    latest_only=True,
):
    """Get STK orbit ephemeris file paths from OCCweb.

    This finds the STK ephemeris files on OCCweb that overlap the interval from start to
    stop.

    Returns a list of dict like below for each STK file::

        {
            'path': 'FOT/mission_planning/Backstop/Ephemeris/Chandra_23107_23321.stk',
            'start': <CxoTime '2023:107:00:00:00.000'>, 'stop': <CxoTime
            '2023:321:59:59.999'>,
        }

    Parameters
    ----------
    start : CxoTimeLike
        Start time of interval
    stop : CxoTimeLike
        Stop time of interval (default=NOW)
    latest_only : bool
        If True (default), return only the latest files that overlaps the interval. If
        False, return all files that overlap the interval.

    Returns
    -------
    files_stk : list of dict
        List of dict with keys path, start, stop
    """
    start = CxoTime(start)
    stop = CxoTime(stop)

    files_stk = []

    for dir_path in [EPHEM_STK_RECENT_DIR, EPHEM_STK_ARCHIVE_DIR]:
        logger.info(f"Checking OCCweb directory {dir_path}")
        files = occweb.get_occweb_dir(dir_path)
        for name in files["Name"]:
            # Match file names like: Chandra_01190_01250.stk. Parse this as a regex
            # with 01 as year1, 190 as doy1, 01 as year2, 250 as doy2.
            if match := re.match(r"Chandra_(\d{2})(\d{3})_(\d{2})(\d{3}).stk$", name):
                yr1, doy1, yr2, doy2 = (int(val) for val in match.groups())
                yr1 += 1900 if yr1 >= 98 else 2000
                yr2 += 1900 if yr2 >= 98 else 2000

                start_stk = CxoTime(f"{yr1}:{doy1}:00:00:00.000")
                stop_stk = CxoTime(f"{yr2}:{doy2}:23:59:59.999")

                # Intervals overlap?
                if not (start_stk > stop or stop_stk < start):
                    file_stk = {
                        "path": f"{dir_path}/{name}",
                        "start": start_stk,
                        "stop": stop_stk,
                    }
                    files_stk.append(file_stk)

        # If latest_only then we can skip EPHEM_STK_ARCHIVE_DIR if we found any files
        # that start before the start time.
        if latest_only and any(file_stk["start"] <= start for file_stk in files_stk):
            break

    files_stk = sorted(files_stk, key=lambda x: x["start"].date)

    if latest_only:
        for ii, file_stk in enumerate(reversed(files_stk)):
            if file_stk["start"] <= start:
                files_stk = files_stk[-ii - 1 :]
                break

    return files_stk


# Cache the last call for the common case of fetching all 6 components of the ephemeris
# over the same time range.
@functools.lru_cache(maxsize=1)
def get_ephemeris_stk(start: CxoTimeLike, stop: CxoTimeLike) -> np.ndarray:
    """Get ephemeris data from OCCweb or local cache STK files.

    Returns a structured array with columns time, x, y, z, vx, vy, vz. The time is in
    CXC seconds since 1998.0, and the position and velocity are in meters and
    meters/second, respectively.

    The last result of this function is cached in memory. This is for the common use
    case of fetching (via fetch.Msid) multiple components of the ephemeris over the same
    time range.

    Parameters
    ----------
    start : CxoTimeLike
        Start time of interval
    stop : CxoTimeLike
        Stop time of interval

    Returns
    -------
    dat : np.ndarray
        Structured array with columns time, x, y, z, vx, vy, vz
    """
    start = CxoTime(start)
    stop = CxoTime(stop)

    stk_paths = get_ephem_stk_occweb_paths(start, stop)
    dats = [_read_stk_file_cxc_cached(stk_path["path"]) for stk_path in stk_paths]

    # The ephemeris all overlap with the next one, so we can clip them to the interval.
    dats_clip = []
    for dat0, dat1 in zip(dats[:-1], dats[1:]):
        # This is equivalent to dat0[dat0["Time"] < dat1["Time"][0]] but faster.
        # See: https://occweb.cfa.harvard.edu/twiki/Aspect/SkaPython
        idx1 = np.searchsorted(dat0["time"], dat1["time"][0], side="left")
        dats_clip.append(dat0[:idx1])
    dats_clip.append(dats[-1])

    dat = np.concatenate(dats_clip)

    idx0 = np.searchsorted(dat["time"], start.secs, side="left")
    idx1 = np.searchsorted(dat["time"], stop.secs, side="left")

    return dat[idx0:idx1]


class Comp_EphemSTK(ComputedMsid):
    """Computed MSID for returning the STK orbit ephemeris.

    This defines the following computed MSIDs:

    - ``orbitephem_stk_x``: STK orbit ephemeris X position (m)
    - ``orbitephem_stk_y``: STK orbit ephemeris Y position (m)
    - ``orbitephem_stk_z``: STK orbit ephemeris Z position (m)
    - ``orbitephem_stk_vx``: STK orbit ephemeris X velocity (m/s)
    - ``orbitephem_stk_vy``: STK orbit ephemeris Y velocity (m/s)
    - ``orbitephem_stk_vz``: STK orbit ephemeris Z velocity (m/s)

    Example::

      >>> from cheta import fetch
      >>> orbit_x = fetch.Msid('orbitephem_stk_x', '2022:001', '2023:001')
      >>> orbit_x.plot()
      # Makes a plot

    """

    msid_match = r"orbitephem_stk_(x|y|z|vx|vy|vz)"

    def get_msid_attrs(self, tstart: float, tstop: float, msid: str, msid_args: tuple):
        # Component of the STK ephemeris to fetch (x, y, z, vx, vy, vz)
        comp = msid_args[0]
        dat = get_ephemeris_stk(tstart, tstop)
        bads = np.zeros(dat[comp].shape, dtype=bool)
        out = {"vals": dat[comp], "bads": bads, "times": dat["time"], "unit": None}

        return out
