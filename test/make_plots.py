#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst

# Make a few plots for a sanity check of test archive correctness
# run in pylab

import os

import matplotlib.pyplot as plt
from ska_matplotlib import plot_cxctime

import cheta.fetch_sci as fetch

print("Fetch file is", fetch.__file__)
print("ENG_ARCHIVE is", os.environ["ENG_ARCHIVE"])

msids = ("1crat", "fptemp_11", "orbitephem0_x", "sim_z", "tephin")
rootdir = os.path.dirname(__file__)

for ifig, msid in enumerate(msids):
    plt.figure(ifig + 1)
    plt.clf()
    dat = fetch.MSID(msid, "2024:002", "2024:008", filter_bad=True)
    dat5 = fetch.MSID(msid, "2024:002", "2024:008", stat="5min")
    datday = fetch.MSID(msid, "2024:002", "2024:008", stat="daily")
    plt.subplot(3, 1, 1)
    plot_cxctime(dat.times, dat.vals, "-b")
    plt.grid()
    plt.subplot(3, 1, 2)
    plot_cxctime(dat5.times, dat5.means, "-r")
    plt.grid()
    plt.subplot(3, 1, 3)
    plot_cxctime(datday.times, datday.means, "-c")
    plt.grid()
    plt.savefig(os.path.join(rootdir, "plot_{0}.png".format(msid)))
