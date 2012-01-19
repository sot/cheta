import numpy as np
import matplotlib.pyplot as plt
import Ska.engarchive.fetch as fetch
from Ska.Matplotlib import cxctime2plotdate, plot_cxctime
from Chandra.Time import DateTime
from matplotlib.dates import num2epoch, epoch2num

MIN_TSTART_UNIX = DateTime('1999:100').unix
MAX_TSTOP_UNIX = DateTime().unix + 1e7


def get_stat(t0, t1, npix):
    t0 = DateTime(t0)
    t1 = DateTime(t1)
    dt_days = t1 - t0

    if dt_days > npix:
        stat = 'daily'
    elif dt_days * (24 * 60 / 5) > npix:
        stat = '5min'
    else:
        stat = None
    return stat


class MsidPlot(object):
    def __init__(self, msid):
        self.fig = plt.gcf()
        self.ax = self.fig.gca()
        self.zoom = 4.0
        self.msid = msid
        self.msidname = self.msid.msid
        self.plot_mins = True
        self.tstart = self.msid.times[0]
        self.tstop = self.msid.times[-1]
        self.scaley = True

        self.ax.set_autoscale_on(True)
        self.draw_plot()
        self.ax.set_autoscale_on(False)
        self.ax.callbacks.connect('xlim_changed', self.xlim_changed)
        self.fig.canvas.mpl_connect('key_press_event', self.key_press)

    @property
    def npix(self):
        dims = self.ax.axesPatch.get_window_extent().bounds
        return int(dims[2] + 0.5)

    def key_press(self, event):
        if event.key in ['z', 'p'] and event.inaxes:
            x0, x1 = self.ax.get_xlim()
            dx = x1 - x0
            xc = event.xdata
            zoom = self.zoom if event.key == 'p' else 1.0 / self.zoom
            new_x1 = zoom * (x1 - xc) + xc
            new_x0 = new_x1 - zoom * dx
            tstart = max(num2epoch(new_x0), MIN_TSTART_UNIX)
            tstop = min(num2epoch(new_x1), MAX_TSTOP_UNIX)
            new_x0 = epoch2num(tstart)
            new_x1 = epoch2num(tstop)

            self.ax.set_xlim(new_x0, new_x1)
            self.ax.figure.canvas.draw_idle()
        elif event.key == 'm':
            for _ in range(len(self.ax.lines)):
                self.ax.lines.pop()
            self.plot_mins = not self.plot_mins
            print '\nPlotting mins and maxes is {}'.format(
                'enabled' if self.plot_mins else 'disabled')
            self.draw_plot()
        elif event.key == 'a':
            self.ax.set_autoscale_on(True)
            self.draw_plot()
            self.ax.set_autoscale_on(False)
        elif event.key == 'y':
            self.scaley = not self.scaley
            print 'Autoscaling y axis is {}'.format(
                'enabled' if self.scaley else 'disabled')
            self.draw_plot()
        elif event.key == '?':
            print """
Interactive MSID plot keys:

  a: autoscale for full data range in x and y
  m: toggle plotting of min/max values
  p: pan at cursor x
  y: toggle autoscaling of y-axis
  z: zoom at cursor x
  ?: print help
"""

    def xlim_changed(self, event):
        x0, x1 = self.ax.get_xlim()
        self.tstart = DateTime(num2epoch(x0), format='unix').secs
        self.tstop = DateTime(num2epoch(x1), format='unix').secs
        stat = get_stat(self.tstart, self.tstop, self.npix)

        if (self.tstart < self.msid.tstart or
            self.tstop > self.msid.tstop or
            stat != self.msid.stat):
            dt = self.tstop - self.tstart
            self.tstart -= dt / 4
            self.tstop += dt / 4
            self.msid = fetch.Msid(self.msidname, self.tstart, self.tstop,
                                   stat=stat)
        self.draw_plot()

    def draw_plot(self):
        for _ in range(len(self.ax.lines)):
            self.ax.lines.pop()

        # Force manual y scaling
        scaley = self.scaley and not self.ax.get_autoscaley_on()
        if scaley:
            ymin = None
            ymax = None
            ok = ((self.msid.times >= self.tstart) &
                  (self.msid.times <= self.tstop))

        if self.plot_mins and hasattr(self.msid, 'mins'):
            plot_cxctime(self.msid.times, self.msid.mins, '-c',
                         ax=self.ax, fig=self.fig)
            plot_cxctime(self.msid.times, self.msid.maxes, '-c',
                         ax=self.ax, fig=self.fig)
            if scaley:
                ymin = np.min(self.msid.mins[ok])
                ymax = np.max(self.msid.maxes[ok])

        plot_cxctime(self.msid.times, self.msid.vals, '-b',
                     ax=self.ax, fig=self.fig)

        if scaley:
            plotvals = self.msid.vals[ok]
            if ymin is None:
                ymin = np.min(plotvals)
            if ymax is None:
                ymax = np.max(plotvals)
            self.ax.set_ylim(ymin, ymax)

        self.ax.set_title(self.msid.MSID)
        if self.msid.unit:
            self.ax.set_ylabel(self.msid.unit)

        # Update the image object with our new data and extent
        self.ax.figure.canvas.draw_idle()


# if 'dat' not in globals():
#    dat = fetch.Msid('tephin', '2011:001', '2011:010')
# fig = plt.figure()
# ax = fig.add_subplot(1, 1, 1)
# MsidPlot('tephin')

# Connect for changing the view limits
# ax.callbacks.connect('xlim_changed', md.ax_update)

# plt.show()
