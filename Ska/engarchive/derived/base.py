import Ska.engarchive.fetch_eng as fetch_eng
import numpy as np
 
class DerivedParameter(object):
    def calc(self,data):
        raise NotImplementedError

    def __call__(self, start, stop):
        dataset = fetch_eng.MSIDset(self.rootparams, start, stop, filter_bad=True)

        # Translate state codes "ON" and "OFF" to 1 and 0, respectively.
        for data in dataset.values():
            if (data.vals.dtype.name == 'string24'
                and set(data.vals) == set(('ON ', 'OFF'))):
                data.vals = np.where(data.vals == 'OFF', 0, 1)
                    
        dataset.interpolate(dt=self.timestep)

        return self.calc(dataset)

