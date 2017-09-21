#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Update the engineering archive database.  Normally this
includes new telemetry from the CXC archive and updating
the statistics and derived parameter values.  It also includes
facilities for various eng archive maintenance activities.

This is normally run as a cron job.
"""

if __name__ == '__main__':
    from Ska.engarchive import update_archive
    update_archive.main()
