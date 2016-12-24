#!/usr/bin/env python
"""
Perform file transfer functions to get files over to GRETA network.

This is normally run as a cron job.
"""

if __name__ == '__main__':
    from Ska.engarchive import transfer_stage
    transfer_stage.main()
