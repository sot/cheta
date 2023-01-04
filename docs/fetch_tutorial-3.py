from cheta import fetch_eng as fetch
from cheta.utils import logical_intervals
import matplotlib.pyplot as plt
sa_temps = fetch.Msid('TSAPYT','2010:001',stat='5min')
roll = fetch.Msid('ROLL','2010:001',stat='5min')
roll_off_nom = (roll.vals > 5) & (roll.vals < 10)
off_nom_intervals = logical_intervals(roll.times, roll_off_nom)
sa_temps_off_nom = sa_temps.select_intervals(off_nom_intervals, copy=True)

plt.figure(figsize=(6, 4), dpi=75)
sa_temps.plot('.r')
sa_temps_off_nom.plot('.b')
plt.grid()
plt.title('Solar array temps at off-nominal roll 5 - 10 degrees')