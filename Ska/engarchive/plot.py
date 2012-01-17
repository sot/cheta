import matplotlib.pyplot as plt
import Ska.engarchive.fetch as fetch
from Ska.Matplotlib import cxctime2plotdate
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
    def __init__(self, msid,
                 start='2011:001', stop='2011:010',
                 fig=None, ax=None):
        self.fig = fig or plt.gcf()
        self.ax = ax or self.fig.gca()
        self.fig.autofmt_xdate()
        self.zoom = 4.0

        if isinstance(msid, fetch.MSID):
            self.msid = msid
        else:
            stat = get_stat(start, stop, self.npix)
            self.msid = fetch.Msid(msid, start, stop, stat=stat)

        self.msidname = self.msid.msid
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
            # print 'x0, x1', x0, x1, num2epoch(x0), num2epoch(x1)
            tstart = max(num2epoch(new_x0), MIN_TSTART_UNIX)
            tstop = min(num2epoch(new_x1), MAX_TSTOP_UNIX)
            new_x0 = epoch2num(tstart)
            new_x1 = epoch2num(tstop)
            # print 'x0, x1', x0, x1, num2epoch(x0), num2epoch(x1)

            self.ax.set_xlim(new_x0, new_x1)
            self.ax.figure.canvas.draw_idle()

    def xlim_changed(self, event):
        x0, x1 = self.ax.get_xlim()
        tstart = DateTime(num2epoch(x0), format='unix').secs
        tstop = DateTime(num2epoch(x1), format='unix').secs
        stat = get_stat(tstart, tstop, self.npix)
        print 'XLIM', x0, x1

        if (tstart < self.msid.tstart or
            tstop > self.msid.tstop or
            stat != self.msid.stat):
            dt = tstop - tstart
            tstart -= dt / 4
            tstop += dt / 4
            print 'Fetching', DateTime(tstart).date, DateTime(tstop).date
            self.msid = fetch.Msid(self.msidname, tstart, tstop,
                                   stat=stat)
            self.ax.set_autoscale_on(False)
            for _ in range(len(self.ax.lines)):
                self.ax.lines.pop()
            self.draw_plot()

    def draw_plot(self):
        self.plot_dates = cxctime2plotdate(self.msid.times)
        if hasattr(self.msid, 'p84s'):
            self.ax.plot_date(self.plot_dates, self.msid.p84s, '-m')
            self.ax.plot_date(self.plot_dates, self.msid.p16s, '-m')
        if hasattr(self.msid, 'mins'):
            self.ax.plot_date(self.plot_dates, self.msid.mins, '-c')
            self.ax.plot_date(self.plot_dates, self.msid.maxes, '-c')
        self.ax.plot_date(self.plot_dates, self.msid.vals, '-b')

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
