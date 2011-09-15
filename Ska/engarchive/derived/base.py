from Chandra.Time import DateTime
import Ska.engarchive.fetch_eng as fetch_eng
import Ska.Numpy
import numpy as np
 
__all__ = ['MNF_TIME', 'times_indexes', 'DerivedParameter']

MNF_TIME = 0.25625              # Minor Frame duration (seconds)

def times_indexes(start, stop, dt):
    index0 = DateTime(start).secs // dt
    index1 = DateTime(stop).secs // dt + 1
    indexes = np.arange(index0, index1, dtype=np.int64)
    times = indexes * dt
    return times, indexes

class DerivedParameter(object):
    max_gap = 66.0              # Max allowed data gap (seconds)

    def calc(self, data):
        raise NotImplementedError

    def fetch(self, start, stop):
        dataset = fetch_eng.MSIDset(self.rootparams, start, stop)

        # Translate state codes "ON" and "OFF" to 1 and 0, respectively.
        for data in dataset.values():
            if (data.vals.dtype.name == 'string24'
                and set(data.vals) == set(('ON ', 'OFF'))):
                data.vals = np.where(data.vals == 'OFF', np.int8(0), np.int8(1))
                    
        times, indexes = times_indexes(start, stop, self.timestep)
        bads = np.zeros(len(times), dtype=np.bool)  # All data OK (false)

        for msidname, data in dataset.items():
            idxs = Ska.Numpy.interpolate(np.arange(len(data.times)),
                                         data.times, times, method='nearest')
            
            # Loop over data attributes like "bads", "times", "vals" etc and
            # perform near-neighbor interpolation by indexing
            for attr in data.colnames:
                vals = getattr(data, attr)
                if vals is not None:
                    setattr(data, attr, vals[idxs])

            bads = bads | data.bads
            # Reject near-neighbor points more than max_gap secs from available data
            bads = bads | (abs(data.times - times) > self.max_gap)

        dataset.times = times
        dataset.bads = bads
        dataset.indexes = indexes

        return dataset

    def __call__(self, start, stop):
        dataset = fetch_eng.MSIDset(self.rootparams, start, stop, filter_bad=True)

        # Translate state codes "ON" and "OFF" to 1 and 0, respectively.
        for data in dataset.values():
            if (data.vals.dtype.name == 'string24'
                and set(data.vals) == set(('ON ', 'OFF'))):
                data.vals = np.where(data.vals == 'OFF', np.int8(0), np.int8(1))
                    
        dataset.interpolate(dt=self.timestep)

        return self.calc(dataset)

    @property
    def mnf_step(self):
        return int(round(self.timestep / MNF_TIME))
    

class MockMSIDset(object):
    pass

class DerivedParameterTime(DerivedParameter):
    content = 'time'
    def calc(self, dataset):
        return dataset.times

    def fetch(self, start, stop):
        dataset = MockMSIDset()
                    
        times, indexes = times_indexes(start, stop, self.timestep)
        bads = np.zeros(len(times), dtype=np.bool)  # All data OK (false)

        dataset.times = times
        dataset.bads = bads
        dataset.indexes = indexes

        return dataset

class DP_TIME1(DerivedParameterTime):
    timestep = 0.25625

class DP_TIME128(DerivedParameterTime):
    timestep = 32.8
