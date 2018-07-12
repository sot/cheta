Fix corruption of ephemeris files
=================================

The problem
-----------

From Joy ([ascds_help] mixed version ephem files in AP on Jul 5, 2018)::

  We were delivered an slightly incorrect ephemeris file last week.  It was allowed to go
  into AP after the FOT recreated it and got the same answer.  Now the FOT has found the
  error and created a good ephemeris file to replace the incorrect one.  I want to:

  1. Replace the incorrect ephemeris products in the archive, either by demoting the
  previous version N001, or by having SAP process ephem producing N002 products.

  2. Reprocess all obsids that used this particular ephem information in processing.  This
  step isn't strictly necessary because the error is in spacecraft location and is off by 7
  meters.  But I think we should correct the products now so the archive is completely
  consistent.

This meant that a second version of the day 2018:147 ephemeris file got into the archive
and was ingested by update_archive, resulting in the following archfiles::

  cd /proj/sot/ska/data/eng_archive/data/orbitephem0
  sqlite3 archfiles.db3
  sqlite>  select filename,year,doy,tstart,tstop,rowstart,rowstop,ascdsver,revision,date from archfiles where year=2018 and doy>130;
  orbitf642600305N001_eph0.fits.gz|2018|133|642600305.184|648734705.184|34648149|34668598|10.6.3|1|2018-06-12T23:22:18
  orbitf643205105N001_eph0.fits.gz|2018|140|643205105.184|649339505.184|34668598|34689047|10.6.3|1|2018-06-19T00:55:42
  orbitf643809905N001_eph0.fits.gz|2018|147|643809905.184|649944305.184|34689047|34709496|10.6.3|1|2018-06-28T16:30:52
  orbitf644414705N001_eph0.fits.gz|2018|154|644414705.184|650549105.184|34709496|34729945|10.6.3|1|2018-07-02T23:19:35
  orbitf643809905N002_eph0.fits.gz|2018|147|643809905.184|649944305.184|34729945|34750394|10.6.3|2|2018-07-06T16:53:38

The first sign of this were errors in processing like::

  /proj/sot/ska/data/eng_archive/logs/eng_archive.log
  ** ERROR - line 42777: /proj/sot/ska/arch/x86_64-linux_CentOS-6/lib/python2.7/site-packages/
  Ska.engarchive-3.43.1-py2.7.egg/Ska/engarchive/derived/orbit.py:97:
  RuntimeWarning: divide by zero encountered in true_divide

Fixing on HEAD
--------------

Log in as ``aldcroft`` (FIX THIS!) and do a dry run to confirm reasonable output.  The ``2018:130``
should be replaced with something around 20 days before the corruption::

  /proj/sot/ska/share/eng_archive/update_archive.py --content=lunarephem0 --truncate 2018:130 --data-root=/proj/sot/ska/data/eng_archive --dry-run

You can practice by copying everything to a local directory (anywhere convenient).  Note that compressing eng archive
files is not helpful because they are already compressed::

  mkdir data
  rsync -av --ignore=arch /proj/sot/ska/data/eng_archive/data/lunarephem0/ data/lunarephem0/

  # Set directories where fetch *reads*.  The flight /proj/sot/ska bit is needed for
  # reading telemetry to compute derived parameters, if you are doing dp_orbit1280 or
  # dp_pcad4 on the side.
  export ENG_ARCHIVE=${PWD}:/proj/sot/ska/data/eng_archive

  /proj/sot/ska/share/eng_archive/update_archive.py --content=lunarephem0 --truncate 2018:130 --data-root=.
  /proj/sot/ska/share/eng_archive/update_archive.py --content=lunarephem0 --data-root=. --max-lookback-time=100

  unset ENG_ARCHIVE  # Important!!

Now you can go for it.  There is always the NetApp snapshot in case of disaster::

  /proj/sot/ska/share/eng_archive/update_archive.py --content=lunarephem0 --truncate 2018:130 --data-root=/proj/sot/ska/data/eng_archive
  /proj/sot/ska/share/eng_archive/update_archive.py --content=lunarephem0 --data-root=/proj/sot/ska/data/eng_archive --max-lookback-time=100

You should see updates that look about right.  In particular you can see that about the right
number of days are added to the daily stats.

Now make sure it worked::

  ipython --matplotlib
  from Ska.engarchive import fetch
  dat = fetch.Msid('orbitephem0_x', DateTime() - 60, DateTime() + 100)
  dat.plot()

Now do the rest::

  /proj/sot/ska/share/eng_archive/update_archive.py --content=lunarephem1 --truncate 2018:130 --data-root=/proj/sot/ska/data/eng_archive
  /proj/sot/ska/share/eng_archive/update_archive.py --content=orbitephem0 --truncate 2018:130 --data-root=/proj/sot/ska/data/eng_archive
  /proj/sot/ska/share/eng_archive/update_archive.py --content=orbitephem1 --truncate 2018:130 --data-root=/proj/sot/ska/data/eng_archive
  /proj/sot/ska/share/eng_archive/update_archive.py --content=solarephem0 --truncate 2018:130 --data-root=/proj/sot/ska/data/eng_archive
  /proj/sot/ska/share/eng_archive/update_archive.py --content=solarephem1 --truncate 2018:130 --data-root=/proj/sot/ska/data/eng_archive
  /proj/sot/ska/share/eng_archive/update_archive.py --content=dp_orbit1280 --truncate 2018:130 --data-root=/proj/sot/ska/data/eng_archive
  /proj/sot/ska/share/eng_archive/update_archive.py --content=dp_pcad4 --truncate 2018:130 --data-root=/proj/sot/ska/data/eng_archive

  /proj/sot/ska/share/eng_archive/update_archive.py --content=lunarephem1 --data-root=/proj/sot/ska/data/eng_archive --max-lookback-time=100
  /proj/sot/ska/share/eng_archive/update_archive.py --content=solarephem0 --data-root=/proj/sot/ska/data/eng_archive --max-lookback-time=100
  /proj/sot/ska/share/eng_archive/update_archive.py --content=solarephem1 --data-root=/proj/sot/ska/data/eng_archive --max-lookback-time=100
  /proj/sot/ska/share/eng_archive/update_archive.py --content=orbitephem0 --data-root=/proj/sot/ska/data/eng_archive --max-lookback-time=100
  /proj/sot/ska/share/eng_archive/update_archive.py --content=orbitephem1 --data-root=/proj/sot/ska/data/eng_archive --max-lookback-time=100
  /proj/sot/ska/share/eng_archive/update_archive.py --content=dp_orbit1280 --data-root=/proj/sot/ska/data/eng_archive --max-lookback-time=100
  /proj/sot/ska/share/eng_archive/update_archive.py --content=dp_pcad4 --data-root=/proj/sot/ska/data/eng_archive --max-lookback-time=100

You can test a few, but if these go through with no errors then everything should be OK.
particular the ``dp_orbit1280`` and ``dp_pcad4`` processing will give errors if the other products are not consistent.

Fixing on GRETA
---------------

Log in as ``SOT`` and rsync the files over::

  cd /proj/sot/ska/data/eng_archive/data

  rsync -av --dry-run --exclude=arch aldcroft@ccosmos:/proj/sot/ska/data/eng_archive/data/orbitephem0/ orbitephem0/

  rsync -av --exclude=arch aldcroft@ccosmos:/proj/sot/ska/data/eng_archive/data/orbitephem0/ orbitephem0/
  rsync -av --exclude=arch aldcroft@ccosmos:/proj/sot/ska/data/eng_archive/data/orbitephem1/ orbitephem1/
  rsync -av --exclude=arch aldcroft@ccosmos:/proj/sot/ska/data/eng_archive/data/lunarephem0/ lunarephem0/
  rsync -av --exclude=arch aldcroft@ccosmos:/proj/sot/ska/data/eng_archive/data/lunarephem1/ lunarephem1/
  rsync -av --exclude=arch aldcroft@ccosmos:/proj/sot/ska/data/eng_archive/data/solarephem0/ solarephem0/
  rsync -av --exclude=arch aldcroft@ccosmos:/proj/sot/ska/data/eng_archive/data/solarephem1/ solarephem1/
  rsync -av --exclude=arch aldcroft@ccosmos:/proj/sot/ska/data/eng_archive/data/dp_orbit1280/ dp_orbit1280/
  rsync -av --exclude=arch aldcroft@ccosmos:/proj/sot/ska/data/eng_archive/data/dp_orbit1280/ dp_pcad4/
