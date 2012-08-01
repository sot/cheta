"""Check that the 5min and daily stats are consistent between two different
builds of the stats archive.
"""


import numpy as np
import tables
import matplotlib.pyplot as plt
from Ska.engarchive import fetch

stat ='5min'  # or set to 'daily'
IMAX = {'daily': 4000, '5min': 10000}[stat]

content = fetch.content

content_types = sorted(set(content.values()))

def getstats(filename):
    try:
        h5f = tables.openFile(filename, 'r')
        if len(h5f.root.data) < IMAX:
            raise ValueError('Not enough rows')
        means = h5f.root.data.col('mean')[:IMAX]
        vals = h5f.root.data.col('val')[:IMAX]
        mins = h5f.root.data.col('min')[:IMAX]
        maxes = h5f.root.data.col('max')[:IMAX]
    except Exception as err:
        raise ValueError(err)
    finally:
        h5f.close()
    return means, vals, mins, maxes

for content_type in reversed(content_types):
    if content_type.startswith('dp_therm') or content_type in ('pcad13eng', 'pcad8eng', 'pcad7eng'):
        # These have known and OK issues.
        print 'Skipping', content_type
        continue
    print content_type
    msids = [k for k, v in content.items() if v == content_type]

    for msid in msids:
        # print msid,
        h5f = '/proj/sot/ska/data/eng_archive/data/{}/{}/{}.h5'.format(content[msid], stat, msid.upper())
        h5n = '/proj/sot/ska/tmp/eng_archive/data/{}/{}/{}.h5'.format(content[msid], stat, msid.upper())
        try:
            fmeans, fvals, fmins, fmaxes = getstats(h5f)  # flight
            nmeans, nvals, nmins, nmaxes = getstats(h5n)  # new
        except Exception as err:
            continue
        means_med = abs(np.median(fmeans))
        range = max([means_med, np.max(fmaxes) - np.min(fmins)])
        dvals = np.max(np.abs(nvals - fvals) / range)
        dmeans = np.max(np.abs(nmeans - fmeans) / range)
        dmaxes = np.max(np.abs(nmaxes - fmaxes) / range)
        dmins = np.max(np.abs(nmins - fmins) / range)
        if dmeans > 0.005 or dvals > 1e-5 or dmaxes > 1e-5 or dmins > 1e-5:
            print '{:14s} {:.6f} {:.8f} {:.8f} {:.8f} {} {}'.format(msid,
                dmeans, dvals, dmins, dmaxes, means_med, range)

def plot_stats(msid,
               nmeans, nvals, nmins, nmaxes,
               fmeans, fvals, fmins, fmaxes):
    plt.figure(1, figsize=(10, 8))
    plt.clf()

    plt.subplot(4, 2, 1)
    plt.hist(fvals, bins=50)
    plt.title('vals')

    plt.subplot(4, 2, 2)
    plt.hist(nvals - fvals, bins=50)
    plt.title('delta vals')

    plt.subplot(4, 2, 3)
    plt.hist(fmeans, bins=50)
    plt.title('means')

    plt.subplot(4, 2, 4)
    plt.hist(nmeans - fmeans, bins=50)
    plt.title('delta means')

    plt.subplot(4, 2, 5)
    plt.hist(fmins, bins=50)
    plt.title('mins')

    plt.subplot(4, 2, 6)
    plt.hist(nmins - fmins, bins=50)
    plt.title('delta mins')

    plt.subplot(4, 2, 7)
    plt.hist(fmaxes, bins=50)
    plt.title('maxes')

    plt.subplot(4, 2, 8)
    plt.hist(nmaxes - fmaxes, bins=50)
    plt.title('delta maxes')

    plt.tight_layout()
    plt.savefig('stats_plots/{}.png'.format(msid))
    
