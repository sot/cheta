import Ska.engarchive.fetch_eng as fetch_eng
import numpy as np
 
class DerivedParameter(object):
    def calc(self,data):
        raise NotImplementedError

    def __call__(self, start, stop):
        data = fetch_eng.MSIDset(self.rootparams, start, stop, filter_bad=True)
        for name in self.rootparams:
            if isinstance(data[name].vals[0],(str,unicode)):
                if 'ON' in data[name].vals[0] or 'OFF' in data[name].vals[0]:
                    data[name].vals = np.array([d.strip() == 'ON' for d in data[name].vals])
                    
        data.interpolate(dt=self.timestep)

        return self.calc(data)

