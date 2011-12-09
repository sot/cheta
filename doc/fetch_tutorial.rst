================================
Fetch Tutorial
================================

The python module ``Ska.engarchive.fetch`` provides a simple interface to the 
engineering archive data files.  Using the module functions it is easy to
retrieve data over a time range for a single MSID or a related set of MSIDs.
The data are return as MSID objects that contain not only the telemetry timestamps 
and values but also various other data arrays and MSID metadata.

Getting started
================

**Running the demo**

This tutorial is available to be run as an IPython demo.  Each section of
commands will be shown and then you can press <Enter> to actually run them
interactively.  This will allow more time to understand what's happening and
less time typing or cut-n-pasting.  To run the demo enter the following::

  import IPython.demo
  go = IPython.demo.IPythonDemo('/proj/sot/ska/share/eng_archive/fetch_tutorial.py')
  go()

Now you will see the following::

  **************** <fetch_tutorial.py> block # 0 (35 remaining) ****************
  ## The basic process of fetching data always starts with importing the module
  ## into the python session::

  print "Welcome to the fetch module!"
  import Ska.engarchive.fetch as fetch

  ****************** Press <q> to quit, <Enter> to execute... ******************

This means that a block of code from the fetch demo is queued up to be
executed.  The red text lines are comments.  Now press <Enter> to actually run
the code.  You will see the following, which means that the code ran and ``ipython``
is waiting for your next command::

   -------> print("Welcome to the fetch module!")
  Welcome to the fetch module!
  
  In [3]: 

Now you can inspect variables or do any other analysis (as we'll learn later)
or just continue to the next block of the tutorial by entering ``go()`` again
or by hitting the <Up-arrow> followed by <Enter>.

**First fetch**

The basic process of fetching data always starts with importing the module
into the python session::

  import Ska.engarchive.fetch as fetch

The ``as fetch`` part of the ``import`` statement just creates an short alias 
to avoid always typing the somewhat lengthy ``Ska.engarchive.fetch.MSID(..)``.  
Fetching and plotting full time-resolution data for a single MSID is then quite 
easy::

  tephin = fetch.MSID('tephin', '2009:001', '2009:007') # (MSID, start, stop)
  clf()
  plot(tephin.times, tephin.vals)

.. image:: fetchplots/first.png

The ``tephin`` variable returned by ``fetch.MSID()`` is an ``MSID`` object and
we can access the various object attributes with ``<object>.<attr>``.  The
timestamps ``tephin.times`` and the telemetry values ``tephin.vals`` are both
numpy arrays.  As such you can inspect them and perform numpy operations and
explore their methods::

  type(tephin)
  type(tephin.vals)
  help tephin.vals
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

Date and time formats
======================

.. include:: date_time_formats.rst

Converting between units is straightforward with the ``Chandra.Time`` module::

  import Chandra.Time
  datetime = Chandra.Time.DateTime(126446464.184)
  datetime.date
  Out[]: '2002:003:12:00:00.000'
  
  datetime.greta
  Out[]: '2002003.120000000'
  
  Chandra.Time.DateTime('2009:235:12:13:14').secs
  Out[]: 367416860.18399996

Exporting to CSV
================

If you want to move the fetch data to your local machine an ``MSID`` or
``MSIDset`` can be exported as ASCII data table(s) in CSV format.  This can
easily be imported into Excel or other PC applications.::

  biases = fetch.MSIDset(['aogbias1', 'aogbias2', 'aogbias3'], '2002:001', stat='daily')
  biases.write_zip('biases.zip')

To suspend the ipython shell and look at the newly created file do::

  <Ctrl>-z

  % ls -l biases.zip
  -rw-rw-r-- 1 aldcroft aldcroft 366924 Dec  4 17:07 biases.zip

  % unzip -l biases.zip
  Archive:  biases.zip
    Length     Date   Time    Name
   --------    ----   ----    ----
     510809  12-04-09 17:02   aogbias1.csv
     504556  12-04-09 17:02   aogbias2.csv
     504610  12-04-09 17:02   aogbias3.csv
   --------                   -------
    1519975                   3 files

To resume your ``ipython`` session::

  % fg

From a separate local cygwin or terminal window then retrieve the zip file and
unzip as follows::

  scp ccosmos.cfa.harvard.edu:biases.zip ./
  unzip biases.zip

Plotting time data
====================

Even though seconds since 1998.0 is convenient for computations it isn't so
natural for humans.  As mentioned the ``Chandra.Time`` module can help with
converting between formats but for making plots we use the 
`plot_cxctime() <http://cxc.harvard.edu/mta/ASPECT/tool_doc/pydocs/Ska.Matplotlib.html#Ska.Matplotlib.plot_cxctime>`_ 
function of the ``Ska.Matplotlib`` module::

  from Ska.Matplotlib import plot_cxctime
  clf()
  plot_cxctime(tephin.times, tephin.vals)

That looks better:

.. image:: fetchplots/plot_cxctime.png

Bad data
=========

At this point we've glossed over the important point of possible bad data.  For 
various reasons (typically a VCDU drop) the data value associated with a particular 
readout may be bad.  To handle this the engineering archive provides a boolean array 
called ``bads`` that is ``True`` for bad samples.  This array corresponds to the 
respective ``times`` and ``vals`` arrays.  To remove the bad values one can use numpy 
boolean masking::

  ok = ~tephin.bads  # numpy mask requires the "good" values to be True
  vals_ok = tephin.vals[ok]
  times_ok = tephin.times[ok]

This is a bother to do manually so there is a built-in method that filters out
bad data points for all the MSID data arrays.  Instead just do::

  tephin.filter_bad()

In fact it can be even easier if you tell fetch to filter the bad data at the point of
retrieving the data from the archive::

  tephin = fetch.MSID('tephin', '2009:001', '2009:007', filter_bad=True)

You might wonder why fetch ever bothers to return bad data and a bad mask, but
this will become apparent later when we start using time-correlated values instead
just simple time plots.

**Really bad data**

Even after applying ``filter_bad()`` you may run across obviously bad data in
the archive (e.g. there is a single value of AORATE1 of around 2e32
in 2007).  These are not marked with bad quality in the CXC archive and are
presumably real telemetry errors.  If you run across a bad data point you can
locate and filter it out as follows (but also see the next section)::

  aorate1 = fetch.MSID('aorate1', '2007:001', '2008:001', filter_bad=True)
  bad_vals_mask = abs(aorate1.vals) > 0.01
  aorate1.vals[bad_vals_mask]
  Out[]: array([ -2.24164635e+32], dtype=float32)

  Chandra.Time.DateTime(aorate1.times[bad_vals_mask]).date
  Out[]: array(['2007:310:22:10:02.951'], 
         dtype='|S21')

  aorate1.filter_bad(bad_vals_mask)
  bad_vals_mask = abs(aorate1.vals) > 0.01
  aorate1.vals[bad_vals_mask]
  Out[]: array([], dtype=float32)

.. _filter_bad_times:

**Filtering out bad time intervals of data**

If you want to remove an interval of time known to have bad values there is an
easy way with the ``filter_bad_times`` method::

  aorate1 = fetch.MSID('aorate1', '2007:001', '2008:001', filter_bad=True)
  aorate1.filter_bad_times('2007:025:12:13:00', '2007:026:09:00:00')

As expected this will remove all data from the aorate1 MSID between the
specified times.  Multiple bad time filters can be specified at once using the
``table`` parameter option for ``filter_bad_times``::

  bad_times = ['2008:292:00:00:00 2008:297:00:00:00',
               '2008:305:00:12:00 2008:305:00:12:03',
               '2010:101:00:01:12 2010:101:00:01:25']
  msid.filter_bad_times(table=bad_times)

The ``table`` parameter can also be the name of a plain text file that has two
columns (separated by whitespace) containing the start and stop times::

  msid.filter_bad_times(table='msid_bad_times.dat')

Because the bad times for corrupted data don't change it doesn't always
make sense to always have to put these hard-coded times into every plotting or
analysis script.  Instead fetch also allows you to create a plain text file of
bad times in a simple format.  The file can include any number of bad time
interval specifications, one per line.  A bad time interval line has three
columns separated by whitespace, for instance::

  # Bad times file: "bad_times.dat"
  # MSID      bad_start_time  bad_stop_time
  aogbias1 2008:292:00:00:00 2008:297:00:00:00
  aogbias1 2008:227:00:00:00 2008:228:00:00:00
  aogbias1 2009:253:00:00:00 2009:254:00:00:00
  aogbias2 2008:292:00:00:00 2008:297:00:00:00
  aogbias2 2008:227:00:00:00 2008:228:00:00:00
  aogbias2 2009:253:00:00:00 2009:254:00:00:00
      
The MSID name is not case sensitive and the time values can be in any
``DateTime`` format.  Blank lines and any line starting with the # character
are ignored.  To read in this bad times file do::

  fetch.read_bad_times('bad_times.dat')

Once you've done this you can filter out all those bad times with a single method of
the MSID object::

  aorate1.filter_bad_times()

In this case no start or stop time was supplied and the routine instead knows
to use the internal registry of bad times defined by MSID.  Finally, as if this
wasn't easy enough, there is a global list of bad times that is always read
when the fetch module is loaded.  If you come across an interval of time that
can always be filtered by all users of fetch then send an email to Tom Aldcroft
with the interval and MSID and that will be added to the global registry.
After that there will be no need to explicitly run the
``fetch.read_bad_times(filename)`` command to exclude that interval.

At the present time this filtering only applies to MSID objects and not for MSIDset 
objects.  Upon request this can be implemented.

Five minute and daily stats
===========================

The engineering telemetry archive also hosts tables of telemetry statistics
computed over 5 minute and daily intervals.  To be more precise, the intervals
are 328 seconds (10 major frames) and 86400 seconds.  The daily intervals are
not *exactly* lined up with the midnight boundary but are within a couple of minutes.  
These data are accessed by specifying 
``stat=<interval>`` in the ``fetch.MSID()`` call::

  tephin_5min = fetch.MSID('tephin', '2009:001', stat='5min')
  tephin_daily = fetch.MSID('tephin', '2000:001', stat='daily')
  figure(1)
  clf()
  plot_cxctime(tephin_daily.times, tephin_daily.mins, '-b')
  plot_cxctime(tephin_daily.times, tephin_daily.maxes, '-r')
  figure(2)
  clf()
  plot_cxctime(tephin_5min.times, tephin_5min.means, '-b')
  
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
samples       x      x    int,float,string  int16             Number of samples
midvals       x      x    int,float,string  int,float,string  Sample at midpoint
vals          x      x    int,float         int,float         Mean
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

Note: the inadvertent use of int16 for the daily stat ``samples`` column means
that it rolls over at 32767.  This column should not be trusted at this time.

As an example a daily statistics query for the PCAD mode ``AOPCADMD``
(``NPNT``, ``NMAN``, etc) yields an object with only the ``times``,
``indexes``, ``samples``, and ``vals`` arrays.  For these state MSIDs
there is no really useful meaning for the other statistics.

Telemetry statistics are a little different than the full-resolution data in
that they do not have an associated bad values mask.  Instead if there are not
at least 3 good samples within an interval then no record for that interval
will exist.

MSID sets
==========

Frequently one wants to fetch a set of MSIDs over the same time range.  This is
easily accomplished::

  rates = fetch.MSIDset(['aorate1', 'aorate2', 'aorate3'], '2009:001', '2009:002')

The returned ``rates`` object is like a python dictionary (hash) object with
a couple extra methods.  Indexing the object by the MSID name gives the
usual ``fetch.MSID`` object that we've been using up to this point::

  clf()
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
  clf()
  plot(aca_rate, gyr_rate, '.')

.. image:: fetchplots/aca_gyro_rates.png

Unit systems
==============

Within ``fetch`` it is possible to select a different system of physical 
units for the retrieved telemetry.  Internally the engineering archive
stores values in the FITS format standard units as used by the CXC archive.
This is essentially the MKS system and features all temperatures in Kelvins
(not the most convenient).  

In addition to the CXC unit system one can select "science" units or 
"engineering" units:

====== ==============================================================
System  Description
====== ==============================================================
cxc    FITS standard units used in CXC archive files (basically MKS)
sci    Same as "cxc" but with temperatures in degC instead of Kelvins
eng    OCC engineering units (TDB P009, e.g. degF, ft-lb-sec, PSI)
====== ==============================================================

The simplest way to select a different unit system is to alter the
canonical command for importing the ``fetch`` module.  To use OCC 
engineering units use the following command::

  from Ska.engarchive import fetch_eng as fetch

This uses a special Python syntax to import the ``fetch_eng`` module
but then refer to it as ``fetch``.  In this way there is no need to
change existing codes (except one line) or habits.  To use "science"
units use the command::

  from Ska.engarchive import fetch_sci as fetch

The two modules ``fetch_eng`` and ``fetch_sci`` are just very thin wrappers
around ``fetch``.  Underneath what they do is use the ``fetch.set_units()``
command to set the unit system.  So an alternate to the above methods is to
explicitly set the unit system.  This can be done at any time and you can
switch between unit systems as desired.  (But the units for previously
fetched telemetry will *not* change).  In addition the actual unit for any
MSID telemetry can be obtained with the ``unit`` attribute.

Example::

  from Ska.engarchive import fetch
  
  fetch.set_units('eng')
  mom1 = fetch.MSID('aosymom1', '2010:001', '2010:002')
  print mom1.unit  # prints "FTLBSEC"
  
  fetch.set_units('sci')
  mom1 = fetch.MSID('aosymom1', '2010:001', '2010:002')
  print mom1.unit  # print "J*s"

Pushing it to the limit
========================

The engineering telemetry archive is designed to help answer questions that
require big datasets.  Let's explore what is possible.  First quit from your
current ``ipython`` session with ``exit()``.  Then start a window that will let
you watch memory usage::

  xterm -geometry 80x15 -e 'top -u <username>' &

This brings up a text-based process monitor.  Focus on that window and hit "M"
to tell it to order by memory usage.  Now go back to your main window and get
all the ``TEIO`` data for the mission::

  ipython -pylab
  import Ska.engarchive.fetch as fetch
  from Ska.Matplotlib import plot_cxctime
  time teio = fetch.MSID('teio', '2000:001', '2010:001', filter_bad=True)
  Out[]: CPU times: user 2.08 s, sys: 0.49 s, total: 2.57 s
         Wall time: 2.85 s

Now look at the memory usage and see that around a 1 Gb is being used::
  
  len(teio.vals) / 1e6
  clf()
  plot_cxctime(teio.times, teio.vals, '.', markersize=0.5)

Making a plot with 13 million points takes 5 to 10 seconds and some memory.
See what happens to memory when you clear the plot::

  clf()

Now let's get serious and fetch all the AORATE3 values (1 per second) for the mission after deleting the TEIO data::

    del teio
    time aorate3 = fetch.MSID('aorate3', '2000:001', '2010:001', filter_bad=True)
    Out[]: CPU times: user 38.83 s, sys: 7.43 s, total: 46.26 s
           Wall time: 60.10 s

We just fetched 300 million floats and now ``top`` should be showing some respectable memory usage::

  Cpu(s):  0.0%us,  0.1%sy,  0.0%ni, 99.7%id,  0.2%wa,  0.1%hi,  0.0%si,  0.0%st

    PID USER      PR  NI  VIRT  RES  SHR S %CPU %MEM    TIME+  COMMAND           
  14243 aca       15   0 6866m 6.4g  11m S  0.0 40.9   3:08.70 ipython            

If you try to make a simple scatter plot with 300 million points you will
make the machine very unhappy.  But we can do computations or make a histogram of
the distribution::

  clf()
  hist(log10(abs(aorate3.vals)+1e-15), log=True, bins=100)

.. image:: fetchplots/aorate3_hist.png

Rules of thumb: 

* 1 million is fast for plotting and analysis.
* 10 million is OK for plotting and fast for analysis.
* 300 million is OK for analysis, expect 30-60 seconds for any operation.
* Look before you leap, do smaller fetches first and check sizes.
* 5-minute stats are ~10 million so you are always OK.

Putting it all together
=======================

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

To do
======

* Add telemetry:

  - ACA header-3

* Add MSID method to determine exact time of mins or maxes
