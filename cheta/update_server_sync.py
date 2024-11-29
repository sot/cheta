# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
Update the repository of sync files on the server which can be used by
clients to maintain a local copy of the cheta telemetry archive.

The basic concept is to bundle about a day of raw telemetry values
(full-resolution, 5-minute stats and daily stats) for each MSID into
compressed data files that are served by the icxc web server and can
be easily downloaded to client machines.

This pairs with the ``cheta_update_client_archive`` script which uses
these sync files to keep a local cheta archive up to date.

The file structure is as follows::

  sync/                                        Top-level, accessible from icxc URL
  sync/msid_contents.pkl.gz                    Dict of all MSID:content key pairs
  sync/acis4eng/                               Content type
  sync/acis4eng/index.ecsv                     Index of bundles
  sync/acis4eng/last_rows_5min.pkl             Last row index for 5min data for each MSID
  sync/acis4eng/last_rows_daily.pkl            Last row index for daily data for each MSID
  sync/acis4eng/2019-07-29T2340z/              One bundle of sync data
  sync/acis4eng/2019-07-29T2340z/full.pkl.gz   Full-resolution data for all acis4eng MSIDs
  sync/acis4eng/2019-07-29T2340z/5min.pkl.gz   5-minute data
  sync/acis4eng/2019-07-29T2340z/daily.pkl.gz  Daily data

This script reads from the cheta telemetry archive and updates the
sync repository to capture newly-available data since the last bundle.
"""

import argparse
import gzip
import pickle
import shutil
from itertools import count
from pathlib import Path

import numpy as np
import pyyaks.context
import pyyaks.logger
import tables
from astropy.table import Table
from Chandra.Time import DateTime
from Ska.DBI import DBI

from . import fetch, file_defs
from .utils import STATS_DT, get_date_id

sync_files = pyyaks.context.ContextDict(f"{__name__}.sync_files")
sync_files.update(file_defs.sync_files)


def get_options(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sync-root", default=".", help="Root directory for sync files (default='.')"
    )
    parser.add_argument(
        "--content",
        action="append",
        help="Content type to process [match regex] (default = all)",
    )
    parser.add_argument(
        "--max-days",
        type=float,
        default=1.5,
        help="Max number of days of files per sync directory (default=1.5)",
    )
    parser.add_argument(
        "--max-lookback",
        type=float,
        default=60,
        help="Maximum number of days to look back from --date-stop (default=60)",
    )
    parser.add_argument(
        "--max-sync-dirs",
        type=int,
        default=60,
        help="Number of sync directories to keep before removing oldest (default=60)",
    )
    parser.add_argument("--log-level", default=20, help="Logging level")
    parser.add_argument(
        "--date-start",
        help=(
            "Start process date (default=NOW - max-lookback). "
            "Provide this parameter when creating a new sync directory."
        ),
    )
    parser.add_argument("--date-stop", help="Stop process date (default=NOW)")
    return parser.parse_args(args)


def update_msid_contents_pkl(logger):
    """
    Update the `msid_contents.pkl` file to contain a dict of the msid:content pairs.

    :return: None
    """
    filename = Path(sync_files["msid_contents"].abs)

    # Check if an existing version of the file is the same and do not overwrite
    # in that case.
    if filename.exists():
        with gzip.open(filename, "rb") as fh:
            msid_contents = pickle.load(fh)
        if msid_contents == fetch.content:
            return

    logger.info(f"Writing contents pickle {filename}")
    with gzip.open(filename, "wb") as fh:
        pickle.dump(fetch.content, fh, protocol=-1)


def main(args=None):
    # Setup for updating the sync repository
    opt = get_options(args)
    sync_files.basedir = opt.sync_root

    # Set up logging
    loglevel = int(opt.log_level)
    logger = pyyaks.logger.get_logger(
        name="cheta_update_server_sync",
        level=loglevel,
        format="%(asctime)s %(message)s",
    )

    if opt.content:
        contents = opt.content
    else:
        contents = set(fetch.content.values())

    for content in sorted(contents):
        update_sync_repo(opt, logger, content)

    # Make the main msid_contents.pkl file
    update_msid_contents_pkl(logger)


def remove_outdated_sync_files(opt, logger, index_tbl, index_file):
    """
    Remove the sync data dirs and index file rows which correspond to data so
    that no more than ``opt.max_sync_dirs`` sync directories are retained.

    :param opt: options
    :param logger: logger
    :param index_tbl: table containing sync repo entries
    :param index_file: index file Path
    :return: mask of rows that were removed
    """
    # If index table is not too long then no action required.
    if len(index_tbl) <= opt.max_sync_dirs:
        return

    # Index before which rows will be deleted.  Note that index_tbl is guaranteed to be
    # sorted by in ascending order by row (and thus by time) because of
    # check_index_tbl_consistency()
    idx0 = len(index_tbl) - opt.max_sync_dirs

    # Iterate over rows to be deleted and delete corresponding file directories.
    for row in index_tbl[:idx0]:
        fetch.ft["date_id"] = row["date_id"]
        data_dir = sync_files["data_dir"].abs
        if Path(data_dir).exists():
            logger.info(f"Removing sync directory {data_dir}")
            shutil.rmtree(data_dir)

    index_tbl = index_tbl[idx0:]
    logger.info(f"Writing {len(index_tbl)} row(s) to index file {index_file}")
    index_tbl.write(index_file, format="ascii.ecsv", overwrite=True)


def update_sync_repo(opt, logger, content):
    """

    :param opt: argparse options
    :param logger: logger instance
    :param content: content type
    :return:
    """
    # File types context dict
    ft = fetch.ft
    ft["content"] = content

    index_file = Path(sync_files["index"].abs)
    index_tbl = update_index_file(index_file, opt, logger)

    if index_tbl is None:
        # Index table was not created, nothing more to do here
        logger.warning(
            f"WARNING: No index table for {content} (use --date-start to create)"
        )
        return

    for row in index_tbl:
        ft = fetch.ft
        ft["date_id"] = row["date_id"]

        update_sync_data_full(content, logger, row)
        update_sync_data_stat(content, logger, row, "5min")
        update_sync_data_stat(content, logger, row, "daily")

    remove_outdated_sync_files(opt, logger, index_tbl, index_file)


def get_row_from_archfiles(archfiles):
    # Make a row that encapsulates info for this setup of data updates. The ``date_id`` key is a
    # date like 2019-02-20T2109z, human-readable and Windows-friendly (no :) for a unique
    # identifier for this set of updates.
    date_id = get_date_id(DateTime(archfiles[0]["filetime"]).fits)
    row = {
        "date_id": date_id,
        "filetime0": archfiles[0]["filetime"],
        "filetime1": archfiles[-1]["filetime"],
        "row0": archfiles[0]["rowstart"],
        "row1": archfiles[-1]["rowstop"],
    }
    return row


def check_index_tbl_consistency(index_tbl):
    """
    Check for consistency of the index table.

    :param index_tbl: index table (astropy Table)
    :return msg: inconsistency message or None
    """
    filetimes = []
    for row in index_tbl:
        filetimes.append(row["filetime0"])
        filetimes.append(row["filetime1"])

    if np.any(np.diff(filetimes) < 0):
        msg = "filetime values not monotonically increasing"
        return msg

    for idx, row0, row1 in zip(count(), index_tbl[:-1], index_tbl[1:]):
        if row0["row1"] != row1["row0"]:
            msg = f'rows not contiguous at table date0={index_tbl["date_id"][idx]}'
            return msg

    # No problems
    return None


def update_index_file(index_file, opt, logger):
    """Update the top-level index file of data available in the sync archive

    :param index_file: Path of index ECSV file
    :param opt: options
    :param logger: output logger
    :return: index table (astropy Table)
    """
    if index_file.exists():
        # Start time of last update contained in the sync repo (if it exists), but do not look
        # back more than max_lookback days.  This is relevant for rarely sampled
        # content like cpe1eng.
        filetime0 = (DateTime(opt.date_stop) - opt.max_lookback).secs

        index_tbl = Table.read(index_file)
        if len(index_tbl) == 0:
            # Need to start with a fresh index_tbl since the string column will end up
            # with a length=1 string (date_id) and add_row later will give the wrong result.
            index_tbl = None
        else:
            filetime0 = max(filetime0, index_tbl["filetime1"][-1])
    else:
        # For initial index file creation use the --date-start option
        index_tbl = None
        filetime0 = DateTime(opt.date_start).secs

    max_secs = int(opt.max_days * 86400)
    time_stop = DateTime(opt.date_stop).secs

    # Step through the archfile files entries and collect them into groups of up
    # to --max-days based on file time stamp (which is an integer in CXC secs).
    rows = []
    filename = fetch.msid_files["archfiles"].abs
    logger.verbose(f"Opening archfiles {filename}")
    with DBI(dbi="sqlite", server=filename) as dbi:
        while True:
            filetime1 = min(filetime0 + max_secs, time_stop)
            logger.verbose(
                "select from archfiles "
                f"filetime > {DateTime(filetime0).fits[:-4]} {filetime0} "
                f"filetime <= {DateTime(filetime1).fits[:-4]} {filetime1} "
            )
            archfiles = dbi.fetchall(
                "select * from archfiles "
                f"where filetime > {filetime0} "
                f"and filetime <= {filetime1} "
                "order by filetime "
            )

            # Found new archfiles?  If so get a new index table row for them.
            if len(archfiles) > 0:
                rows.append(get_row_from_archfiles(archfiles))
                filedates = DateTime(archfiles["filetime"]).fits
                logger.verbose(
                    f"Got {len(archfiles)} archfiles rows from "
                    f"{filedates[0]} to {filedates[-1]}"
                )

            filetime0 = filetime1

            # Stop if already queried out to the end of desired time range
            if filetime1 >= time_stop:
                break

    if not rows:
        logger.info(f'No updates available for content {fetch.ft["content"]}')
        return index_tbl

    # Create table from scratch or add new rows.  In normal processing there
    # will just be one row per run.
    if index_tbl is None:
        index_tbl = Table(rows)
    else:
        for row in rows:
            index_tbl.add_row(row)

    if not index_file.parent.exists():
        logger.info(f"Making directory {index_file.parent}")
        index_file.parent.mkdir(exist_ok=True, parents=True)

    msg = check_index_tbl_consistency(index_tbl)
    if msg:
        msg += "\n"
        msg += "\n".join(index_tbl.pformat(max_lines=-1, max_width=-1))
        logger.error(f"ERROR: Index table inconsistency: {msg}")
        return None

    logger.info(f"Writing {len(rows)} row(s) to index file {index_file}")
    index_tbl.write(index_file, format="ascii.ecsv", overwrite=True)

    return index_tbl


def update_sync_data_full(content, logger, row):
    """
    Update full-resolution sync data including archfiles for index table ``row``

    This generates a gzipped pickle file with a dict that has sync update values
    for all available  MSIDs in this chunk of ``content`` telemetry.  This has
    `archfiles` (structured ndarray of rows) to store archfiles rows and then
    {msid}.quality, {msid}.data, {msid}.row0 and {msid}.row1.

    :param content: content type
    :param logger: global logger
    :param row: archfile row
    :return: None
    """
    ft = fetch.ft
    ft["interval"] = "full"

    outfile = Path(sync_files["data"].abs)
    if outfile.exists():
        logger.verbose(f"Skipping {outfile}, already exists")
        return

    out = {}
    msids = list(fetch.all_colnames[content]) + ["TIME"]

    # row{filetime0} and row{filetime1} are the *inclusive* `filetime` stamps
    # for the archfiles to be included  in this row.  They do not overlap, so
    # the selection below must be equality.
    with DBI(dbi="sqlite", server=fetch.msid_files["archfiles"].abs) as dbi:
        query = (
            "select * from archfiles "
            f'where filetime >= {row["filetime0"]} '
            f'and filetime <= {row["filetime1"]} '
            "order by filetime "
        )
        archfiles = dbi.fetchall(query)
        out["archfiles"] = archfiles

    # Row slice indexes into full-resolution MSID h5 files.  All MSIDs share the
    # same row0:row1 range.
    row0 = row["row0"]
    row1 = row["row1"]

    # Go through each MSID and collect values
    n_msids = 0
    for msid in msids:
        ft["msid"] = msid
        filename = fetch.msid_files["msid"].abs
        if not Path(filename).exists():
            logger.debug(f"No MSID file for {msid} - skipping")
            continue

        n_msids += 1
        with tables.open_file(filename, "r") as h5:
            out[f"{msid}.quality"] = h5.root.quality[row0:row1]
            out[f"{msid}.data"] = h5.root.data[row0:row1]
            out[f"{msid}.row0"] = row0
            out[f"{msid}.row1"] = row1

    n_rows = row1 - row0
    logger.info(f"Writing {outfile} with {n_rows} rows of data and {n_msids} msids")

    outfile.parent.mkdir(exist_ok=True, parents=True)
    # TODO: increase compression to max (gzip?)
    with gzip.open(outfile, "wb") as fh:
        pickle.dump(out, fh)


def _get_stat_data_from_archive(filename, stat, tstart, tstop, last_row1, logger):
    """
    Return stat table rows in the range tstart <= time < tstop.

    Also returns the corresponding table row indexes.

    :param filename: HDF5 file to read
    :param stat: stat (5min or daily)
    :param tstart: min time
    :param tstop: max time
    :param last_row1: row1 for previous index table entry
    :param logger: logger
    :return:
    """
    dt = STATS_DT[stat]

    logger.verbose(
        f"_get_stat_data({filename}, {stat}, {DateTime(tstart).fits}, "
        f"{DateTime(tstop).fits}, {last_row1})"
    )

    with tables.open_file(filename, "r") as h5:
        # Check if tstart is beyond the end of the table.  If so, return an empty table
        table = h5.root.data
        last_index = table[-1]["index"]
        last_time = (last_index + 0.5) * dt
        if tstart > last_time:
            logger.verbose(
                f"No available stats data {DateTime(tstart).fits} > "
                f"{DateTime(last_time).fits} (returning empty table)"
            )
            row0 = row1 = len(table)
            table_rows = table[row0:row1]
        else:
            # Compute approx number of rows from the end for tstart.  Normally the index value
            # goes in lock step with row, but it can happen that an index is missed because of
            # missing data.  But if we back up by delta_rows, we are guaranteed to get to at
            # least the row corresponding to tstart.
            delta_rows = int((last_time - tstart) / dt) + 10

            # For rarely sampled data like CPE1ENG, delta_rows can end up being larger than the
            # table due to the gaps.  Therefore clip to the length of the table.
            delta_rows = min(delta_rows, len(table))

            times = (table[-delta_rows:]["index"] + 0.5) * dt

            # In the worst case of starting to sync a client archive for a rarely-sampled
            # content like cpe1eng or pcad7eng (AOSPASA2CV,) we need to include an extra ``dt``
            # on both ends to ensure that the first / last rows are caught. If the last
            # full-res sample is either before or after the stat mid-point timestamp then
            # stat sample may get dropped. This happened in real life for AOSPASA2CV.
            # Having extra rows on front is OK because they just get clipped, and an extra
            # row on back is OK because of clipping on the next update (and in normal
            # processing we always want the sync archive to have all recent data).
            sub_row0, sub_row1 = np.searchsorted(times, [tstart - dt, tstop + dt])
            sub_row_offset = len(table) - delta_rows

            row0 = sub_row0 + sub_row_offset
            row1 = sub_row1 + sub_row_offset

            # If we have the last value of row1 (from previous sync entry) then use
            # that instead of computed value for row0.
            if last_row1 is not None:
                row0 = last_row1

            table_rows = table[row0:row1]  # returns np.ndarray (structured array)

    return table_rows, row0, row1


def update_sync_data_stat(content, logger, row, stat):
    """
    Update stats (5min, daily) sync data for index table ``row``

    :param content: content name (e.g. acis4eng)
    :param logger: logger
    :param row: one row of the full-res index table
    :param stat: stat interval (5min or daily)
    :return:
    """
    ft = fetch.ft
    ft["interval"] = stat

    outfile = Path(sync_files["data"].abs)
    if outfile.exists():
        logger.verbose(f"Skipping {outfile}, already exists")
        return

    # First get the times corresponding to row0 and row1 in the full resolution archive
    ft["msid"] = "TIME"
    with tables.open_file(fetch.msid_files["msid"].abs, "r") as h5:
        table = h5.root.data
        tstart = table[row["row0"]]
        # Ensure that table row1 (for tstop) doesn't fall off the edge since the last
        # index file row will have row1 exactly equal to the table length.
        row1 = min(row["row1"], len(table) - 1)
        tstop = table[row1]

    out = {}
    msids = list(fetch.all_colnames[content] - set(fetch.IGNORE_COLNAMES))

    # Get dict of last sync repo row for each MSID.  This is keyed as {msid: last_row1},
    # where row1 is (as always) the slice row1.
    last_rows_filename = sync_files["last_rows"].abs
    if Path(last_rows_filename).exists():
        logger.verbose(f"Reading {last_rows_filename}")
        last_rows = pickle.load(open(last_rows_filename, "rb"))
    else:
        last_rows = {}

    # Go through each MSID and get the raw HDF5 table data corresponding to the
    # time range tstart:tstop found above.
    n_rows_set = set()
    n_msids = 0
    for msid in msids:
        last_row1 = last_rows.get(msid)
        ft["msid"] = msid
        filename = fetch.msid_files["stats"].abs
        if not Path(filename).exists():
            logger.debug(f"No {stat} stat data for {msid} - skipping")
            continue

        n_msids += 1
        stat_rows, row0, row1 = _get_stat_data_from_archive(
            filename, stat, tstart, tstop, last_row1, logger
        )
        logger.verbose(f"Got stat rows {row0} {row1} for stat {stat} {msid}")
        n_rows_set.add(row1 - row0)
        if row1 > row0:
            out[f"{msid}.data"] = stat_rows
            out[f"{msid}.row0"] = row0
            out[f"{msid}.row1"] = row1
            last_rows[msid] = row1

    n_rows = n_rows_set.pop() if len(n_rows_set) == 1 else n_rows_set

    outfile.parent.mkdir(exist_ok=True, parents=True)
    # TODO: increase compression to max (gzip?)
    logger.info(f"Writing {outfile} with {n_rows} rows of data and {n_msids} msids")
    with gzip.open(outfile, "wb") as fh:
        pickle.dump(out, fh)

    # Save the row1 value for each MSID to use as row0 for the next update
    logger.verbose(f"Writing {last_rows_filename}")
    with open(last_rows_filename, "wb") as fh:
        pickle.dump(last_rows, fh)


if __name__ == "__main__":
    main()
