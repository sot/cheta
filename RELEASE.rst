0.19 - 2012-05-04
=================

- Fix MSID.raw_vals() so it handles state codes with different lengths
- Fix problem in iplot where units not tied to fetched MSID
- Add units to DEA housekeeping MSIDs

0.18 - 2012-04-30
=================

- Make it possible to reliably use the import mechanism to select different
  unit systems within the same script or Python process with no interactions.

0.17 - 2012-04-17
=================

- Improve tutorial documentation
- Modify PCAD derived parameters to use only predictive ephemeris
- Redefine DP_ROLL_FSS and DP_PITCH_FSS to improve accuracy
- Allow for filter_bad_times to function for data that have already been
  filtered.

0.16 and 0.15
=============

A number of major new features are available in the release 0.16 of the
Ska engineering archive:

- Built-in plotting capability and an interactive plot browser that
  allows arbitrary zooming and panning.  See tutorial sections: 
  Plotting time data (http://goo.gl/6tGNZ) and 
  Interactive plotting (http://goo.gl/2dG4c)

- Support for plotting state-valued MSIDs and for accessing
  the raw count values.  See: 
  State valued MSIDs (http://goo.gl/9R0Tz)

- Support for accessing Telemetry Database attributes related
  to an MSID.  See: 
  Telemetry database (http://goo.gl/pPo0s)

- PCAD derived parameters (main code from A. Arvai).  See:
  Derived PCAD parameters (http://goo.gl/iKDUK)

API Changes
-----------

- MSIDset.interpolate() now behaves more intuitively.  This was done
  by making the ``times`` attribute of interpolated MSIDs correspond
  to the new (linearly-spaced) interpolated times.  Previously
  times was set to the nearest-neighbor times, which is not generally
  useful.  See https://github.com/sot/eng_archive/issues/20 and
  Interpolation (http://goo.gl/5U5Kp)

Bug fixes
---------
- Fixed problem where Msidset fails for 5min and daily values.

0.14
====

Minor updates and bug fixes:

- Change max_gap for ACISDEAHK from 3600 to 10000 sec
- Add midvals attr for stat fetch
- Fix ss_vector() to use quaternion midvals and handle missing telemetry
- Fix typo in fetch.logical_intervals
- Explicitly set --data-root when calling update_archive.py in task_schedule.cfg

0.13
====

Version 0.13 of the Ska.engineering archive contains a number of
new features:

- Support for `derived parameter pseudo-MSIDs <http://goo.gl/354M6>`_.
  Currently there are number of thermal values and ACIS power values.  

- Two new `fetch.MSID <http://goo.gl/GBYvV>`_ methods:

  - logical_intervals() returns contiguous intervals during which a logical
    expression is true.
  - state_intervals() determines contiguous intervals during which the MSID
    value is unchanged.

- Two new classes fetch.Msid and fetch.Msidset.  These are just like fetch.MSID
  or fetch.MSIDset except that filter_bad=True by default.  You can use the
  new classes just like before but you'll always only get good data values.

- Changed definition of the "vals" attribute for '5min' and 'daily' stat values
  so "vals" is now the sames as "means".  Previously the "vals" attribute for a
  statistics fetch was the exact telemetry value at the interval midpoint.
  This quantity is not that useful and prone to errors since one frequently
  does things like::
  
      dat = fetch.MSID('tephin', '2011:150', stat='5min')
      plot_cxctime(dat.times, dat.vals)

- Caching of previously fetched data values.  This is disabled by default
  but used for telemetry and derived parameter ingest.  In certain
  circumstances caching can be useful.

- New function for truncating the engineering archive at a certain date.
  This is useful for fixing the database in the event of a corruption.
