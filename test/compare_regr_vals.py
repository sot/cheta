#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst

import optparse
import pickle

import numpy as np


def get_options():
    parser = optparse.OptionParser()
    parser.add_option("--root", default="regr_vals", help="Input prefix")
    return parser.parse_args()


opt, args = get_options()

flight = pickle.load(open(opt.root + ".flight.pkl", "rb"))
test = pickle.load(open(opt.root + ".test.pkl", "rb"))

msids = (
    "1crat",
    "fptemp_11",
    "orbitephem0_x",
    "sim_z",
    "tephin",
    "cvcductr",
)  # , 'dp_dpa_power')
attrs = (
    "times",
    "vals",
    "quals",
    "stds",
    "mins",
    "maxes",
    "means",
    "p01s",
    "p05s",
    "p16s",
    "p50s",
    "p84s",
    "p95s",
    "p99s",
)

all_ok = True

for msid in msids:
    for stat in ("dat", "dat5", "datd"):
        if msid == "orbitephem0_x" and stat in ("dat5", "datd"):
            # The overlaps and CXC L0 archive oddities related to ephemeris files mean
            # that regenerating the 5-min and daily stats for past data will not match
            # the values from the real flight processing. Skip those.
            continue
        for attr in attrs:
            try:
                f = flight[msid][stat]
                t = test[msid][stat]
            except KeyError:
                print(
                    "MSID={} stat={} missing in flight or test data".format(msid, stat)
                )
                all_ok = False
                continue
            if attr not in f:
                continue
            if len(f[attr]) != len(t[attr]):
                print(
                    f"[NOT OK] {msid} {stat}: Length mismatch: {len(f[attr])} {len(t[attr])}"
                )
                all_ok = False
                continue
            if attr == "quals":
                ok = f["quals"] == t["quals"]
            else:
                ok = np.allclose(f[attr], t[attr])
            status = "OK" if ok else "NOT OK"
            all_ok &= ok
            print(f"[{status}] {msid} {stat}")

print(f"All OK: {ok}")
