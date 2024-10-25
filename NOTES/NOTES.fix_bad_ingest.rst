Fixing bad ingest
==================

These notes document how to fix the cheta archive if a bad CXC archive file has
been ingested and then the CXC archive is subsequently repaired.

Case story
----------
Around 2021:118 there was a bad ACIS DEA HK file put into the CXC archive.
See thread "Gap in ACIS housekeeping telemetry" from May 1, 2021. The bad file
was less than a second long and this messed up CXC archiving. They fixed this
after a few days with a new file of the same name. The cheta archive had already
ingested the bad file, so these notes document how to fix things.

Rsync with snapshot
--------------------

Here we use the NetApp back-up to roll back the files to before the bad ingest
and start over.

This is generally the preferred method since it is simpler. Note that users
may still need to truncate (see the `GRETA and users`_ section.)

The example in this section is from another bad file ingested June 11, 2021.
See email ``Fwd: [operators] 2 small files to replace in archive`` and
``Ska telemetry archive (IMPORTANT if you have a local archive)``.

HEAD
^^^^

On-the-side update
~~~~~~~~~~~~~~~~~~
This is preferred for smaller content directories like ``acisdeahk``::

  # Get the data files from before the bad ingest
  cd ~/tmp
  mkdir cheta-acisdeahk
  cd cheta-acisdeahk
  mkdir data
  mkdir sync
  rsync -av /proj/sot/.snapshot/weekly.2024-10-20_0015/ska/data/eng_archive/data/acisdeahk data/
  rsync -av /proj/sot/.snapshot/weekly.2024-10-20_0015/ska/data/eng_archive/sync/acisdeahk sync/
  
  # Reprocess on the side
  export ENG_ARCHIVE=$PWD
  cheta_update_server_archive --data-root=$PWD --content=acisdeahk
  cheta_update_server_sync --data-root=$PWD --content=acisdeahk
  
  # Copy new files to /proj/sot/ska/data/eng_archive
  cd /proj/sot/ska/data/eng_archive
  cp -rp ~/tmp/cheta-acisdeahk/data/acisdeahk data/acisdeahk-new
  cp -rp ~/tmp/cheta-acisdeahk/sync/acisdeahk sync/acisdeahk-new
    
  # "Atomic" move of new directories to flight
  mv data/acisdeahk{,-2024-10-25}; mv data/acisdeahk{-new,}
  mv sync/acisdeahk{,-2024-10-25}; mv sync/acisdeahk{-new,}

In-place update
~~~~~~~~~~~~~~~
This is preferred if the bad content directory is very large (well over a Gb).

Find the last snapshot before the bad ingest::

  ls /proj/sot/.snapshot/

  rsync -av /proj/sot/.snapshot/weekly.2021-06-06_0015/ska/data/eng_archive/data/acisdeahk/ \
            /proj/sot/ska/data/eng_archive/data/acisdeahk/
  rsync -av --delete /proj/sot/.snapshot/weekly.2021-06-06_0015/ska/data/eng_archive/sync/acisdeahk/ \
            /proj/sot/ska/data/eng_archive/sync/acisdeahk/

The ``--delete`` flag is important in the second ``rsync`` because the previous
sync directories need to be removed.

Now update the archive. It's most reliable to do the full-update with the cron command::

  /proj/sot/ska3/flight/bin/skare task_schedule3.pl -config eng_archive/task_schedule.cfg

GRETA
^^^^^

As the ``SOT`` user::

   cd /proj/sot/ska/data/eng_archive
   rsync -av <user>@ccosmos.cfa.harvard.edu:/proj/sot/ska/data/eng_archive/data/acisdeahk/ \
             data/acisdeahk/
   rm data/acisdeahk/5min/last_date_id
   rm data/acisdeahk/daily/last_date_id

Truncate and rebuild
--------------------

This may be needed if more than 2 weeks went by since the problem.

On HEAD
^^^^^^^
First we truncate the data files to a time about 2 days before the bad file.
Start by defining the content type::

  export CONTENT=acisdeahk # set to value as seen in $SKA/data/eng_archive/data

An optional first step is to make a backup of the
``$SKA/data/eng_archive/data/$CONTENT`` directory. Since we have NetApp backups
this is not absolutely required. To be extra careful we could also make a copy
of that data directory and do all the processing on the side. This is just a bit
painful for some of the content types that might be 30 Gb large.

::

  # Truncate to a date that is 1-2 days before bad file start. Practice with the
  # dry-run flag and then do it for real.
  cheta_update_server_archive --content=$CONTENT \
    --data-root=$SKA/data/eng_archive --truncate=2021:117 --dry-run

  # Now re-run the standard ingest
  cheta_update_server_archive --content=$CONTENT \
    --data-root=$SKA/data/eng_archive

Next fix up the sync archive.

::

  mv $SKA/data/eng_archive/sync/${CONTENT} \
     $SKA/data/eng_archive/sync/${CONTENT}-bak

  # Choose a start date about 60 days before the truncate date.
  cheta_update_server_sync --content=$CONTENT --date-start=2021:057 \
    --sync-root=$SKA/data/eng_archive


GRETA and users
^^^^^^^^^^^^^^^
On either a local laptop or on GRETA (``SOT@cheru``) do the following::

  # Do first with --dry-run and then for real
  cheta_update_server_archive --content=acisdeahk \
    --data-root=$SKA/data/eng_archive --truncate=2021:117 --dry-run

  cheta_sync --content=acisdeahk


HEAD cleanup
^^^^^^^^^^^^
::

  rm -rf $SKA/data/eng_archive/sync/${CONTENT}-bak
