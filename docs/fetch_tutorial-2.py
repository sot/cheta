from cheta import fetch
import matplotlib.pyplot as plt
from kadi import events

plt.figure(figsize=(6, 4), dpi=75)

aorate2 = fetch.Msid('aorate2', '2011:001', '2011:002')
events.manvrs.interval_pad = (600, 300)  # Pad before, after each maneuver (seconds)
aorate2.remove_intervals(events.manvrs)
aorate2.iplot('.')

plt.tight_layout()