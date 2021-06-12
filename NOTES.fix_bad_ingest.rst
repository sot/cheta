Fixing bad ingest
==================

These notes document how to fix the cheta archive if a bad CXC archive file has
been ingested and then the CXC archive is subsequently repaired.

*IMPORTANT: Before going any further, consider just using the NetApp back-up to roll
back the files to before the bad ingest and starting over.*

Case story
----------
Around 2021:118 there was a bad ACIS DEA HK file put into the CXC archive.
See thread "Gap in ACIS housekeeping telemetry" from May 1, 2021. The bad file
was less than a second long and this messed up CXC archiving. They fixed this
after a few days with a new file of the same name. The cheta archive had already
ingested the bad file, so these notes document how to fix things.

On HEAD
-------
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
---------------
On either a local laptop or on GRETA (``SOT@cheru``) do the following::

  # Do first with --dry-run and then for real
  cheta_update_server_archive --content=acisdeahk \
    --data-root=$SKA/data/eng_archive --truncate=2021:117 --dry-run

  cheta_sync --content=acisdeahk


HEAD cleanup
------------
::

  rm -rf $SKA/data/eng_archive/sync/${CONTENT}-bak
