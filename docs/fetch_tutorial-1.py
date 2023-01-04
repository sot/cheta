from cheta import fetch
import matplotlib.pyplot as plt
plt.figure(figsize=(6, 4), dpi=75)

aorate2 = fetch.Msid('aorate2', '2011:001', '2011:002')
aorate2.iplot()

from kadi import events
aorate2.select_intervals(events.manvrs)
aorate2.plot('.r')
plt.tight_layout()