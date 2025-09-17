# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
STK orbit ephemeris computed MSIDs
"""

import calendar
import functools
import logging
import os
import re
from pathlib import Path

import numpy as np
from astropy.table import Column, Table
from cxotime import CxoTime, CxoTimeLike
from kadi import occweb
from ska_helpers.retry import retry_call

from .computed_msid import ComputedMsid

logger = logging.getLogger("cheta.fetch")


EPHEM_STK_RECENT_DIR = "FOT/mission_planning/Backstop/Ephemeris"
EPHEM_STK_ARCHIVE_DIR = "FOT/mission_planning/Backstop/Ephemeris/ArchiveMCC"
EPHEM_STK_CACHE_DIR_DEFAULT = Path.home() / ".cheta" / "cache"
EPHEM_STK_DIRS_DEFAULT = [
    Path.home() / "Documents" / "MATLAB" / "FOT_Tools" / "Ephemeris",  # Windows
    Path("/home/mission/Backstop/Ephemeris"),  # Greta/linux
]

MONTH_NAME_TO_NUM = {
    mon: f"{ii + 1:02d}" for ii, mon in enumerate(calendar.month_abbr[1:])
}


def parse_stk_file_text(text: str, format_out="stk"):
    """Parse STK ephemeris file text and return an astropy table.

    Parse text that looks like below::

                                                                                                          6 Aug 2025 03:30:16
      Satellite-Chandra:  J2000 Position & Velocity


          Time (UTCG)              x (km)           y (km)            z (km)       vx (km/sec)    vy (km/sec)    vz (km/sec)
      -----------------------    -------------    --------------    -------------    -----------    -----------    -----------
      6 Jul 2025 12:00:00.00     34557.394268     -88565.935003     32903.996133       0.199880       1.283853      -1.141781
      6 Jul 2025 12:05:00.00     34616.746289     -88179.214343     32560.881289       0.195790       1.294299      -1.145653
      6 Jul 2025 12:10:00.00     34674.862330     -87789.346381     32216.603475       0.191640       1.304835      -1.149534


    The ``format_out`` argument specifies the output format of the returned Table, in
    particular the column names and units. For format "stk" the table is the same as the
    file with columns:

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
    text: str
        Text of the STK ephemeris data
    format_out : str
        Format of the returned ephemeris Table ("stk" or "cxc")

    Returns
    -------
    astropy.table.Table :
        Table of ephemeris data.
    """  # noqa: E501
    # Find the position of the header line that starts with "Time (UTCG)", discarding
    # blank lines since astropy io.ascii does not count them.
    header_start = 0
    for match in re.finditer(".*", text):
        line = match.group(0).strip()
        if line.startswith("Time (UTCG)"):
            break
        if line:
            header_start += 1
    else:
        raise Exception("did not find header line starting with 'Time (UTCG)'")

    dat = Table.read(
        text,
        format="ascii.fixed_width_two_line",
        header_start=header_start,
        position_line=header_start + 1,
    )
    if format_out == "stk":
        return dat
    elif format_out != "cxc":
        raise ValueError(f"Unknown format {format_out!r} (allowed: 'stk', 'cxc')")

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
        "vz": Column(dat["vz (km/sec)"] * 1000, unit="m/s"),
    }
    return Table(out)


def read_stk_file_from_occweb(path: str | Path, format_out="stk", **kwargs) -> Table:
    """Read a STK ephemeris file from OCCweb and return an astropy table.

    For format "stk" the returned table is the same as the file with columns:

           name     dtype
      ----------- -------
      Time (UTCG)   str23
           x (km) float64
           y (km) float64
           z (km) float64
      vx (km/sec) float64
      vy (km/sec) float64
      vz (km/sec) float64

    For format "cxc" the returned table has the same columns as ephemeris files in the
    CXC archive::

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
    format_out : str
        Output format for the returned table ("stk" or "cxc")
    **kwargs :
        Additional args passed to get_occweb_page()

    Returns
    -------
    astropy.table.Table :
        Table of ephemeris data.
    """
    logger.info(f"Reading OCCweb STK file {path}")
    text = retry_call(
        occweb.get_occweb_page,
        args=[path],
        kwargs={"timeout": 5} | kwargs,
        tries=3,
        backoff=2,
        logger=logger,
    )
    out = parse_stk_file_text(text, format_out=format_out)
    return out


def read_stk_file(path: str | Path) -> np.ndarray:
    """Read a STK ephemeris file from OCCweb or local and return a numpy array.

    This uses a local cache dir which has numpy savez files of the raw numpy arrays
    for each named ephemeris file. Otherwise it reads the file from local directories
    """
    path = Path(path)
    cache_dir = Path(
        os.environ.get("CHETA_EPHEM_STK_CACHE_DIR", EPHEM_STK_CACHE_DIR_DEFAULT)
    )
    cache_file = cache_dir / f"{path.name}.npz"
    if cache_file.exists():
        logger.info(f"Reading cached STK file {path} from {cache_file}")
        out = np.load(cache_file)["arr_0"]
        return out

    # Determine if path is local or occweb
    if path.exists():
        logger.info(f"Reading local STK file {path}")
        text = path.read_text()
        table = parse_stk_file_text(text, format_out="cxc")
    else:
        logger.info(f"Reading OCCweb STK file {path}")
        table = read_stk_file_from_occweb(path, format_out="cxc")

    out = table.as_array()
    logger.info(f"Caching STK file {path} to {cache_file}")
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache_file, out)

    return out


def find_stk_files(file_names, dir_path, source, start, stop):
    found_files = []
    for name in file_names:
        match = re.match(r"Chandra_(\d{2})(\d{3})_(\d{2})(\d{3}).stk$", name)
        if match:
            yr1, doy1, yr2, doy2 = (int(val) for val in match.groups())
            yr1 += 1900 if yr1 >= 98 else 2000
            yr2 += 1900 if yr2 >= 98 else 2000
            start_stk = CxoTime(f"{yr1}:{doy1}:12:00:00.000")
            stop_stk = CxoTime(f"{yr2}:{doy2}:11:59:59.999")
            if not (start_stk > stop or stop_stk < start):
                found_files.append(
                    {
                        "path": f"{dir_path}/{name}"
                        if source == "occweb"
                        else str(Path(dir_path) / name),
                        "start": start_stk,
                        "stop": stop_stk,
                        "source": source,
                    }
                )
    return found_files


def get_ephem_stk_paths(
    start: CxoTimeLike,
    stop: CxoTimeLike = None,
    latest_only=True,
):
    """Get STK orbit ephemeris file paths from OCCweb or local directories.

    Finds STK ephemeris files that overlap the interval from start to stop.

    Returns a list of dict for each STK file, with keys:
        - 'path': full path to the STK file (local or OCCweb)
        - 'start': <CxoTime> start time of file
        - 'stop': <CxoTime> stop time of file
        - 'source': "local" or "occweb"

    Parameters
    ----------
    start : CxoTimeLike
        Start time of interval
    stop : CxoTimeLike
        Stop time of interval (default=NOW)
    latest_only : bool
        If True (default), return only the latest files that overlap the interval. If
        False, return all files that overlap the interval.

    Returns
    -------
    files_stk : list of dict
        List of dict with keys path, start, stop, source
    """
    start = CxoTime(start)
    stop = CxoTime(stop)

    files_stk = []

    # Find the local path on Windows or GRETA Linux. CHETA_EPHEM_STK_DIRS can be a ";"
    # separated string of paths. Any whitespace-only paths are dropped so setting this
    # var to "" results in stk_dirs = [] and falling through to reading from OCCweb.
    stk_dirs: list[Path] = (
        [Path(ss) for s in stk_dirs_str.split(";") if (ss := s.strip())]
        if (stk_dirs_str := os.environ.get("CHETA_EPHEM_STK_DIRS")) is not None
        else EPHEM_STK_DIRS_DEFAULT
    )

    # First try local STK directories (if they exist)
    for stk_dir in stk_dirs:
        if not stk_dir.exists():
            continue
        local_names = [p.name for p in stk_dir.iterdir()]
        logger.info(f"Checking local directory {stk_dir} for STK files")
        files_stk.extend(find_stk_files(local_names, stk_dir, "local", start, stop))
        if latest_only and any(f["start"] <= start for f in files_stk):
            files_stk = sorted(files_stk, key=lambda x: x["start"].date)
            for ii, file_stk in enumerate(reversed(files_stk)):
                if file_stk["start"] <= start:
                    files_stk = files_stk[-ii - 1 :]
                    break
            return files_stk

    # Then try OCCweb
    for dir_path in [EPHEM_STK_RECENT_DIR, EPHEM_STK_ARCHIVE_DIR]:
        logger.info(f"Checking OCCweb directory {dir_path}")
        files = occweb.get_occweb_dir(dir_path)
        files_stk.extend(find_stk_files(files["Name"], dir_path, "occweb", start, stop))
        if latest_only and any(f["start"] <= start for f in files_stk):
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
    """Get ephemeris data from local STK files, OCCweb, or local cache STK data.

    By default, looks for local STK files in the directory specified by the
    CHETA_EPHEM_STK_DIR environment variable (if not set, uses default of
    platform-dependent standard location). If no local files are found, then
    the search for data looks on OCCweb.

    Returns a structured array with columns time, x, y, z, vx, vy, vz. The time is in
    CXC seconds since 1998.0, and the position and velocity are in meters and
    meters/second, respectively.

    The last result of this function is cached in memory for performance. The memory
    cache is for the common use case of fetching (via fetch.Msid) multiple
    components of the ephemeris over the same time range.

    In addition, STK files are cached on disk as compressed numpy arrays in the
    directory specified by the CHETA_EPHEM_STK_CACHE_DIR environment variable
    (if not set uses default ~/.cheta/cache). This reduces repeated downloads and
    speeds up access to ephemeris data.

    This function also respects the CHETA_EPHEM_DISABLE_LOCAL_STK environment
    variable for testing. If set to "True", then local STK files are not used
    even if available (though note that the lru_cache does not know about environment
    variables, so if the function is called with the same start and stop times as a
    previous call, the cached result will be returned even if the environment variable
    has changed).

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

    stk_paths = get_ephem_stk_paths(start, stop)
    dats = [read_stk_file(stk_path["path"]) for stk_path in stk_paths]

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

    Under the hood this uses get_ephemeris_stk() to fetch the ephemeris data from
    local STK files, OCCweb, or local cache STK data.

    Example::

      >>> from cheta import fetch
      >>> orbit_x = fetch.Msid('orbitephem_stk_x', '2022:001', '2023:001')
      >>> orbit_x.plot()
      # Makes a plot

    """

    msid_match = r"orbitephem_stk_(x|y|z|vx|vy|vz)"

    def get_msid_attrs(self, tstart: float, tstop: float, msid: str, msid_args: tuple):
        units = {
            "x": "m",
            "y": "m",
            "z": "m",
            "vx": "m/s",
            "vy": "m/s",
            "vz": "m/s",
        }
        # Component of the STK ephemeris to fetch (x, y, z, vx, vy, vz)
        comp = msid_args[0]
        dat = get_ephemeris_stk(tstart, tstop)
        bads = np.zeros(dat[comp].shape, dtype=bool)
        out = {
            "vals": dat[comp],
            "bads": bads,
            "times": dat["time"],
            "unit": units[comp],
        }

        return out
