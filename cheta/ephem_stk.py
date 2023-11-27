# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Support ingest of STK orbit ephemeris files.
"""

import calendar
import re

from astropy.table import Column, Table
from cxotime import CxoTime, CxoTimeLike
from kadi import occweb

EPHEM_STK_RECENT_DIR = "FOT/mission_planning/Backstop/Ephemeris"
EPHEM_STK_ARCHIVE_DIR = "FOT/mission_planning/Backstop/Ephemeris/ArchiveMCC"

MONTH_NAME_TO_NUM = {
    mon: f"{ii + 1:02d}" for ii, mon in enumerate(calendar.month_abbr[1:])
}

# For reference, here is the schema of the archfiles table in the content directory
# for orbitephem0. Note that startmjf .. ascdsver are not used and are NULL.
"""
sqlite> .schema archfiles
CREATE TABLE archfiles (
  filename        text not null,
  filetime        int  not null,
  year            int not null,
  doy             int not null,
  tstart          float not null,
  tstop           float not null,
  rowstart        int not null,
  rowstop         int not null,
  startmjf        int ,
  startmnf        int ,
  stopmjf         int ,
  stopmnf         int ,
  checksum        text ,
  tlmver          text ,
  ascdsver        text ,
  revision        int ,
  date            text not null,

  CONSTRAINT pk_archfiles PRIMARY KEY (filename)
);
CREATE INDEX idx_archfiles_filetime ON archfiles (filetime);
sqlite> select * from archfiles limit 5;
orbitf051004864N002_eph0.fits.gz|51004864|1999|226|51004864.184|52790464.184|0|5953|||||||R4CU5UPD9|2|2000-09-28T16:47:36
orbitf051580864N002_eph0.fits.gz|51580864|1999|232|51580864.184|53395264.184|5953|12002|||||||R4CU5UPD9|2|2000-09-28T16:47:52
orbitf052185664N002_eph0.fits.gz|52185664|1999|239|52185664.184|54000064.184|12002|18051|||||||R4CU5UPD9|2|2000-09-28T16:47:41
orbitf052790464N002_eph0.fits.gz|52790464|1999|246|52790464.184|54604864.184|18051|24100|||||||R4CU5UPD9|2|2000-09-28T16:47:53
orbitf053395264N002_eph0.fits.gz|53395264|1999|253|53395264.184|55209664.184|24100|30149|||||||R4CU5UPD9|2|2000-09-28T16:46:48
"""  # noqa: E501


def read_stk_file(path, format="stk", cache=True, **kwargs):
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
      Time float64
         X float64     m
         Y float64     m
         Z float64     m
        Vx float64 m / s
        Vy float64 m / s
        Vz float64 m / s

    Parameters
    ----------
    path : str
        Path on OCCweb of the STK ephemeris file, for example
        "FOT/mission_planning/Backstop/Ephemeris/Chandra_23177_24026.stk"
    format : str
        Format of the file ("stk" or "cxc")
    cache : bool
        If True (default), cache the file locally.
    **kwargs :
        Additional args passed to get_occweb_page()

    Returns
    -------
    astropy.table.Table :
        Table of ephemeris data.
    """
    text = occweb.get_occweb_page(path, cache=cache, **kwargs)
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
        "Time": CxoTime(isos, format="isot").secs,
        "X": Column(dat["x (km)"] * 1000, unit="m"),
        "Y": Column(dat["y (km)"] * 1000, unit="m"),
        "Z": Column(dat["z (km)"] * 1000, unit="m"),
        "Vx": Column(dat["vx (km/sec)"] * 1000, unit="m/s"),
        "Vy": Column(dat["vy (km/sec)"] * 1000, unit="m/s"),
        "Vz": Column(dat["vz (km/sec)"] * 1000, unit="m/s"),
    }
    return Table(out)


def get_ephem_stk_files(
    start: CxoTimeLike,
    stop: CxoTimeLike = None,
    latest_only=True,
):
    """Get STK orbit ephemeris files from OCCweb.

    Returns a list of dict like below for each STK file::

        {
            'path': 'FOT/mission_planning/Backstop/Ephemeris/Chandra_23107_23321.stk',
            'start': <CxoTime '2023:107:00:00:00.000'>,
            'stop': <CxoTime '2023:321:59:59.999'>,
        }

    Parameters
    ----------
    start : CxoTimeLike
        Start time of interval
    stop : CxoTimeLike
        Stop time of interval (default=NOW)
    latest_only : bool
        If True (default), return only the latest files that overlaps the interval.
        If False, return all files that overlap the interval.

    Returns
    -------
    files_stk : list of dict
        List of dict with keys path, start, stop
    """
    start = CxoTime(start)
    stop = CxoTime(stop)

    files_stk = []

    for dir_path in [EPHEM_STK_RECENT_DIR, EPHEM_STK_ARCHIVE_DIR]:
        print(dir_path)
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


def create_archive_ephem_stk_files(start: CxoTimeLike, stop: CxoTimeLike = None):
    """Create archive ephemeris STK files from OCCweb files.

    update_archive.py uses these columns (archfiles_hdr_cols)
        "tstart", "tstop",
        "startmjf", "startmnf", "stopmjf", "stopmnf",  # Optional
        "tlmver", "ascdsver", "revision",  # Optional
        "date",

    The optional ones just result in NULL values in the archfiles table.
    """
    start = CxoTime(start)
    stop = CxoTime(stop)

    stk_files = get_ephem_stk_files(start, stop, latest_only=False)
    print(stk_files)
