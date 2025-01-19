=======================
Cheta Telemetry Archive
=======================
.. include:: references.rst

The cheta telemetry archive is a suite of tools and data products that provide the
majority of all Chandra engineering telemetry since the start of the mission (1999:204).
This includes about 6300 MSIDs which are taken directly from CXC Level-0 (L0) telemetry
decom, plus numerous :ref:`pseudo-MSIDs <pseudo-msids>` that are derived from the
primary engineering telemetry.

The telemetry are stored in a way that allows for very fast retrieval into memory.
Typical retrieval rates are around 10^7 samples/sec, so for an MSID sampled once per
second this translates to about 3 sec per year of data.

The data archive includes:

- Full time-resolution data: time, value, quality.
- 5-minute statistics: min, max, mean, sampled value, number of samples.
- Daily statistics: min, max, mean, sampled value, standard deviation, percentiles (1,
  5, 16, 50, 84, 95, 99), number of samples.

The cheta package includes:

- Powerful class to fetch, manipulate, and plot telemetry data.
- Tools to perform a daily update of the primary archive on HEAD from the CXC L0 archive.
- Tools to synchronize a local archive of telemetry data from the primary archive.

.. toctree::
   :hidden:

   fetch_tutorial
   pseudo_msids
   api/index



