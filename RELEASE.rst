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
