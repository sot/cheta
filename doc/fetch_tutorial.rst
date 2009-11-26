The python module ``Ska.engarchive.fetch`` provides a simple interface to the 
engineering archive data files.  Using the module functions it is easy to
retrieve data over a time range for a single MSID or a related set of MSIDs.
The data are return as MSID objects that contain not only the telemetry timestamps 
and values but also various other data arrays and MSID metadata.

**First fetch**

The basic process of fetching data always starts with importing the module
into the python session::

  import Ska.engarchive.fetch as fetch

The ``as fetch`` part of the ``import`` statement just creates an short alias 
to avoid always typing the somewhat lengthy ``Ska.engarchive.fetch.MSID(..)``.  
Fetching and plotting full time-resolution data for a single MSID is then quite 
easy::

  tephin = fetch.MSID('tephin', '2009:001', '2009:007') # (MSID, start, stop)
  plot(tephin.times, tephin.vals)

.. image:: fetchplots/first.png

The ``tephin`` variable returned by ``fetch.MSID()`` is an ``MSID`` object and
we can access the various object attributes with ``<object>.<attr>``.  The
timestamps ``tephin.times`` and the telemetry values ``tephin.vals`` are both
numpy arrays.  As such you can inspect them and perform numpy operations and
explore their methods::

  type(tephin)
  tephin.vals.mean()
  tephin.vals.min()
  tephin.vals.<TAB>
  tephin.times[1:20]
  tephin.vals[1:20]

The name of the variable holding the MSID object is independent of the MSID name
itself.  Case is not important when specifying the MSID name so one might do::

  pcad_mode = fetch.MSID('AOpcadMD', '2009Jan01 at 12:00:00.000', '2009-01-12T14:15:16')
  pcad_mode.msid  # MSID name as entered by user
  pcad_mode.MSID  # Upper-cased version used internally

The ``times`` attribute gives the timestamps in elapsed seconds since
1998-01-01T00:00:00.  This is the start of 1998 in Terrestrial Time (TT) and forms
the basis for time for all CXC data files.  In order to make life inconvenient
1998-01-01T00:00:00 is actually 1997:365:23:58:56.816 (UTC).  This stems from
the difference of around 64 seconds between TT and UTC.

**Date and time formats**

.. include:: date_time_formats.rst

Converting between units is straightforward with the ``Chandra.Time`` module::

  import Chandra.Time
  datetime = Chandra.Time.DateTime(126446464.184)
  datetime.date
  Out: '2002:003:12:00:00.000'
  
  datetime.greta
  Out: '2002003.120000000'
  
  Chandra.Time.DateTime('2009:235:12:13:14').secs
  Out: 367416860.18399996

**Plotting time data**

Even though seconds since 1998.0 is convenient for computations it isn't so
natural for humans.  As mentioned the ``Chandra.Time`` module can help with
converting between formats but for making plots we use the 
`plot_cxctime() <http://cxc.harvard.edu/mta/ASPECT/tool_doc/pydocs/Ska.Matplotlib.html#Ska.Matplotlib.plot_cxctime>`_ 
function of the ``Ska.Matplotlib`` module::

  from Ska.Matplotlib import plot_cxctime
  plot_cxctime(tephin.times, tephin.vals)

That looks better:

.. image:: fetchplots/plot_cxctime.png

**Bad data**

At this point we've glossed over the important point of possible bad data.  For 
various reasons (typically a VCDU drop) the data value associated with a particular 
readout may be bad.  To handle this the engineering archive provides a boolean array 
called ``bads`` that is ``True`` for bad samples.  This array corresponds to the 
respective ``times`` and ``vals`` arrays.  To remove the bad values one can use numpy 
boolean masking::

  ok = ~tephin.bad  # numpy mask requires the "good" values to be True
  vals_ok = tephin.vals[ok]
  times_ok = tephin.times[ok]

This is a bother to do manually so there is a built-in method that filters out
bad data points for all the MSID data arrays.  Instead just do::

  tephin.filter_bad()

In fact it can be even easier if you tell fetch to filter the bad data at the point of
retrieving the data from the archive::

  tephin = fetch.MSID('tephin', '2009:001', '2009:007', filter_bad=True)

You might wonder why fetch ever bothers to return bad data and a bad mask, but
this will become apparent later when we start making scatter plots instead of
just time plots.

**5 minute and daily statistics**

The engineering telemetry archive also hosts tables of telemetry statistics
computed over 5 minute and daily intervals.  To be more precise, the intervals
are 328 seconds (10 major frames) and 86400 seconds.  The daily intervals are
not *exactly* lined up with the midnight boundary but are within a couple of minutes.  
These data are accessed by specifying 
``stat=<interval>`` in the ``fetch.MSID()`` call::

  tephin_5min = fetch.MSID('tephin', '2009:001', stat='5min')
  tephin_daily = fetch.MSID('tephin', '2000:001', stat='daily')
  plot_cxctime(tephin_daily.times, tephin_daily.mins, '-b')
  plot_cxctime(tephin_daily.times, tephin_daily.maxes, '-r')
  
.. image:: fetchplots/tephin_daily.png

Notice that we did not supply a stop time which means to return values up to the last
available data in the archive.  The start time, however, is always required.  

The MSID object returned for a telemetry statistics query has a number of array 
attributes, depending on the statistic and the MSID data type.

==========  =====  =====  ================= ================  ===================
Name        5min   daily  Supported types   Column type       Description
==========  =====  =====  ================= ================  ===================
times         x      x    int,float,string  float             Time at midpoint
indexes       x      x    int,float,string  int               Interval index
samples       x      x    int,float,string  int               Number of samples 
vals          x      x    int,float,string  int,float,string  Sample at midpoint
mins          x      x    int,float         int,float         Minimum
maxes         x      x    int,float         int,float         Maximum
means         x      x    int,float         float             Mean
stds                 x    int,float         float             Standard deviation
p01s                 x    int,float         float             1% percentile
p05s                 x    int,float         float             5% percentile
p16s                 x    int,float         float             16% percentile
p50s                 x    int,float         float             50% percentile
p84s                 x    int,float         float             84% percentile
p95s                 x    int,float         float             95% percentile
p99s                 x    int,float         float             99% percentile
==========  =====  =====  ================= ================  ===================

As an example a daily statistics query for the PCAD mode ``AOPCADMD``
(``NPNT``, ``NMAN``, etc) yields an object with only the ``times``,
``indexes``, ``samples``, and ``vals`` arrays.  For these state MSIDs
there is no really useful meaning for the other statistics.

Telemetry statistics are a little different than the full-resolution data in
that they do not have an associated bad values mask.  Instead if there are not
at least 3 good samples within an interval then no record for that interval
will exist.

**MSID sets**

Frequently one wants to fetch a set of MSIDs over the same time range.  This is
easily accomplished::

  rates = fetch.MSIDset(['aorate1', 'aorate2', 'aorate3'], '2009:001', '2009:002')

The returned ``rates`` object is like a python dictionary (hash) object with
a couple extra methods.  Indexing the object by the MSID name gives the
usual ``fetch.MSID`` object that we've been using up to this point::

  plot_cxctime(rates['aorate1'].times, rates['aorate1'].vals)

You might wonder what's special about an ``MSIDset``, after all the actual code
that creates an ``MSIDset`` is very simple::

  for msid in msids:
      self[msid] = MSID(msid, self.tstart, self.tstop, filter_bad=False, stat=stat)
  
  if filter_bad:
      self.filter_bad()

The answer lies in the additional methods that let you manipulate the MSIDs as a set and
enforce concordance between the MSIDs in the face of different bad values and/or 
different sampling.  

Say you want to calculate the spacecraft rates directly from telemetered gyro
count values instead of relying on OBC rates.  To do this you need to have
valid data for all 4 gyro channels at identical times.  In this case we know that 
the gyro count MSIDs AOGYRCT<N> all come at the same rate so the only issue is with
bad values.
::

  gyro_msids = ['aogyrct1', 'aogyrct2', 'aogyrct3', 'aogyrct4']
  cts = fetch.MSIDset(gyro_msids, '2009:001', '2009:002')
  cts.filter_bad()
  # OR equivalently
  cts = fetch.MSIDset(gyro_msids, '2009:001', '2009:002', filter_bad=True)

Now we know that ``cts['aogyrct1']`` is exactly lined up with
``cts['aogyrct2']`` and so forth.  Any bad value among the 4 MSIDs will filter
out the all the values for that time stamp.  It's important to note that the
resulting data may well have time "gaps" where bad values were filtered.  In this case
the time delta between samples won't always be 0.25625 seconds.

How do you know if your favorite MSIDs are always sampled at the same rate in
the Ska engineering archive?  Apart from certain sets of MSIDs that are obvious
(like the gyro counts), here is where things get a little complicated and a
digression is needed.  

The engineering archive is derived from CXC level-0 engineering telemetry
decom.  This processing divides the all the engineering MSIDs into groups based
on subsystem (ACIS, CCDM, EPHIN, EPS, HRC, MISC, OBC, PCAD, PROP, SIM, SMS,
TEL, THM) and further divides by sampling rate (e.g. ACIS2ENG, ACIS3ENG,
ACIS4ENG).  In all there about 80 "content-types" for engineering telemetry.
All MSIDs within a content type are guaranteed to come out of CXC L0 decom with
the same time-stamps, though of course the bad value masks can be different.
Thus from the perspective of the Ska engineering archive two MSIDs are sure to
have the same sampling (time-stamps) if and only if they have have the same CXC
content type.  In order to know whether the ``MSIDset.filter_bad()`` function
will apply a common bad values filter to a set of MSIDs you need to inspect the
content type as follows::

  msids = fetch.MSIDset(['aorate1', 'aorate2', 'aogyrct1', 'aogyrct2'], '2009:001', '2009:002')
  for msid in msids.values():
      print msid.msid, msid.content

In this case if we apply the ``filter_bad()`` method then ``aorate1`` and
``aorate2`` will be grouped separately from ``aogyrct1`` and ``aogyrct2``.  In
most cases this is probably the right thing, but there is another
hammer we can use if not.

Pretend we want to look for a correlation between gyro channel 1 rate and star centroid
rates in Y during an observation.  We get new gyro counts every 0.25625 sec and a
new centroid value every 2.05 sec.
::

  msids = fetch.MSIDset(['aoacyan3', 'aogyrct1'], '2009:246:08:00:00', '2009:246:18:00:00')
  msids.interpolate(dt=2.05)
  aca_dy = msids['aoacyan3'].vals[1:] - msids['aoacyan3'].vals[:-1]
  aca_dt = msids['aoacyan3'].times[1:] - msids['aoacyan3'].times[:-1]
  aca_rate = aca_dy / aca_dt
  gyr_dct1 = msids['aogyrct1'].vals[1:] - msids['aogyrct1'].vals[:-1]
  gyr_dt = msids['aogyrct1'].times[1:] - msids['aogyrct1'].times[:-1]
  gyr_rate = gyr_dct1 / gyr_dt * 0.02
  plot(aca_rate, gyr_rate, '.')

.. image:: fetchplots/aca_gyro_rates.png

**Putting it all together**

As a final example here is a real-world problem of wanting to compare OBC
rates to those derived on the ground using raw gyro data.
::

  import Ska.engarchive.fetch as fetch
  from Ska.Matplotlib import plot_cxctime
  import Ska.Numpy

  tstart = '2009:313:16:00:00'
  tstop = '2009:313:17:00:00'

  # Get OBC rates and gyro counts
  obc = fetch.MSIDset(['aorate1', 'aorate2', 'aorate3'], tstart, tstop, filter_bad=True)
  gyr = fetch.MSIDset(['aogyrct1', 'aogyrct2', 'aogyrct3', 'aogyrct4'], tstart, tstop, filter_bad=True)

  # Transform delta gyro counts (4 channels) to a body rate (3 axes)
  cts2rate = array([[-0.5       ,  0.5       ,  0.5       , -0.5       ],
                    [-0.25623091,  0.60975037, -0.25623091,  0.60975037],
                    [-0.55615682, -0.05620959, -0.55615682, -0.05620959]])

  # Calculate raw spacecraft rate directly from gyro data
  cts = np.array([gyr['aogyrct1'].vals,
                  gyr['aogyrct2'].vals,
                  gyr['aogyrct3'].vals,
                  gyr['aogyrct4'].vals])
  raw_times = (gyr['aogyrct1'].times[1:] + gyr['aogyrct1'].times[:-1]) / 2
  delta_times = gyr['aogyrct1'].times[1:] - gyr['aogyrct1'].times[:-1]
  delta_cts = cts[:, 1:] - cts[:, :-1]
  raw_rates = np.dot(cts2rate, delta_cts) * 0.02 / delta_times

  # Plot the OBC rates
  figure(1, figsize=(8,6))
  clf()
  for frame, msid, label in ((1, 'aorate1', 'roll'),
                             (2, 'aorate2', 'pitch'),
                             (3, 'aorate3', 'yaw')):
      subplot(3, 1, frame)
      obc_rates = obc[msid].vals * 206254.
      plot_cxctime(obc[msid].times, obc_rates, '-')
      plot_cxctime(obc[msid].times, Ska.Numpy.smooth(obc_rates, window_len=20), '-r')
      ylim(average(obc_rates) + array([-1.5, 1.5]))
      title(label.capitalize() + ' rate (arcsec/sec)')

  subplots_adjust(bottom=0.12, top=0.90)
  # savefig('obc_rates.png')

  # Plot the S/C rates from raw gyro data
  figure(2, figsize=(8,6))
  clf()
  for axis, label in ((0, 'roll'),
                      (1, 'pitch'),
                      (2, 'yaw')):
      subplot(3, 1, 1+axis)
      raw_rate = raw_rates[axis, :]
      plot_cxctime(raw_times, raw_rate, '-')
      plot_cxctime(raw_times, Ska.Numpy.smooth(raw_rate, window_len=20), '-r')
      ylim(np.mean(raw_rate) + np.array([-0.4, 0.4]))
      title(label.capitalize() + ' S/C rate (arcsec/sec)')

  subplots_adjust(bottom=0.12, top=0.90)
  # savefig('gyro_sc_rates.png')

.. image:: fetchplots/obc_rates.png
.. image:: fetchplots/gyro_sc_rates.png

**To do**

* Add telemetry:

  - 3TSCPOS and 3FAPOS
  - ACIS DEA housekeeping
  - ACA header-3

* Apply transformations to P009 units (e.g. Kelvins to C or F)
* Add MSID method to determine exact time of mins or maxes
