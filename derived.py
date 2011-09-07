import Ska.engarchive.fetch_eng as fetch_eng
import numpy as np

# no zone 21,22,56,70-74?

# See PEP8 http://www.python.org/dev/peps/pep-0008/

# In [1]: import Ska.engarchive.fetch_eng as fetch
# In [2]: dats = fetch.MSIDset(['tephin', '5ephint'], '2011:100', '2011:105')
# In [3]: dats.interpolate(dt=8.2)
# In [5]: dats['tephin'].times[:40] - dats['tephin'].times[0]
# Out[5]: 
# array([   0.        ,    0.        ,    0.        ,   32.80000168,
#          32.80000168,   32.80000168,   32.80000168,   65.60000342,
#          65.60000342,   65.60000342,   65.60000342,   98.4000051 ,
#          98.4000051 ,   98.4000051 ,   98.4000051 ,  131.20000678,
#         ...
#         295.20001531,  295.20001531,  295.20001531,  328.00001699])
# In [6]: dats.times[:40] - dats['tephin'].times[0]
# Out[6]: 
# array([  -6.59606242,    1.60393757,    9.80393755,   18.00393754,
#          26.20393753,   34.40393752,   42.60393751,   50.80393749,
#          59.00393748,   67.20393747,   75.40393746,   83.60393745,
#         ...
#         288.60393715,  296.80393714,  305.00393713,  313.20393711])

def get_data_old(rootparams, t1, t2, stat):
    if stat:
        data = fetch_eng.MSIDset(rootparams, t1, t2, stat=stat)
    else:
        data = fetch_eng.MSIDset(rootparams, t1, t2, filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    return data

def get_data(rootparams, t1, t2):
    data = fetch_eng.MSIDset(rootparams, t1, t2, filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    return data


class DerivedParam(object):
    def calc(self, data):
        raise NotImplementedError

    def __call__(self, start, stop):
        data = fetch_eng.MSIDset(rootparams, start, stop, filter_bad=True)
        # timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
        data.interpolate(dt=self.timestep)

        return self.calc(data)

class CalcEE_AXIAL(DerivedParameter):
    rootparams = ['OHRTHR58', 'OHRTHR12', 'OHRTHR36', 'OHRTHR56', 'OHRTHR57',
                  'OHRTHR55', 'OHRTHR35', 'OHRTHR37', 'OHRTHR34', 'OHRTHR13',
                  'OHRTHR10', 'OHRTHR11']
    timestep = 1 # minor frames

    def calc(self, data):
        HYPAVE = (data['OHRTHR12'].vals + data['OHRTHR13'].vals + data['OHRTHR36'].vals
                  + data['OHRTHR37'].vals + data['OHRTHR57'].vals + data['OHRTHR58'].vals) / 6.0
        PARAVE = (data['OHRTHR10'].vals + data['OHRTHR11'].vals + data['OHRTHR34'].vals
                  + data['OHRTHR35'].vals + data['OHRTHR55'].vals + data['OHRTHR56'].vals) / 6.0
        HAAG = PARAVE - HYPAVE
        DTAXIAL = np.abs(1.0 * HAAG)
        EE_AXIAL = DTAXIAL * 0.0034
        return (EE_AXIAL, data.times)

#-----------------------------------------------
def calcEE_AXIAL(t1, t2, stat=None):
    """Calculate axial contribution to encircled energy.
    """
    rootparams = ['OHRTHR58', 'OHRTHR12', 'OHRTHR36', 'OHRTHR56', 'OHRTHR57',
                  'OHRTHR55', 'OHRTHR35', 'OHRTHR37', 'OHRTHR34', 'OHRTHR13',
                  'OHRTHR10', 'OHRTHR11']
    data = get_data(rootparams, t1, t2)
    HYPAVE = (data['OHRTHR12'].vals + data['OHRTHR13'].vals + data['OHRTHR36'].vals
              + data['OHRTHR37'].vals + data['OHRTHR57'].vals + data['OHRTHR58'].vals) / 6.0
    PARAVE = (data['OHRTHR10'].vals + data['OHRTHR11'].vals + data['OHRTHR34'].vals
              + data['OHRTHR35'].vals + data['OHRTHR55'].vals + data['OHRTHR56'].vals) / 6.0
    HAAG = PARAVE - HYPAVE
    DTAXIAL = np.abs(1.0 * HAAG)
    EE_AXIAL = DTAXIAL * 0.0034
    return (EE_AXIAL, data.times)


#-----------------------------------------------
def calcEE_BULK(t1,t2,*args):
    derrparam = 'EE_BULK'
    eqnparams = ['P_SUM','EE_BULK','DTBULK','HMCSAVE','H_SUM','CAP_SUM']
    rootparams = ['OHRTHR10','OHRTHR58','OHRTHR52','OHRTHR53','OHRTHR56','OHRTHR57','OHRTHR54','OHRTHR55','OHRTHR12','OHRTHR35','OHRTHR11','OHRTHR08','OHRTHR09','OHRTHR31','OHRTHR33','OHRTHR34','OHRTHR13','OHRTHR36','OHRTHR37']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    P_SUM = data['OHRTHR10'].vals+data['OHRTHR11'].vals+data['OHRTHR34'].vals+data['OHRTHR35'].vals+data['OHRTHR55'].vals+data['OHRTHR56'].vals
    H_SUM = data['OHRTHR12'].vals+data['OHRTHR13'].vals+data['OHRTHR36'].vals+data['OHRTHR37'].vals+data['OHRTHR57'].vals+data['OHRTHR58'].vals
    CAP_SUM = data['OHRTHR08'].vals+data['OHRTHR09'].vals+data['OHRTHR31'].vals+data['OHRTHR33'].vals+data['OHRTHR52'].vals+data['OHRTHR53'].vals+data['OHRTHR54'].vals
    HMCSAVE = (CAP_SUM+P_SUM+H_SUM)/19.0
    DTBULK = np.abs(1.0*HMCSAVE-69.8)
    EE_BULK = DTBULK*0.0267
    return (EE_BULK,data['OHRTHR10'].times)


#-----------------------------------------------
def calcEE_DIAM(t1,t2,*args):
    derrparam = 'EE_DIAM'
    eqnparams = ['VAL2','VAL1','EE_DIAM','DTDIAM']
    rootparams = ['OHRMGRD6','OHRMGRD3']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VAL2 = np.abs(1.0*data['OHRMGRD6'].vals)
    VAL1 = np.abs(1.0*data['OHRMGRD3'].vals)
    DTDIAM = (VAL1>=VAL2)*VAL1+(VAL1<VAL2)*VAL2
    EE_DIAM = DTDIAM*0.401
    return (EE_DIAM,data['OHRMGRD6'].times)


#-----------------------------------------------
def calcEE_RADIAL(t1,t2,*args):
    derrparam = 'EE_RADIAL'
    eqnparams = ['HARG','DTRADIAL','CAPIAVE','CAPOAVE','EE_RADIAL']
    rootparams = ['OHRTHR52','OHRTHR53','OHRTHR54','OHRTHR31','OHRTHR09','OHRTHR08','OHRTHR33']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    CAPIAVE = (data['OHRTHR09'].vals+data['OHRTHR53'].vals+data['OHRTHR54'].vals)/3
    CAPOAVE = (data['OHRTHR08'].vals+data['OHRTHR31'].vals+data['OHRTHR33'].vals+data['OHRTHR52'].vals)/4
    HARG = CAPOAVE-CAPIAVE
    DTRADIAL = np.abs(1.0*HARG)
    EE_RADIAL = DTRADIAL*0.0127
    return (EE_RADIAL,data['OHRTHR52'].times)


#-----------------------------------------------
def calcEE_THERM(t1,t2,*args):
    # derrparam = 'EE_THERM'
    # eqnparams = ['DTRADIAL','CAPIAVE','DTDIAM','P_SUM','EE_BULK','VAL2','HARG','CAPOAVE','DTBULK','EE_RADIAL','EE_AXIAL','H_SUM','DTAXIAL','PARAVE','EE_DIAM','HYPAVE','EE_THERM','VAL1','HMCSAVE','HAAG','CAP_SUM']
    # rootparams = ['OHRTHR37','OHRTHR58','OHRMGRD6','OHRMGRD3','OHRTHR35','OHRTHR52','OHRTHR53','OHRTHR56','OHRTHR57','OHRTHR54','OHRTHR55','OHRTHR12','OHRTHR36','OHRTHR08','OHRTHR09','OHRTHR31','OHRTHR33','OHRTHR34','OHRTHR13','OHRTHR10','OHRTHR11']
    (EE_RADIAL,times) = calcEE_RADIAL(t1,t2,args[0])
    (EE_AXIAL,times) = calcEE_AXIAL(t1,t2,args[0])
    (EE_DIAM,times) = calcEE_DIAM(t1,t2,args[0])
    (EE_BULK,times) = calcEE_BULK(t1,t2,args[0])
    EE_THERM = (EE_BULK+EE_AXIAL+EE_RADIAL+EE_DIAM)
    return (EE_THERM,times)


#-----------------------------------------------
def calcHAAG(t1,t2,*args):
    derrparam = 'HAAG'
    eqnparams = ['HYPAVE','PARAVE','HAAG']
    rootparams = ['OHRTHR58','OHRTHR12','OHRTHR56','OHRTHR57','OHRTHR55','OHRTHR13','OHRTHR36','OHRTHR37','OHRTHR34','OHRTHR35','OHRTHR10','OHRTHR11']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    HYPAVE = (data['OHRTHR12'].vals+data['OHRTHR13'].vals+data['OHRTHR36'].vals+data['OHRTHR37'].vals+data['OHRTHR57'].vals+data['OHRTHR58'].vals)/6
    PARAVE = (data['OHRTHR10'].vals+data['OHRTHR11'].vals+data['OHRTHR34'].vals+data['OHRTHR35'].vals+data['OHRTHR55'].vals+data['OHRTHR56'].vals)/6
    HAAG = PARAVE-HYPAVE
    return (HAAG,data['OHRTHR58'].times)


#-----------------------------------------------
def calcHARG(t1,t2,*args):
    derrparam = 'HARG'
    eqnparams = ['HARG','CAPIAVE','CAPOAVE']
    rootparams = ['OHRTHR52','OHRTHR53','OHRTHR54','OHRTHR31','OHRTHR09','OHRTHR08','OHRTHR33']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    CAPIAVE = (data['OHRTHR09'].vals+data['OHRTHR53'].vals+data['OHRTHR54'].vals)/3
    CAPOAVE = (data['OHRTHR08'].vals+data['OHRTHR31'].vals+data['OHRTHR33'].vals+data['OHRTHR52'].vals)/4
    HARG = CAPOAVE-CAPIAVE
    return (HARG,data['OHRTHR52'].times)


#-----------------------------------------------
def calcHMAX35(t1,t2,*args):
    derrparam = 'HMAX35'
    eqnparams = ['HMAX28','HMAX29','HMAX22','HMAX23','HMAX20','HMAX21','HMAX26','HMAX27','HMAX24','HMAX25','HMAX3','HMAX2','HMAX1','HMAX7','HMAX6','HMAX5','HMAX4','HMAX9','HMAX8','HMAX13','HMAX12','HMAX11','HMAX10','HMAX17','HMAX16','HMAX15','HMAX14','HMAX19','HMAX18','HMAX31','HMAX30','HMAX33','HMAX32','HMAX35','HMAX34']
    rootparams = ['OHRTHR52','OHRTHR53','OHRTHR50','OHRTHR51','OHRTHR56','OHRTHR55','OHRTHR23','OHRTHR22','OHRTHR30','OHRTHR33','OHRTHR12','OHRTHR13','OHRTHR10','OHRTHR11','OHRTHR36','OHRTHR37','OHRTHR49','OHRTHR45','OHRTHR44','OHRTHR47','OHRTHR46','OHRTHR42','OHRTHR29','OHRTHR02','OHRTHR05','OHRTHR04','OHRTHR07','OHRTHR06','OHRTHR09','OHRTHR08','OHRTHR21','OHRTHR27','OHRTHR26','OHRTHR25','OHRTHR24','OHRTHR03']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    HMAX1 = (data['OHRTHR02'].vals<data['OHRTHR03'].vals)*data['OHRTHR03'].vals+(data['OHRTHR02'].vals>=data['OHRTHR03'].vals)*data['OHRTHR02'].vals
    HMAX2 = (HMAX1<data['OHRTHR04'].vals)*data['OHRTHR04'].vals+(HMAX1>=data['OHRTHR04'].vals)*HMAX1
    HMAX3 = (HMAX2<data['OHRTHR05'].vals)*data['OHRTHR05'].vals+(HMAX2>=data['OHRTHR05'].vals)*HMAX2
    HMAX4 = (HMAX3<data['OHRTHR06'].vals)*data['OHRTHR06'].vals+(HMAX3>=data['OHRTHR06'].vals)*HMAX3
    HMAX5 = (HMAX4<data['OHRTHR07'].vals)*data['OHRTHR07'].vals+(HMAX4>=data['OHRTHR07'].vals)*HMAX4
    HMAX6 = (HMAX5<data['OHRTHR08'].vals)*data['OHRTHR08'].vals+(HMAX5>=data['OHRTHR08'].vals)*HMAX5
    HMAX7 = (HMAX6<data['OHRTHR09'].vals)*data['OHRTHR09'].vals+(HMAX6>=data['OHRTHR09'].vals)*HMAX6
    HMAX8 = (HMAX7<data['OHRTHR10'].vals)*data['OHRTHR10'].vals+(HMAX7>=data['OHRTHR10'].vals)*HMAX7
    HMAX9 = (HMAX8<data['OHRTHR11'].vals)*data['OHRTHR11'].vals+(HMAX8>=data['OHRTHR11'].vals)*HMAX8
    HMAX10 = (HMAX9<data['OHRTHR12'].vals)*data['OHRTHR12'].vals+(HMAX9>=data['OHRTHR12'].vals)*HMAX9
    HMAX11 = (HMAX10<data['OHRTHR13'].vals)*data['OHRTHR13'].vals+(HMAX10>=data['OHRTHR13'].vals)*HMAX10
    HMAX12 = (HMAX11<data['OHRTHR21'].vals)*data['OHRTHR21'].vals+(HMAX11>=data['OHRTHR21'].vals)*HMAX11
    HMAX13 = (HMAX12<data['OHRTHR22'].vals)*data['OHRTHR22'].vals+(HMAX12>=data['OHRTHR22'].vals)*HMAX12
    HMAX14 = (HMAX13<data['OHRTHR23'].vals)*data['OHRTHR23'].vals+(HMAX13>=data['OHRTHR23'].vals)*HMAX13
    HMAX15 = (HMAX14<data['OHRTHR24'].vals)*data['OHRTHR24'].vals+(HMAX14>=data['OHRTHR24'].vals)*HMAX14
    HMAX16 = (HMAX15<data['OHRTHR25'].vals)*data['OHRTHR25'].vals+(HMAX15>=data['OHRTHR25'].vals)*HMAX15
    HMAX17 = (HMAX16<data['OHRTHR26'].vals)*data['OHRTHR26'].vals+(HMAX16>=data['OHRTHR26'].vals)*HMAX16
    HMAX18 = (HMAX17<data['OHRTHR27'].vals)*data['OHRTHR27'].vals+(HMAX17>=data['OHRTHR27'].vals)*HMAX17
    HMAX19 = (HMAX18<data['OHRTHR29'].vals)*data['OHRTHR29'].vals+(HMAX18>=data['OHRTHR29'].vals)*HMAX18
    HMAX20 = (HMAX19<data['OHRTHR30'].vals)*data['OHRTHR30'].vals+(HMAX19>=data['OHRTHR30'].vals)*HMAX19
    HMAX21 = (HMAX20<data['OHRTHR36'].vals)*data['OHRTHR36'].vals+(HMAX20>=data['OHRTHR36'].vals)*HMAX20
    HMAX22 = (HMAX21<data['OHRTHR37'].vals)*data['OHRTHR37'].vals+(HMAX21>=data['OHRTHR37'].vals)*HMAX21
    HMAX23 = (HMAX22<data['OHRTHR42'].vals)*data['OHRTHR42'].vals+(HMAX22>=data['OHRTHR42'].vals)*HMAX22
    HMAX24 = (HMAX23<data['OHRTHR33'].vals)*data['OHRTHR33'].vals+(HMAX23>=data['OHRTHR33'].vals)*HMAX23
    HMAX25 = (HMAX24<data['OHRTHR44'].vals)*data['OHRTHR44'].vals+(HMAX24>=data['OHRTHR44'].vals)*HMAX24
    HMAX26 = (HMAX25<data['OHRTHR45'].vals)*data['OHRTHR45'].vals+(HMAX25>=data['OHRTHR45'].vals)*HMAX25
    HMAX27 = (HMAX26<data['OHRTHR46'].vals)*data['OHRTHR46'].vals+(HMAX26>=data['OHRTHR46'].vals)*HMAX26
    HMAX28 = (HMAX27<data['OHRTHR47'].vals)*data['OHRTHR47'].vals+(HMAX27>=data['OHRTHR47'].vals)*HMAX27
    HMAX29 = (HMAX28<data['OHRTHR49'].vals)*data['OHRTHR49'].vals+(HMAX28>=data['OHRTHR49'].vals)*HMAX28
    HMAX30 = (HMAX29<data['OHRTHR50'].vals)*data['OHRTHR50'].vals+(HMAX29>=data['OHRTHR50'].vals)*HMAX29
    HMAX31 = (HMAX30<data['OHRTHR51'].vals)*data['OHRTHR51'].vals+(HMAX30>=data['OHRTHR51'].vals)*HMAX30
    HMAX32 = (HMAX31<data['OHRTHR52'].vals)*data['OHRTHR52'].vals+(HMAX31>=data['OHRTHR52'].vals)*HMAX31
    HMAX33 = (HMAX32<data['OHRTHR53'].vals)*data['OHRTHR53'].vals+(HMAX32>=data['OHRTHR53'].vals)*HMAX32
    HMAX34 = (HMAX33<data['OHRTHR55'].vals)*data['OHRTHR55'].vals+(HMAX33>=data['OHRTHR55'].vals)*HMAX33
    HMAX35 = (HMAX34<data['OHRTHR56'].vals)*data['OHRTHR56'].vals+(HMAX34>=data['OHRTHR56'].vals)*HMAX34
    return (HMAX35,data['OHRTHR52'].times)


#-----------------------------------------------
def calcHMCSAVE(t1,t2,*args):
    derrparam = 'HMCSAVE'
    eqnparams = ['HMCSAVE','P_SUM','H_SUM','CAP_SUM']
    rootparams = ['OHRTHR10','OHRTHR58','OHRTHR52','OHRTHR53','OHRTHR56','OHRTHR57','OHRTHR54','OHRTHR55','OHRTHR12','OHRTHR35','OHRTHR11','OHRTHR08','OHRTHR09','OHRTHR31','OHRTHR33','OHRTHR34','OHRTHR13','OHRTHR36','OHRTHR37']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    P_SUM = data['OHRTHR10'].vals+data['OHRTHR11'].vals+data['OHRTHR34'].vals+data['OHRTHR35'].vals+data['OHRTHR55'].vals+data['OHRTHR56'].vals
    H_SUM = data['OHRTHR12'].vals+data['OHRTHR13'].vals+data['OHRTHR36'].vals+data['OHRTHR37'].vals+data['OHRTHR57'].vals+data['OHRTHR58'].vals
    CAP_SUM = data['OHRTHR08'].vals+data['OHRTHR09'].vals+data['OHRTHR31'].vals+data['OHRTHR33'].vals+data['OHRTHR52'].vals+data['OHRTHR53'].vals+data['OHRTHR54'].vals
    HMCSAVE = (CAP_SUM+P_SUM+H_SUM)/19.0
    return (HMCSAVE,data['OHRTHR10'].times)


#-----------------------------------------------
def calcHMIN35(t1,t2,*args):
    derrparam = 'HMIN35'
    eqnparams = ['HMIN33','HMIN32','HMIN31','HMIN30','HMIN35','HMIN34','HMIN19','HMIN18','HMIN11','HMIN10','HMIN13','HMIN12','HMIN15','HMIN14','HMIN17','HMIN16','HMIN24','HMIN25','HMIN26','HMIN27','HMIN20','HMIN21','HMIN22','HMIN23','HMIN28','HMIN29','HMIN1','HMIN3','HMIN2','HMIN5','HMIN4','HMIN7','HMIN6','HMIN9','HMIN8']
    rootparams = ['OHRTHR52','OHRTHR53','OHRTHR50','OHRTHR51','OHRTHR56','OHRTHR55','OHRTHR23','OHRTHR08','OHRTHR30','OHRTHR33','OHRTHR12','OHRTHR13','OHRTHR36','OHRTHR11','OHRTHR10','OHRTHR37','OHRTHR49','OHRTHR45','OHRTHR44','OHRTHR47','OHRTHR46','OHRTHR42','OHRTHR29','OHRTHR02','OHRTHR05','OHRTHR04','OHRTHR07','OHRTHR06','OHRTHR09','OHRTHR22','OHRTHR21','OHRTHR27','OHRTHR26','OHRTHR25','OHRTHR24','OHRTHR03']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    HMIN1 = (data['OHRTHR02'].vals>data['OHRTHR03'].vals)*data['OHRTHR03'].vals+(data['OHRTHR02'].vals<=data['OHRTHR03'].vals)*data['OHRTHR02'].vals
    HMIN2 = (HMIN1>data['OHRTHR04'].vals)*data['OHRTHR04'].vals+(HMIN1<=data['OHRTHR04'].vals)*HMIN1
    HMIN3 = (HMIN2>data['OHRTHR05'].vals)*data['OHRTHR05'].vals+(HMIN2<=data['OHRTHR05'].vals)*HMIN2
    HMIN4 = (HMIN3>data['OHRTHR06'].vals)*data['OHRTHR06'].vals+(HMIN3<=data['OHRTHR06'].vals)*HMIN3
    HMIN5 = (HMIN4>data['OHRTHR07'].vals)*data['OHRTHR07'].vals+(HMIN4<=data['OHRTHR07'].vals)*HMIN4
    HMIN6 = (HMIN5>data['OHRTHR08'].vals)*data['OHRTHR08'].vals+(HMIN5<=data['OHRTHR08'].vals)*HMIN5
    HMIN7 = (HMIN6>data['OHRTHR09'].vals)*data['OHRTHR09'].vals+(HMIN6<=data['OHRTHR09'].vals)*HMIN6
    HMIN8 = (HMIN7>data['OHRTHR10'].vals)*data['OHRTHR10'].vals+(HMIN7<=data['OHRTHR10'].vals)*HMIN7
    HMIN9 = (HMIN8>data['OHRTHR11'].vals)*data['OHRTHR11'].vals+(HMIN8<=data['OHRTHR11'].vals)*HMIN8
    HMIN10 = (HMIN9>data['OHRTHR12'].vals)*data['OHRTHR12'].vals+(HMIN9<=data['OHRTHR12'].vals)*HMIN9
    HMIN11 = (HMIN10>data['OHRTHR13'].vals)*data['OHRTHR13'].vals+(HMIN10<=data['OHRTHR13'].vals)*HMIN10
    HMIN12 = (HMIN11>data['OHRTHR21'].vals)*data['OHRTHR21'].vals+(HMIN11<=data['OHRTHR21'].vals)*HMIN11
    HMIN13 = (HMIN12>data['OHRTHR22'].vals)*data['OHRTHR22'].vals+(HMIN12<=data['OHRTHR22'].vals)*HMIN12
    HMIN14 = (HMIN13>data['OHRTHR23'].vals)*data['OHRTHR23'].vals+(HMIN13<=data['OHRTHR23'].vals)*HMIN13
    HMIN15 = (HMIN14>data['OHRTHR24'].vals)*data['OHRTHR24'].vals+(HMIN14<=data['OHRTHR24'].vals)*HMIN14
    HMIN16 = (HMIN15>data['OHRTHR25'].vals)*data['OHRTHR25'].vals+(HMIN15<=data['OHRTHR25'].vals)*HMIN15
    HMIN17 = (HMIN16>data['OHRTHR26'].vals)*data['OHRTHR26'].vals+(HMIN16<=data['OHRTHR26'].vals)*HMIN16
    HMIN18 = (HMIN17>data['OHRTHR27'].vals)*data['OHRTHR27'].vals+(HMIN17<=data['OHRTHR27'].vals)*HMIN17
    HMIN19 = (HMIN18>data['OHRTHR29'].vals)*data['OHRTHR29'].vals+(HMIN18<=data['OHRTHR29'].vals)*HMIN18
    HMIN20 = (HMIN19>data['OHRTHR30'].vals)*data['OHRTHR30'].vals+(HMIN19<=data['OHRTHR30'].vals)*HMIN19
    HMIN21 = (HMIN20>data['OHRTHR36'].vals)*data['OHRTHR36'].vals+(HMIN20<=data['OHRTHR36'].vals)*HMIN20
    HMIN22 = (HMIN21>data['OHRTHR37'].vals)*data['OHRTHR37'].vals+(HMIN21<=data['OHRTHR37'].vals)*HMIN21
    HMIN23 = (HMIN22>data['OHRTHR42'].vals)*data['OHRTHR42'].vals+(HMIN22<=data['OHRTHR42'].vals)*HMIN22
    HMIN24 = (HMIN23>data['OHRTHR33'].vals)*data['OHRTHR33'].vals+(HMIN23<=data['OHRTHR33'].vals)*HMIN23
    HMIN25 = (HMIN24>data['OHRTHR44'].vals)*data['OHRTHR44'].vals+(HMIN24<=data['OHRTHR44'].vals)*HMIN24
    HMIN26 = (HMIN25>data['OHRTHR45'].vals)*data['OHRTHR45'].vals+(HMIN25<=data['OHRTHR45'].vals)*HMIN25
    HMIN27 = (HMIN26>data['OHRTHR46'].vals)*data['OHRTHR46'].vals+(HMIN26<=data['OHRTHR46'].vals)*HMIN26
    HMIN28 = (HMIN27>data['OHRTHR47'].vals)*data['OHRTHR47'].vals+(HMIN27<=data['OHRTHR47'].vals)*HMIN27
    HMIN29 = (HMIN28>data['OHRTHR49'].vals)*data['OHRTHR49'].vals+(HMIN28<=data['OHRTHR49'].vals)*HMIN28
    HMIN30 = (HMIN29>data['OHRTHR50'].vals)*data['OHRTHR50'].vals+(HMIN29<=data['OHRTHR50'].vals)*HMIN29
    HMIN31 = (HMIN30>data['OHRTHR51'].vals)*data['OHRTHR51'].vals+(HMIN30<=data['OHRTHR51'].vals)*HMIN30
    HMIN32 = (HMIN31>data['OHRTHR52'].vals)*data['OHRTHR52'].vals+(HMIN31<=data['OHRTHR52'].vals)*HMIN31
    HMIN33 = (HMIN32>data['OHRTHR53'].vals)*data['OHRTHR53'].vals+(HMIN32<=data['OHRTHR53'].vals)*HMIN32
    HMIN34 = (HMIN33>data['OHRTHR55'].vals)*data['OHRTHR55'].vals+(HMIN33<=data['OHRTHR55'].vals)*HMIN33
    HMIN35 = (HMIN34>data['OHRTHR56'].vals)*data['OHRTHR56'].vals+(HMIN34<=data['OHRTHR56'].vals)*HMIN34
    return (HMIN35,data['OHRTHR52'].times)


#-----------------------------------------------
def calcHRMA_AVE(t1,t2,*args):
    derrparam = 'HRMA_AVE'
    eqnparams = ['HSUM6','HSUM4','HSUM5','HSUM2','HSUM3','HSUM1','HRMA_AVE']
    rootparams = ['OHRTHR52','OHRTHR53','OHRTHR50','OHRTHR51','OHRTHR56','OHRTHR55','OHRTHR09','OHRTHR08','OHRTHR30','OHRTHR33','OHRTHR12','OHRTHR13','OHRTHR10','OHRTHR11','OHRTHR36','OHRTHR37','OHRTHR49','OHRTHR45','OHRTHR44','OHRTHR47','OHRTHR46','OHRTHR42','OHRTHR29','OHRTHR02','OHRTHR05','OHRTHR04','OHRTHR07','OHRTHR06','OHRTHR23','OHRTHR22','OHRTHR21','OHRTHR27','OHRTHR26','OHRTHR25','OHRTHR24','OHRTHR03']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    HSUM1 = data['OHRTHR02'].vals+data['OHRTHR03'].vals+data['OHRTHR04'].vals+data['OHRTHR05'].vals+data['OHRTHR06'].vals+data['OHRTHR07'].vals
    HSUM2 = data['OHRTHR08'].vals+data['OHRTHR09'].vals+data['OHRTHR10'].vals+data['OHRTHR11'].vals+data['OHRTHR12'].vals+data['OHRTHR13'].vals
    HSUM3 = data['OHRTHR21'].vals+data['OHRTHR22'].vals+data['OHRTHR23'].vals+data['OHRTHR24'].vals+data['OHRTHR25'].vals+data['OHRTHR26'].vals
    HSUM4 = data['OHRTHR27'].vals+data['OHRTHR29'].vals+data['OHRTHR30'].vals+data['OHRTHR36'].vals+data['OHRTHR37'].vals+data['OHRTHR42'].vals
    HSUM5 = data['OHRTHR33'].vals+data['OHRTHR44'].vals+data['OHRTHR45'].vals+data['OHRTHR46'].vals+data['OHRTHR47'].vals+data['OHRTHR49'].vals
    HSUM6 = data['OHRTHR50'].vals+data['OHRTHR51'].vals+data['OHRTHR52'].vals+data['OHRTHR53'].vals+data['OHRTHR55'].vals+data['OHRTHR56'].vals
    HRMA_AVE = (HSUM1+HSUM2+HSUM3+HSUM4+HSUM5+HSUM6)/36
    return (HRMA_AVE,data['OHRTHR52'].times)


#-----------------------------------------------
def calcHRMHCHK(t1,t2,*args):
    derrparam = 'HRMHCHK'
    eqnparams = ['HMAX28','HMAX29','HMIN35','HMAX22','HMAX23','HMAX20','HMIN34','HMAX26','HMAX27','HMAX24','HMAX25','HMAX3','HMAX2','HMAX1','HMIN30','HMAX7','HMAX6','HMAX5','HMAX4','HMAX9','HMAX8','HMIN19','HMIN18','HMIN11','HMIN10','HMIN13','HMIN12','HMIN15','HMIN14','HMIN17','HMIN16','HMAX13','HMAX12','HMAX11','HMAX10','HMAX17','HMAX16','HMAX15','HMAX14','HMAX19','HMAX18','HMAX21','HMAX31','HMAX30','HMAX33','HMAX32','HMAX35','HMAX34','HMIN24','HMIN25','HMIN26','HMIN27','HMIN20','HMIN21','HMIN22','HMIN23','HMIN28','HMIN29','HMIN33','HRMHCHK','HMIN32','HMIN31','HMIN1','HMIN3','HMIN2','HMIN5','HMIN4','HMIN7','HMIN6','HMIN9','HMIN8']
    rootparams = ['OHRTHR52','OHRTHR53','OHRTHR50','OHRTHR51','OHRTHR56','OHRTHR55','OHRTHR09','OHRTHR08','OHRTHR30','OHRTHR33','OHRTHR12','OHRTHR13','OHRTHR10','OHRTHR11','OHRTHR36','OHRTHR37','OHRTHR49','OHRTHR45','OHRTHR44','OHRTHR47','OHRTHR46','OHRTHR42','OHRTHR03','OHRTHR02','OHRTHR05','OHRTHR04','OHRTHR07','OHRTHR06','OHRTHR23','OHRTHR22','OHRTHR21','OHRTHR27','OHRTHR26','OHRTHR25','OHRTHR24','OHRTHR29']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    HMAX1 = (data['OHRTHR02'].vals<data['OHRTHR03'].vals)*data['OHRTHR03'].vals+(data['OHRTHR02'].vals>=data['OHRTHR03'].vals)*data['OHRTHR02'].vals
    HMAX2 = (HMAX1<data['OHRTHR04'].vals)*data['OHRTHR04'].vals+(HMAX1>=data['OHRTHR04'].vals)*HMAX1
    HMAX3 = (HMAX2<data['OHRTHR05'].vals)*data['OHRTHR05'].vals+(HMAX2>=data['OHRTHR05'].vals)*HMAX2
    HMAX4 = (HMAX3<data['OHRTHR06'].vals)*data['OHRTHR06'].vals+(HMAX3>=data['OHRTHR06'].vals)*HMAX3
    HMAX5 = (HMAX4<data['OHRTHR07'].vals)*data['OHRTHR07'].vals+(HMAX4>=data['OHRTHR07'].vals)*HMAX4
    HMAX6 = (HMAX5<data['OHRTHR08'].vals)*data['OHRTHR08'].vals+(HMAX5>=data['OHRTHR08'].vals)*HMAX5
    HMAX7 = (HMAX6<data['OHRTHR09'].vals)*data['OHRTHR09'].vals+(HMAX6>=data['OHRTHR09'].vals)*HMAX6
    HMAX8 = (HMAX7<data['OHRTHR10'].vals)*data['OHRTHR10'].vals+(HMAX7>=data['OHRTHR10'].vals)*HMAX7
    HMAX9 = (HMAX8<data['OHRTHR11'].vals)*data['OHRTHR11'].vals+(HMAX8>=data['OHRTHR11'].vals)*HMAX8
    HMAX10 = (HMAX9<data['OHRTHR12'].vals)*data['OHRTHR12'].vals+(HMAX9>=data['OHRTHR12'].vals)*HMAX9
    HMAX11 = (HMAX10<data['OHRTHR13'].vals)*data['OHRTHR13'].vals+(HMAX10>=data['OHRTHR13'].vals)*HMAX10
    HMAX12 = (HMAX11<data['OHRTHR21'].vals)*data['OHRTHR21'].vals+(HMAX11>=data['OHRTHR21'].vals)*HMAX11
    HMAX13 = (HMAX12<data['OHRTHR22'].vals)*data['OHRTHR22'].vals+(HMAX12>=data['OHRTHR22'].vals)*HMAX12
    HMAX14 = (HMAX13<data['OHRTHR23'].vals)*data['OHRTHR23'].vals+(HMAX13>=data['OHRTHR23'].vals)*HMAX13
    HMAX15 = (HMAX14<data['OHRTHR24'].vals)*data['OHRTHR24'].vals+(HMAX14>=data['OHRTHR24'].vals)*HMAX14
    HMAX16 = (HMAX15<data['OHRTHR25'].vals)*data['OHRTHR25'].vals+(HMAX15>=data['OHRTHR25'].vals)*HMAX15
    HMAX17 = (HMAX16<data['OHRTHR26'].vals)*data['OHRTHR26'].vals+(HMAX16>=data['OHRTHR26'].vals)*HMAX16
    HMAX18 = (HMAX17<data['OHRTHR27'].vals)*data['OHRTHR27'].vals+(HMAX17>=data['OHRTHR27'].vals)*HMAX17
    HMAX19 = (HMAX18<data['OHRTHR29'].vals)*data['OHRTHR29'].vals+(HMAX18>=data['OHRTHR29'].vals)*HMAX18
    HMAX20 = (HMAX19<data['OHRTHR30'].vals)*data['OHRTHR30'].vals+(HMAX19>=data['OHRTHR30'].vals)*HMAX19
    HMAX21 = (HMAX20<data['OHRTHR36'].vals)*data['OHRTHR36'].vals+(HMAX20>=data['OHRTHR36'].vals)*HMAX20
    HMAX22 = (HMAX21<data['OHRTHR37'].vals)*data['OHRTHR37'].vals+(HMAX21>=data['OHRTHR37'].vals)*HMAX21
    HMAX23 = (HMAX22<data['OHRTHR42'].vals)*data['OHRTHR42'].vals+(HMAX22>=data['OHRTHR42'].vals)*HMAX22
    HMAX24 = (HMAX23<data['OHRTHR33'].vals)*data['OHRTHR33'].vals+(HMAX23>=data['OHRTHR33'].vals)*HMAX23
    HMAX25 = (HMAX24<data['OHRTHR44'].vals)*data['OHRTHR44'].vals+(HMAX24>=data['OHRTHR44'].vals)*HMAX24
    HMAX26 = (HMAX25<data['OHRTHR45'].vals)*data['OHRTHR45'].vals+(HMAX25>=data['OHRTHR45'].vals)*HMAX25
    HMAX27 = (HMAX26<data['OHRTHR46'].vals)*data['OHRTHR46'].vals+(HMAX26>=data['OHRTHR46'].vals)*HMAX26
    HMAX28 = (HMAX27<data['OHRTHR47'].vals)*data['OHRTHR47'].vals+(HMAX27>=data['OHRTHR47'].vals)*HMAX27
    HMAX29 = (HMAX28<data['OHRTHR49'].vals)*data['OHRTHR49'].vals+(HMAX28>=data['OHRTHR49'].vals)*HMAX28
    HMAX30 = (HMAX29<data['OHRTHR50'].vals)*data['OHRTHR50'].vals+(HMAX29>=data['OHRTHR50'].vals)*HMAX29
    HMAX31 = (HMAX30<data['OHRTHR51'].vals)*data['OHRTHR51'].vals+(HMAX30>=data['OHRTHR51'].vals)*HMAX30
    HMAX32 = (HMAX31<data['OHRTHR52'].vals)*data['OHRTHR52'].vals+(HMAX31>=data['OHRTHR52'].vals)*HMAX31
    HMAX33 = (HMAX32<data['OHRTHR53'].vals)*data['OHRTHR53'].vals+(HMAX32>=data['OHRTHR53'].vals)*HMAX32
    HMAX34 = (HMAX33<data['OHRTHR55'].vals)*data['OHRTHR55'].vals+(HMAX33>=data['OHRTHR55'].vals)*HMAX33
    HMAX35 = (HMAX34<data['OHRTHR56'].vals)*data['OHRTHR56'].vals+(HMAX34>=data['OHRTHR56'].vals)*HMAX34
    HMIN1 = (data['OHRTHR02'].vals>data['OHRTHR03'].vals)*data['OHRTHR03'].vals+(data['OHRTHR02'].vals<=data['OHRTHR03'].vals)*data['OHRTHR02'].vals
    HMIN2 = (HMIN1>data['OHRTHR04'].vals)*data['OHRTHR04'].vals+(HMIN1<=data['OHRTHR04'].vals)*HMIN1
    HMIN3 = (HMIN2>data['OHRTHR05'].vals)*data['OHRTHR05'].vals+(HMIN2<=data['OHRTHR05'].vals)*HMIN2
    HMIN4 = (HMIN3>data['OHRTHR06'].vals)*data['OHRTHR06'].vals+(HMIN3<=data['OHRTHR06'].vals)*HMIN3
    HMIN5 = (HMIN4>data['OHRTHR07'].vals)*data['OHRTHR07'].vals+(HMIN4<=data['OHRTHR07'].vals)*HMIN4
    HMIN6 = (HMIN5>data['OHRTHR08'].vals)*data['OHRTHR08'].vals+(HMIN5<=data['OHRTHR08'].vals)*HMIN5
    HMIN7 = (HMIN6>data['OHRTHR09'].vals)*data['OHRTHR09'].vals+(HMIN6<=data['OHRTHR09'].vals)*HMIN6
    HMIN8 = (HMIN7>data['OHRTHR10'].vals)*data['OHRTHR10'].vals+(HMIN7<=data['OHRTHR10'].vals)*HMIN7
    HMIN9 = (HMIN8>data['OHRTHR11'].vals)*data['OHRTHR11'].vals+(HMIN8<=data['OHRTHR11'].vals)*HMIN8
    HMIN10 = (HMIN9>data['OHRTHR12'].vals)*data['OHRTHR12'].vals+(HMIN9<=data['OHRTHR12'].vals)*HMIN9
    HMIN11 = (HMIN10>data['OHRTHR13'].vals)*data['OHRTHR13'].vals+(HMIN10<=data['OHRTHR13'].vals)*HMIN10
    HMIN12 = (HMIN11>data['OHRTHR21'].vals)*data['OHRTHR21'].vals+(HMIN11<=data['OHRTHR21'].vals)*HMIN11
    HMIN13 = (HMIN12>data['OHRTHR22'].vals)*data['OHRTHR22'].vals+(HMIN12<=data['OHRTHR22'].vals)*HMIN12
    HMIN14 = (HMIN13>data['OHRTHR23'].vals)*data['OHRTHR23'].vals+(HMIN13<=data['OHRTHR23'].vals)*HMIN13
    HMIN15 = (HMIN14>data['OHRTHR24'].vals)*data['OHRTHR24'].vals+(HMIN14<=data['OHRTHR24'].vals)*HMIN14
    HMIN16 = (HMIN15>data['OHRTHR25'].vals)*data['OHRTHR25'].vals+(HMIN15<=data['OHRTHR25'].vals)*HMIN15
    HMIN17 = (HMIN16>data['OHRTHR26'].vals)*data['OHRTHR26'].vals+(HMIN16<=data['OHRTHR26'].vals)*HMIN16
    HMIN18 = (HMIN17>data['OHRTHR27'].vals)*data['OHRTHR27'].vals+(HMIN17<=data['OHRTHR27'].vals)*HMIN17
    HMIN19 = (HMIN18>data['OHRTHR29'].vals)*data['OHRTHR29'].vals+(HMIN18<=data['OHRTHR29'].vals)*HMIN18
    HMIN20 = (HMIN19>data['OHRTHR30'].vals)*data['OHRTHR30'].vals+(HMIN19<=data['OHRTHR30'].vals)*HMIN19
    HMIN21 = (HMIN20>data['OHRTHR36'].vals)*data['OHRTHR36'].vals+(HMIN20<=data['OHRTHR36'].vals)*HMIN20
    HMIN22 = (HMIN21>data['OHRTHR37'].vals)*data['OHRTHR37'].vals+(HMIN21<=data['OHRTHR37'].vals)*HMIN21
    HMIN23 = (HMIN22>data['OHRTHR42'].vals)*data['OHRTHR42'].vals+(HMIN22<=data['OHRTHR42'].vals)*HMIN22
    HMIN24 = (HMIN23>data['OHRTHR33'].vals)*data['OHRTHR33'].vals+(HMIN23<=data['OHRTHR33'].vals)*HMIN23
    HMIN25 = (HMIN24>data['OHRTHR44'].vals)*data['OHRTHR44'].vals+(HMIN24<=data['OHRTHR44'].vals)*HMIN24
    HMIN26 = (HMIN25>data['OHRTHR45'].vals)*data['OHRTHR45'].vals+(HMIN25<=data['OHRTHR45'].vals)*HMIN25
    HMIN27 = (HMIN26>data['OHRTHR46'].vals)*data['OHRTHR46'].vals+(HMIN26<=data['OHRTHR46'].vals)*HMIN26
    HMIN28 = (HMIN27>data['OHRTHR47'].vals)*data['OHRTHR47'].vals+(HMIN27<=data['OHRTHR47'].vals)*HMIN27
    HMIN29 = (HMIN28>data['OHRTHR49'].vals)*data['OHRTHR49'].vals+(HMIN28<=data['OHRTHR49'].vals)*HMIN28
    HMIN30 = (HMIN29>data['OHRTHR50'].vals)*data['OHRTHR50'].vals+(HMIN29<=data['OHRTHR50'].vals)*HMIN29
    HMIN31 = (HMIN30>data['OHRTHR51'].vals)*data['OHRTHR51'].vals+(HMIN30<=data['OHRTHR51'].vals)*HMIN30
    HMIN32 = (HMIN31>data['OHRTHR52'].vals)*data['OHRTHR52'].vals+(HMIN31<=data['OHRTHR52'].vals)*HMIN31
    HMIN33 = (HMIN32>data['OHRTHR53'].vals)*data['OHRTHR53'].vals+(HMIN32<=data['OHRTHR53'].vals)*HMIN32
    HMIN34 = (HMIN33>data['OHRTHR55'].vals)*data['OHRTHR55'].vals+(HMIN33<=data['OHRTHR55'].vals)*HMIN33
    HMIN35 = (HMIN34>data['OHRTHR56'].vals)*data['OHRTHR56'].vals+(HMIN34<=data['OHRTHR56'].vals)*HMIN34
    HRMHCHK = HMAX35-HMIN35
    return (HRMHCHK,data['OHRTHR52'].times)


#-----------------------------------------------
def calcOBAAG(t1,t2,*args):
    derrparam = 'OBAAG'
    eqnparams = ['AVE2','AXAVE','AVE1','DIAVE','OBAAG']
    rootparams = ['4RT708T','4RT709T','4RT702T','4RT704T','4RT705T','4RT707T','4RT706T','4RT710T','OOBTHR34','OOBTHR33','OOBTHR31','4RT711T','4RT700T','4RT701T','OOBTHR63','4RT703T','OOBTHR62']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    AVE1 = data['OOBTHR62'].vals+data['OOBTHR63'].vals+data['4RT700T'].vals+data['4RT701T'].vals+data['4RT702T'].vals+data['4RT703T'].vals+data['4RT704T'].vals
    AVE2 = data['4RT705T'].vals+data['4RT706T'].vals+data['4RT707T'].vals+data['4RT708T'].vals+data['4RT709T'].vals+data['4RT710T'].vals+data['4RT711T'].vals
    DIAVE = (data['OOBTHR31'].vals+data['OOBTHR33'].vals+data['OOBTHR34'].vals)/3
    AXAVE = (AVE1+AVE2)/14
    OBAAG = AXAVE-DIAVE
    return (OBAAG,data['4RT708T'].times)


#-----------------------------------------------
def calcOBAAGW(t1,t2,*args):
    derrparam = 'OBAAGW'
    eqnparams = ['OBAAGW','AFT_FIT','FWD_FIT']
    rootparams = ['4RT709T','4RT705T','4RT707T','OOBTHR34','OOBTHR33','OOBTHR31','4RT711T','4RT701T','4RT703T']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    AFT_FIT = (data['OOBTHR31'].vals+data['OOBTHR33'].vals+data['OOBTHR34'].vals)/3
    FWD_FIT = (data['4RT701T'].vals+data['4RT703T'].vals+data['4RT705T'].vals+data['4RT707T'].vals+data['4RT709T'].vals+data['4RT711T'].vals)/6
    OBAAGW = FWD_FIT-AFT_FIT
    return (OBAAGW,data['4RT709T'].times)


#-----------------------------------------------
def calcOBACAVE(t1,t2,*args):
    derrparam = 'OBACAVE'
    eqnparams = ['OBACAVE','MIDCONE','AFTCONE','FWDCONE']
    rootparams = ['OOBTHR19','OOBTHR18','OOBTHR15','OOBTHR14','OOBTHR17','OOBTHR11','OOBTHR10','OOBTHR13','OOBTHR12','OOBTHR30','OOBTHR08','OOBTHR09','OOBTHR24','OOBTHR25','OOBTHR26','OOBTHR27','OOBTHR20','OOBTHR21','OOBTHR22','OOBTHR23','OOBTHR28','OOBTHR29']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    MIDCONE = data['OOBTHR19'].vals+data['OOBTHR20'].vals+data['OOBTHR21'].vals+data['OOBTHR22'].vals+data['OOBTHR23'].vals+data['OOBTHR24'].vals+data['OOBTHR25'].vals
    AFTCONE = data['OOBTHR26'].vals+data['OOBTHR27'].vals+data['OOBTHR28'].vals+data['OOBTHR29'].vals+data['OOBTHR30'].vals
    FWDCONE = data['OOBTHR08'].vals+data['OOBTHR09'].vals+data['OOBTHR10'].vals+data['OOBTHR11'].vals+data['OOBTHR12'].vals+data['OOBTHR13'].vals+data['OOBTHR14'].vals+data['OOBTHR15'].vals+data['OOBTHR17'].vals+data['OOBTHR18'].vals
    OBACAVE = (FWDCONE+MIDCONE+AFTCONE)/22
    return (OBACAVE,data['OOBTHR19'].times)


#-----------------------------------------------
def calcOBACAVEW(t1,t2,*args):
    derrparam = 'OBACAVEW'
    eqnparams = ['FWD_FIT','AFTCONE','OBACAVEW','AFT_FIT','MIDCONE','OBACAVE','FWDCONE']
    rootparams = ['4RT709T','OOBTHR19','OOBTHR18','OOBTHR15','OOBTHR14','OOBTHR17','OOBTHR11','OOBTHR10','OOBTHR13','OOBTHR12','OOBTHR34','OOBTHR33','OOBTHR31','OOBTHR30','4RT705T','4RT707T','4RT711T','4RT701T','4RT703T','OOBTHR08','OOBTHR09','OOBTHR24','OOBTHR25','OOBTHR26','OOBTHR27','OOBTHR20','OOBTHR21','OOBTHR22','OOBTHR23','OOBTHR28','OOBTHR29']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    FWD_FIT = (data['4RT701T'].vals+data['4RT703T'].vals+data['4RT705T'].vals+data['4RT707T'].vals+data['4RT709T'].vals+data['4RT711T'].vals)/6
    AFTCONE = data['OOBTHR26'].vals+data['OOBTHR27'].vals+data['OOBTHR28'].vals+data['OOBTHR29'].vals+data['OOBTHR30'].vals
    FWDCONE = data['OOBTHR08'].vals+data['OOBTHR09'].vals+data['OOBTHR10'].vals+data['OOBTHR11'].vals+data['OOBTHR12'].vals+data['OOBTHR13'].vals+data['OOBTHR14'].vals+data['OOBTHR15'].vals+data['OOBTHR17'].vals+data['OOBTHR18'].vals
    AFT_FIT = (data['OOBTHR31'].vals+data['OOBTHR33'].vals+data['OOBTHR34'].vals)/3
    MIDCONE = data['OOBTHR19'].vals+data['OOBTHR20'].vals+data['OOBTHR21'].vals+data['OOBTHR22'].vals+data['OOBTHR23'].vals+data['OOBTHR24'].vals+data['OOBTHR25'].vals
    OBACAVE = (FWDCONE+MIDCONE+AFTCONE)/22
    OBACAVEW = (OBACAVE*148.-FWD_FIT*70.-AFT_FIT*29.)/49.
    return (OBACAVEW,data['4RT709T'].times)


#-----------------------------------------------
def calcOBADIG(t1,t2,*args):
    derrparam = 'OBADIG'
    eqnparams = ['MZSAVE','OBADIG','PZSAVE']
    rootparams = ['OOBTHR08','OOBTHR19','OOBTHR31','OOBTHR13','OOBTHR26','OOBTHR34','OOBTHR33','OOBTHR22','OOBTHR23','OOBTHR60','OOBTHR61','OOBTHR28','OOBTHR29']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    MZSAVE = (data['OOBTHR08'].vals+data['OOBTHR19'].vals+data['OOBTHR26'].vals+data['OOBTHR31'].vals+data['OOBTHR60'].vals)/5
    PZSAVE = (data['OOBTHR13'].vals+data['OOBTHR22'].vals+data['OOBTHR23'].vals+data['OOBTHR28'].vals+data['OOBTHR29'].vals+data['OOBTHR61'].vals+data['OOBTHR33'].vals+data['OOBTHR34'].vals)/8
    OBADIG = MZSAVE-PZSAVE
    return (OBADIG,data['OOBTHR08'].times)


#-----------------------------------------------
def calcOBADIGW(t1,t2,*args):
    derrparam = 'OBADIGW'
    eqnparams = ['OBADIGW','FWD_FIT_PZ','AFT_FIT_MZ','PZSAVE','MZSAVE','AFT_FIT_PZ','OBADIG','FWD_FIT_MZ']
    rootparams = ['OOBTHR08','OOBTHR19','OOBTHR22','4RT705T','4RT707T','OOBTHR23','OOBTHR13','OOBTHR26','OOBTHR34','OOBTHR33','OOBTHR31','4RT711T','OOBTHR60','OOBTHR61','4RT701T','OOBTHR28','OOBTHR29']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    PZSAVE = (data['OOBTHR13'].vals+data['OOBTHR22'].vals+data['OOBTHR23'].vals+data['OOBTHR28'].vals+data['OOBTHR29'].vals+data['OOBTHR61'].vals+data['OOBTHR33'].vals+data['OOBTHR34'].vals)/8
    MZSAVE = (data['OOBTHR08'].vals+data['OOBTHR19'].vals+data['OOBTHR26'].vals+data['OOBTHR31'].vals+data['OOBTHR60'].vals)/5
    OBADIG = MZSAVE-PZSAVE
    AFT_FIT_PZ = (data['OOBTHR33'].vals+data['OOBTHR34'].vals)/2*29.
    FWD_FIT_PZ = ((data['4RT705T'].vals+data['4RT707T'].vals)/2.)*70.0
    AFT_FIT_MZ = data['OOBTHR31'].vals*29.
    FWD_FIT_MZ = (data['4RT701T'].vals+data['4RT711T'].vals)/2.*70.0
    OBADIGW = (OBADIG*148.-(FWD_FIT_MZ-FWD_FIT_PZ)-(AFT_FIT_MZ-AFT_FIT_PZ))/49.
    return (OBADIGW,data['OOBTHR08'].times)


#-----------------------------------------------
def calcOBA_AVE(t1,t2,*args):
    derrparam = 'OBA_AVE'
    eqnparams = ['OBA_AVE','OSUM5','OSUM4','OSUM6','OSUM1','OSUM3','OSUM2']
    rootparams = ['OOBTHR19','OOBTHR18','OOBTHR15','OOBTHR14','OOBTHR17','OOBTHR11','OOBTHR10','OOBTHR13','OOBTHR12','OOBTHR37','OOBTHR36','OOBTHR35','OOBTHR34','OOBTHR33','OOBTHR31','OOBTHR30','OOBTHR39','OOBTHR38','OOBTHR08','OOBTHR09','OOBTHR24','OOBTHR25','OOBTHR26','OOBTHR27','OOBTHR20','OOBTHR21','OOBTHR22','OOBTHR23','OOBTHR46','OOBTHR44','OOBTHR45','OOBTHR28','OOBTHR29','OOBTHR40','OOBTHR41']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    OSUM1 = data['OOBTHR08'].vals+data['OOBTHR09'].vals+data['OOBTHR10'].vals+data['OOBTHR11'].vals+data['OOBTHR12'].vals+data['OOBTHR13'].vals
    OSUM2 = data['OOBTHR14'].vals+data['OOBTHR15'].vals+data['OOBTHR17'].vals+data['OOBTHR18'].vals+data['OOBTHR19'].vals+data['OOBTHR20'].vals
    OSUM3 = data['OOBTHR21'].vals+data['OOBTHR22'].vals+data['OOBTHR23'].vals+data['OOBTHR24'].vals+data['OOBTHR25'].vals+data['OOBTHR26'].vals
    OSUM4 = data['OOBTHR27'].vals+data['OOBTHR28'].vals+data['OOBTHR29'].vals+data['OOBTHR30'].vals+data['OOBTHR31'].vals+data['OOBTHR33'].vals
    OSUM5 = data['OOBTHR34'].vals+data['OOBTHR35'].vals+data['OOBTHR36'].vals+data['OOBTHR37'].vals+data['OOBTHR38'].vals+data['OOBTHR39'].vals
    OSUM6 = data['OOBTHR40'].vals+data['OOBTHR41'].vals+data['OOBTHR44'].vals+data['OOBTHR45'].vals+data['OOBTHR46'].vals
    OBA_AVE = (OSUM1+OSUM2+OSUM3+OSUM4+OSUM5+OSUM6)/35
    return (OBA_AVE,data['OOBTHR19'].times)


#-----------------------------------------------
def calcOMAX34(t1,t2,*args):
    derrparam = 'OMAX34'
    eqnparams = ['OMAX30','OMAX17','OMAX32','OMAX15','OMAX29','OMAX28','OMAX27','OMAX26','OMAX25','OMAX24','OMAX23','OMAX22','OMAX21','OMAX20','OMAX4','OMAX5','OMAX6','OMAX7','OMAX1','OMAX2','OMAX3','OMAX8','OMAX9','OMAX16','OMAX31','OMAX14','OMAX33','OMAX34','OMAX13','OMAX10','OMAX11','OMAX12','OMAX18','OMAX19']
    rootparams = ['OOBTHR19','OOBTHR18','OOBTHR15','OOBTHR14','OOBTHR17','OOBTHR11','OOBTHR10','OOBTHR13','OOBTHR12','OOBTHR37','OOBTHR36','OOBTHR35','OOBTHR34','OOBTHR33','OOBTHR31','OOBTHR30','OOBTHR39','OOBTHR38','OOBTHR28','OOBTHR08','OOBTHR09','OOBTHR24','OOBTHR25','OOBTHR26','OOBTHR27','OOBTHR20','OOBTHR21','OOBTHR22','OOBTHR23','OOBTHR46','OOBTHR45','OOBTHR42','OOBTHR29','OOBTHR40','OOBTHR41']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    OMAX1 = (data['OOBTHR08'].vals<data['OOBTHR09'].vals)*data['OOBTHR09'].vals+(data['OOBTHR08'].vals>=data['OOBTHR09'].vals)*data['OOBTHR08'].vals
    OMAX2 = (OMAX1<data['OOBTHR10'].vals)*data['OOBTHR10'].vals+(OMAX1>=data['OOBTHR10'].vals)*OMAX1
    OMAX3 = (OMAX2<data['OOBTHR11'].vals)*data['OOBTHR11'].vals+(OMAX2>=data['OOBTHR11'].vals)*OMAX2
    OMAX4 = (OMAX3<data['OOBTHR12'].vals)*data['OOBTHR12'].vals+(OMAX3>=data['OOBTHR12'].vals)*OMAX3
    OMAX5 = (OMAX4<data['OOBTHR13'].vals)*data['OOBTHR13'].vals+(OMAX4>=data['OOBTHR13'].vals)*OMAX4
    OMAX6 = (OMAX5<data['OOBTHR14'].vals)*data['OOBTHR14'].vals+(OMAX5>=data['OOBTHR14'].vals)*OMAX5
    OMAX7 = (OMAX6<data['OOBTHR15'].vals)*data['OOBTHR15'].vals+(OMAX6>=data['OOBTHR15'].vals)*OMAX6
    OMAX8 = (OMAX7<data['OOBTHR17'].vals)*data['OOBTHR17'].vals+(OMAX7>=data['OOBTHR17'].vals)*OMAX7
    OMAX9 = (OMAX8<data['OOBTHR18'].vals)*data['OOBTHR18'].vals+(OMAX8>=data['OOBTHR18'].vals)*OMAX8
    OMAX10 = (OMAX9<data['OOBTHR19'].vals)*data['OOBTHR19'].vals+(OMAX9>=data['OOBTHR19'].vals)*OMAX9
    OMAX11 = (OMAX10<data['OOBTHR20'].vals)*data['OOBTHR20'].vals+(OMAX10>=data['OOBTHR20'].vals)*OMAX10
    OMAX12 = (OMAX11<data['OOBTHR21'].vals)*data['OOBTHR21'].vals+(OMAX11>=data['OOBTHR21'].vals)*OMAX11
    OMAX13 = (OMAX12<data['OOBTHR22'].vals)*data['OOBTHR22'].vals+(OMAX12>=data['OOBTHR22'].vals)*OMAX12
    OMAX14 = (OMAX13<data['OOBTHR23'].vals)*data['OOBTHR23'].vals+(OMAX13>=data['OOBTHR23'].vals)*OMAX13
    OMAX15 = (OMAX14<data['OOBTHR24'].vals)*data['OOBTHR24'].vals+(OMAX14>=data['OOBTHR24'].vals)*OMAX14
    OMAX16 = (OMAX15<data['OOBTHR25'].vals)*data['OOBTHR25'].vals+(OMAX15>=data['OOBTHR25'].vals)*OMAX15
    OMAX17 = (OMAX16<data['OOBTHR26'].vals)*data['OOBTHR26'].vals+(OMAX16>=data['OOBTHR26'].vals)*OMAX16
    OMAX18 = (OMAX17<data['OOBTHR27'].vals)*data['OOBTHR27'].vals+(OMAX17>=data['OOBTHR27'].vals)*OMAX17
    OMAX19 = (OMAX18<data['OOBTHR28'].vals)*data['OOBTHR28'].vals+(OMAX18>=data['OOBTHR28'].vals)*OMAX18
    OMAX20 = (OMAX19<data['OOBTHR29'].vals)*data['OOBTHR29'].vals+(OMAX19>=data['OOBTHR29'].vals)*OMAX19
    OMAX21 = (OMAX20<data['OOBTHR30'].vals)*data['OOBTHR30'].vals+(OMAX20>=data['OOBTHR30'].vals)*OMAX20
    OMAX22 = (OMAX21<data['OOBTHR31'].vals)*data['OOBTHR31'].vals+(OMAX21>=data['OOBTHR31'].vals)*OMAX21
    OMAX23 = (OMAX22<data['OOBTHR33'].vals)*data['OOBTHR33'].vals+(OMAX22>=data['OOBTHR33'].vals)*OMAX22
    OMAX24 = (OMAX23<data['OOBTHR34'].vals)*data['OOBTHR34'].vals+(OMAX23>=data['OOBTHR34'].vals)*OMAX23
    OMAX25 = (OMAX24<data['OOBTHR35'].vals)*data['OOBTHR35'].vals+(OMAX24>=data['OOBTHR35'].vals)*OMAX24
    OMAX26 = (OMAX25<data['OOBTHR36'].vals)*data['OOBTHR36'].vals+(OMAX25>=data['OOBTHR36'].vals)*OMAX25
    OMAX27 = (OMAX26<data['OOBTHR37'].vals)*data['OOBTHR37'].vals+(OMAX26>=data['OOBTHR37'].vals)*OMAX26
    OMAX28 = (OMAX27<data['OOBTHR38'].vals)*data['OOBTHR38'].vals+(OMAX27>=data['OOBTHR38'].vals)*OMAX27
    OMAX29 = (OMAX28<data['OOBTHR39'].vals)*data['OOBTHR39'].vals+(OMAX28>=data['OOBTHR39'].vals)*OMAX28
    OMAX30 = (OMAX29<data['OOBTHR40'].vals)*data['OOBTHR40'].vals+(OMAX29>=data['OOBTHR40'].vals)*OMAX29
    OMAX31 = (OMAX30<data['OOBTHR41'].vals)*data['OOBTHR41'].vals+(OMAX30>=data['OOBTHR41'].vals)*OMAX30
    OMAX32 = (OMAX31<data['OOBTHR42'].vals)*data['OOBTHR42'].vals+(OMAX31>=data['OOBTHR42'].vals)*OMAX31
    OMAX33 = (OMAX32<data['OOBTHR45'].vals)*data['OOBTHR45'].vals+(OMAX32>=data['OOBTHR45'].vals)*OMAX32
    OMAX34 = (OMAX33<data['OOBTHR46'].vals)*data['OOBTHR46'].vals+(OMAX33>=data['OOBTHR46'].vals)*OMAX33
    return (OMAX34,data['OOBTHR19'].times)


#-----------------------------------------------
def calcOMIN34(t1,t2,*args):
    derrparam = 'OMIN34'
    eqnparams = ['OMIN21','OMIN20','OMIN23','OMIN22','OMIN25','OMIN24','OMIN27','OMIN26','OMIN29','OMIN28','OMIN8','OMIN9','OMIN2','OMIN3','OMIN1','OMIN6','OMIN7','OMIN4','OMIN5','OMIN32','OMIN33','OMIN30','OMIN31','OMIN18','OMIN19','OMIN34','OMIN14','OMIN15','OMIN16','OMIN17','OMIN10','OMIN11','OMIN12','OMIN13']
    rootparams = ['OOBTHR19','OOBTHR18','OOBTHR15','OOBTHR14','OOBTHR17','OOBTHR11','OOBTHR10','OOBTHR13','OOBTHR12','OOBTHR37','OOBTHR36','OOBTHR35','OOBTHR34','OOBTHR33','OOBTHR31','OOBTHR30','OOBTHR39','OOBTHR38','OOBTHR28','OOBTHR08','OOBTHR09','OOBTHR24','OOBTHR25','OOBTHR26','OOBTHR27','OOBTHR20','OOBTHR21','OOBTHR22','OOBTHR23','OOBTHR46','OOBTHR45','OOBTHR42','OOBTHR29','OOBTHR40','OOBTHR41']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    OMIN1 = (data['OOBTHR08'].vals>data['OOBTHR09'].vals)*data['OOBTHR09'].vals+(data['OOBTHR08'].vals<=data['OOBTHR09'].vals)*data['OOBTHR08'].vals
    OMIN2 = (OMIN1>data['OOBTHR10'].vals)*data['OOBTHR10'].vals+(OMIN1<=data['OOBTHR10'].vals)*OMIN1
    OMIN3 = (OMIN2>data['OOBTHR11'].vals)*data['OOBTHR11'].vals+(OMIN2<=data['OOBTHR11'].vals)*OMIN2
    OMIN4 = (OMIN3>data['OOBTHR12'].vals)*data['OOBTHR12'].vals+(OMIN3<=data['OOBTHR12'].vals)*OMIN3
    OMIN5 = (OMIN4>data['OOBTHR13'].vals)*data['OOBTHR13'].vals+(OMIN4<=data['OOBTHR13'].vals)*OMIN4
    OMIN6 = (OMIN5>data['OOBTHR14'].vals)*data['OOBTHR14'].vals+(OMIN5<=data['OOBTHR14'].vals)*OMIN5
    OMIN7 = (OMIN6>data['OOBTHR15'].vals)*data['OOBTHR15'].vals+(OMIN6<=data['OOBTHR15'].vals)*OMIN6
    OMIN8 = (OMIN7>data['OOBTHR17'].vals)*data['OOBTHR17'].vals+(OMIN7<=data['OOBTHR17'].vals)*OMIN7
    OMIN9 = (OMIN8>data['OOBTHR18'].vals)*data['OOBTHR18'].vals+(OMIN8<=data['OOBTHR18'].vals)*OMIN8
    OMIN10 = (OMIN9>data['OOBTHR19'].vals)*data['OOBTHR19'].vals+(OMIN9<=data['OOBTHR19'].vals)*OMIN9
    OMIN11 = (OMIN10>data['OOBTHR20'].vals)*data['OOBTHR20'].vals+(OMIN10<=data['OOBTHR20'].vals)*OMIN10
    OMIN12 = (OMIN11>data['OOBTHR21'].vals)*data['OOBTHR21'].vals+(OMIN11<=data['OOBTHR21'].vals)*OMIN11
    OMIN13 = (OMIN12>data['OOBTHR22'].vals)*data['OOBTHR22'].vals+(OMIN12<=data['OOBTHR22'].vals)*OMIN12
    OMIN14 = (OMIN13>data['OOBTHR23'].vals)*data['OOBTHR23'].vals+(OMIN13<=data['OOBTHR23'].vals)*OMIN13
    OMIN15 = (OMIN14>data['OOBTHR24'].vals)*data['OOBTHR24'].vals+(OMIN14<=data['OOBTHR24'].vals)*OMIN14
    OMIN16 = (OMIN15>data['OOBTHR25'].vals)*data['OOBTHR25'].vals+(OMIN15<=data['OOBTHR25'].vals)*OMIN15
    OMIN17 = (OMIN16>data['OOBTHR26'].vals)*data['OOBTHR26'].vals+(OMIN16<=data['OOBTHR26'].vals)*OMIN16
    OMIN18 = (OMIN17>data['OOBTHR27'].vals)*data['OOBTHR27'].vals+(OMIN17<=data['OOBTHR27'].vals)*OMIN17
    OMIN19 = (OMIN18>data['OOBTHR28'].vals)*data['OOBTHR28'].vals+(OMIN18<=data['OOBTHR28'].vals)*OMIN18
    OMIN20 = (OMIN19>data['OOBTHR29'].vals)*data['OOBTHR29'].vals+(OMIN19<=data['OOBTHR29'].vals)*OMIN19
    OMIN21 = (OMIN20>data['OOBTHR30'].vals)*data['OOBTHR30'].vals+(OMIN20<=data['OOBTHR30'].vals)*OMIN20
    OMIN22 = (OMIN21>data['OOBTHR31'].vals)*data['OOBTHR31'].vals+(OMIN21<=data['OOBTHR31'].vals)*OMIN21
    OMIN23 = (OMIN22>data['OOBTHR33'].vals)*data['OOBTHR33'].vals+(OMIN22<=data['OOBTHR33'].vals)*OMIN22
    OMIN24 = (OMIN23>data['OOBTHR34'].vals)*data['OOBTHR34'].vals+(OMIN23<=data['OOBTHR34'].vals)*OMIN23
    OMIN25 = (OMIN24>data['OOBTHR35'].vals)*data['OOBTHR35'].vals+(OMIN24<=data['OOBTHR35'].vals)*OMIN24
    OMIN26 = (OMIN25>data['OOBTHR36'].vals)*data['OOBTHR36'].vals+(OMIN25<=data['OOBTHR36'].vals)*OMIN25
    OMIN27 = (OMIN26>data['OOBTHR37'].vals)*data['OOBTHR37'].vals+(OMIN26<=data['OOBTHR37'].vals)*OMIN26
    OMIN28 = (OMIN27>data['OOBTHR38'].vals)*data['OOBTHR38'].vals+(OMIN27<=data['OOBTHR38'].vals)*OMIN27
    OMIN29 = (OMIN28>data['OOBTHR39'].vals)*data['OOBTHR39'].vals+(OMIN28<=data['OOBTHR39'].vals)*OMIN28
    OMIN30 = (OMIN29>data['OOBTHR40'].vals)*data['OOBTHR40'].vals+(OMIN29<=data['OOBTHR40'].vals)*OMIN29
    OMIN31 = (OMIN30>data['OOBTHR41'].vals)*data['OOBTHR41'].vals+(OMIN30<=data['OOBTHR41'].vals)*OMIN30
    OMIN32 = (OMIN31>data['OOBTHR42'].vals)*data['OOBTHR42'].vals+(OMIN31<=data['OOBTHR42'].vals)*OMIN31
    OMIN33 = (OMIN32>data['OOBTHR45'].vals)*data['OOBTHR45'].vals+(OMIN32<=data['OOBTHR45'].vals)*OMIN32
    OMIN34 = (OMIN33>data['OOBTHR46'].vals)*data['OOBTHR46'].vals+(OMIN33<=data['OOBTHR46'].vals)*OMIN33
    return (OMIN34,data['OOBTHR19'].times)



#-----------------------------------------------
def calcP01(t1,t2,*args):
    derrparam = 'P01'
    eqnparams = ['P01','VSQUARED']
    rootparams = ['ELBV','4OHTRZ01']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P01 = (data['4OHTRZ01'].vals=='ON')*VSQUARED/110.2
    return (P01,data['ELBV'].times)


#-----------------------------------------------
def calcP02(t1,t2,*args):
    derrparam = 'P02'
    eqnparams = ['P02','VSQUARED']
    rootparams = ['ELBV','4OHTRZ02']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P02 = (data['4OHTRZ02'].vals=='ON')*VSQUARED/109.7
    return (P02,data['ELBV'].times)


#-----------------------------------------------
def calcP03(t1,t2,*args):
    derrparam = 'P03'
    eqnparams = ['P03','VSQUARED']
    rootparams = ['ELBV','4OHTRZ03']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P03 = (data['4OHTRZ03'].vals=='ON')*VSQUARED/109.4
    return (P03,data['ELBV'].times)


#-----------------------------------------------
def calcP04(t1,t2,*args):
    derrparam = 'P04'
    eqnparams = ['VSQUARED','P04']
    rootparams = ['4OHTRZ04','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P04 = (data['4OHTRZ04'].vals=='ON')*VSQUARED/175.9
    return (P04,data['4OHTRZ04'].times)


#-----------------------------------------------
def calcP05(t1,t2,*args):
    derrparam = 'P05'
    eqnparams = ['VSQUARED','P05']
    rootparams = ['4OHTRZ05','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P05 = (data['4OHTRZ05'].vals=='ON')*VSQUARED/175.7
    return (P05,data['4OHTRZ05'].times)


#-----------------------------------------------
def calcP06(t1,t2,*args):
    derrparam = 'P06'
    eqnparams = ['P06','VSQUARED']
    rootparams = ['4OHTRZ06','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P06 = (data['4OHTRZ06'].vals=='ON')*VSQUARED/175.6
    return (P06,data['4OHTRZ06'].times)


#-----------------------------------------------
def calcP07(t1,t2,*args):
    derrparam = 'P07'
    eqnparams = ['P07','VSQUARED']
    rootparams = ['4OHTRZ07','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P07 = (data['4OHTRZ07'].vals=='ON')*VSQUARED/135.8
    return (P07,data['4OHTRZ07'].times)


#-----------------------------------------------
def calcP08(t1,t2,*args):
    derrparam = 'P08'
    eqnparams = ['P08','VSQUARED']
    rootparams = ['ELBV','4OHTRZ08']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P08 = (data['4OHTRZ08'].vals=='ON')*VSQUARED/36.1
    return (P08,data['ELBV'].times)


#-----------------------------------------------
def calcP09(t1,t2,*args):
    derrparam = 'P09'
    eqnparams = ['P09','VSQUARED']
    rootparams = ['ELBV','4OHTRZ09']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P09 = (data['4OHTRZ09'].vals=='ON')*VSQUARED/32.6
    return (P09,data['ELBV'].times)


#-----------------------------------------------
def calcP10(t1,t2,*args):
    derrparam = 'P10'
    eqnparams = ['P10','VSQUARED']
    rootparams = ['ELBV','4OHTRZ10']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P10 = (data['4OHTRZ10'].vals=='ON')*VSQUARED/34.9
    return (P10,data['ELBV'].times)


#-----------------------------------------------
def calcP11(t1,t2,*args):
    derrparam = 'P11'
    eqnparams = ['P11','VSQUARED']
    rootparams = ['ELBV','4OHTRZ11']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P11 = (data['4OHTRZ11'].vals=='ON')*VSQUARED/39.4
    return (P11,data['ELBV'].times)


#-----------------------------------------------
def calcP12(t1,t2,*args):
    derrparam = 'P12'
    eqnparams = ['P12','VSQUARED']
    rootparams = ['ELBV','4OHTRZ12']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P12 = (data['4OHTRZ12'].vals=='ON')*VSQUARED/40.3
    return (P12,data['ELBV'].times)


#-----------------------------------------------
def calcP13(t1,t2,*args):
    derrparam = 'P13'
    eqnparams = ['P13','VSQUARED']
    rootparams = ['ELBV','4OHTRZ13']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P13 = (data['4OHTRZ13'].vals=='ON')*VSQUARED/39.7
    return (P13,data['ELBV'].times)


#-----------------------------------------------
def calcP14(t1,t2,*args):
    derrparam = 'P14'
    eqnparams = ['P14','VSQUARED']
    rootparams = ['4OHTRZ14','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P14 = (data['4OHTRZ14'].vals=='ON')*VSQUARED/41.2
    return (P14,data['4OHTRZ14'].times)


#-----------------------------------------------
def calcP15(t1,t2,*args):
    derrparam = 'P15'
    eqnparams = ['P15','VSQUARED']
    rootparams = ['4OHTRZ15','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P15 = (data['4OHTRZ15'].vals=='ON')*VSQUARED/40.5
    return (P15,data['4OHTRZ15'].times)


#-----------------------------------------------
def calcP16(t1,t2,*args):
    derrparam = 'P16'
    eqnparams = ['VSQUARED','P16']
    rootparams = ['4OHTRZ16','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P16 = (data['4OHTRZ16'].vals=='ON')*VSQUARED/41.3
    return (P16,data['4OHTRZ16'].times)


#-----------------------------------------------
def calcP17(t1,t2,*args):
    derrparam = 'P17'
    eqnparams = ['VSQUARED','P17']
    rootparams = ['4OHTRZ17','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P17 = (data['4OHTRZ17'].vals=='ON')*VSQUARED/116.0
    return (P17,data['4OHTRZ17'].times)


#-----------------------------------------------
def calcP18(t1,t2,*args):
    derrparam = 'P18'
    eqnparams = ['P18','VSQUARED']
    rootparams = ['ELBV','4OHTRZ18']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P18 = (data['4OHTRZ18'].vals=='ON')*VSQUARED/115.7
    return (P18,data['ELBV'].times)


#-----------------------------------------------
def calcP19(t1,t2,*args):
    derrparam = 'P19'
    eqnparams = ['P19','VSQUARED']
    rootparams = ['ELBV','4OHTRZ19']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P19 = (data['4OHTRZ19'].vals=='ON')*VSQUARED/95.3
    return (P19,data['ELBV'].times)


#-----------------------------------------------
def calcP20(t1,t2,*args):
    derrparam = 'P20'
    eqnparams = ['P20','VSQUARED']
    rootparams = ['ELBV','4OHTRZ20']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P20 = (data['4OHTRZ20'].vals=='ON')*VSQUARED/379.0
    return (P20,data['ELBV'].times)


#-----------------------------------------------
def calcP23(t1,t2,*args):
    derrparam = 'P23'
    eqnparams = ['VSQUARED','P23']
    rootparams = ['ELBV','4OHTRZ23']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P23 = (data['4OHTRZ23'].vals=='ON')*VSQUARED/386.0
    return (P23,data['ELBV'].times)


#-----------------------------------------------
def calcP24(t1,t2,*args):
    derrparam = 'P24'
    eqnparams = ['P24','VSQUARED']
    rootparams = ['4OHTRZ24','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P24 = (data['4OHTRZ24'].vals=='ON')*VSQUARED/385.8
    return (P24,data['4OHTRZ24'].times)


#-----------------------------------------------
def calcP25(t1,t2,*args):
    derrparam = 'P25'
    eqnparams = ['P25','VSQUARED']
    rootparams = ['4OHTRZ25','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P25 = (data['4OHTRZ25'].vals=='ON')*VSQUARED/383.0
    return (P25,data['4OHTRZ25'].times)


#-----------------------------------------------
def calcP26(t1,t2,*args):
    derrparam = 'P26'
    eqnparams = ['P26','VSQUARED']
    rootparams = ['4OHTRZ26','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    P26 = (data['4OHTRZ26'].vals=='ON')*VSQUARED/383.5
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    return (P26,data['4OHTRZ26'].times)


#-----------------------------------------------
def calcP27(t1,t2,*args):
    derrparam = 'P27'
    eqnparams = ['P27','VSQUARED']
    rootparams = ['4OHTRZ27','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P27 = (data['4OHTRZ27'].vals=='ON')*VSQUARED/383.0
    return (P27,data['4OHTRZ27'].times)


#-----------------------------------------------
def calcP28(t1,t2,*args):
    derrparam = 'P28'
    eqnparams = ['P28','VSQUARED']
    rootparams = ['ELBV','4OHTRZ28']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P28 = (data['4OHTRZ28'].vals=='ON')*VSQUARED/382.3
    return (P28,data['ELBV'].times)


#-----------------------------------------------
def calcP29(t1,t2,*args):
    derrparam = 'P29'
    eqnparams = ['P29','VSQUARED']
    rootparams = ['ELBV','4OHTRZ29']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P29 = (data['4OHTRZ29'].vals=='ON')*VSQUARED/384.0
    return (P29,data['ELBV'].times)


#-----------------------------------------------
def calcP30(t1,t2,*args):
    derrparam = 'P30'
    eqnparams = ['P30','VSQUARED']
    rootparams = ['4OHTRZ30','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P30 = (data['4OHTRZ30'].vals=='ON')*VSQUARED/383.0
    return (P30,data['4OHTRZ30'].times)


#-----------------------------------------------
def calcP31(t1,t2,*args):
    derrparam = 'P31'
    eqnparams = ['P31','VSQUARED']
    rootparams = ['4OHTRZ31','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P31 = (data['4OHTRZ31'].vals=='ON')*VSQUARED/32.2
    return (P31,data['4OHTRZ31'].times)


#-----------------------------------------------
def calcP32(t1,t2,*args):
    derrparam = 'P32'
    eqnparams = ['P32','VSQUARED']
    rootparams = ['4OHTRZ32','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P32 = (data['4OHTRZ32'].vals=='ON')*VSQUARED/28.6
    return (P32,data['4OHTRZ32'].times)


#-----------------------------------------------
def calcP33(t1,t2,*args):
    derrparam = 'P33'
    eqnparams = ['P33','VSQUARED']
    rootparams = ['4OHTRZ33','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P33 = (data['4OHTRZ33'].vals=='ON')*VSQUARED/36.9
    return (P33,data['4OHTRZ33'].times)


#-----------------------------------------------
def calcP34(t1,t2,*args):
    derrparam = 'P34'
    eqnparams = ['VSQUARED','P34']
    rootparams = ['ELBV','4OHTRZ34']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P34 = (data['4OHTRZ34'].vals=='ON')*VSQUARED/28.0
    return (P34,data['ELBV'].times)


#-----------------------------------------------
def calcP35(t1,t2,*args):
    derrparam = 'P35'
    eqnparams = ['VSQUARED','P35']
    rootparams = ['ELBV','4OHTRZ35']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P35 = (data['4OHTRZ35'].vals=='ON')*VSQUARED/32.2
    return (P35,data['ELBV'].times)


#-----------------------------------------------
def calcP36(t1,t2,*args):
    derrparam = 'P36'
    eqnparams = ['P36','VSQUARED']
    rootparams = ['ELBV','4OHTRZ36']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P36 = (data['4OHTRZ36'].vals=='ON')*VSQUARED/44.3
    return (P36,data['ELBV'].times)


#-----------------------------------------------
def calcP37(t1,t2,*args):
    derrparam = 'P37'
    eqnparams = ['P37','VSQUARED']
    rootparams = ['ELBV','4OHTRZ37']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P37 = (data['4OHTRZ37'].vals=='ON')*VSQUARED/32.1
    return (P37,data['ELBV'].times)


#-----------------------------------------------
def calcP38(t1,t2,*args):
    derrparam = 'P38'
    eqnparams = ['P38','VSQUARED']
    rootparams = ['4OHTRZ38','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P38 = (data['4OHTRZ38'].vals=='ON')*VSQUARED/27.8
    return (P38,data['4OHTRZ38'].times)


#-----------------------------------------------
def calcP39(t1,t2,*args):
    derrparam = 'P39'
    eqnparams = ['P39','VSQUARED']
    rootparams = ['4OHTRZ39','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P39 = (data['4OHTRZ39'].vals=='ON')*VSQUARED/36.8
    return (P39,data['4OHTRZ39'].times)


#-----------------------------------------------
def calcP40(t1,t2,*args):
    derrparam = 'P40'
    eqnparams = ['VSQUARED','P40']
    rootparams = ['4OHTRZ40','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P40 = (data['4OHTRZ40'].vals=='ON')*VSQUARED/28.3
    return (P40,data['4OHTRZ40'].times)


#-----------------------------------------------
def calcP41(t1,t2,*args):
    derrparam = 'P41'
    eqnparams = ['VSQUARED','P41']
    rootparams = ['4OHTRZ41','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P41 = (data['4OHTRZ41'].vals=='ON')*VSQUARED/61.7
    return (P41,data['4OHTRZ41'].times)


#-----------------------------------------------
def calcP42(t1,t2,*args):
    derrparam = 'P42'
    eqnparams = ['P42','VSQUARED']
    rootparams = ['4OHTRZ42','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P42 = (data['4OHTRZ42'].vals=='ON')*VSQUARED/51.7
    return (P42,data['4OHTRZ42'].times)


#-----------------------------------------------
def calcP43(t1,t2,*args):
    derrparam = 'P43'
    eqnparams = ['P43','VSQUARED']
    rootparams = ['4OHTRZ43','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P43 = (data['4OHTRZ43'].vals=='ON')*VSQUARED/36.8
    return (P43,data['4OHTRZ43'].times)


#-----------------------------------------------
def calcP44(t1,t2,*args):
    derrparam = 'P44'
    eqnparams = ['P44','VSQUARED']
    rootparams = ['ELBV','4OHTRZ44']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P44 = (data['4OHTRZ44'].vals=='ON')*VSQUARED/36.9
    return (P44,data['ELBV'].times)


#-----------------------------------------------
def calcP45(t1,t2,*args):
    derrparam = 'P45'
    eqnparams = ['P45','VSQUARED']
    rootparams = ['ELBV','4OHTRZ45']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P45 = (data['4OHTRZ45'].vals=='ON')*VSQUARED/36.8
    return (P45,data['ELBV'].times)


#-----------------------------------------------
def calcP46(t1,t2,*args):
    derrparam = 'P46'
    eqnparams = ['P46','VSQUARED']
    rootparams = ['ELBV','4OHTRZ46']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P46 = (data['4OHTRZ46'].vals=='ON')*VSQUARED/36.5
    return (P46,data['ELBV'].times)


#-----------------------------------------------
def calcP47(t1,t2,*args):
    derrparam = 'P47'
    eqnparams = ['P47','VSQUARED']
    rootparams = ['ELBV','4OHTRZ47']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P47 = (data['4OHTRZ47'].vals=='ON')*VSQUARED/52.3
    return (P47,data['ELBV'].times)


#-----------------------------------------------
def calcP48(t1,t2,*args):
    derrparam = 'P48'
    eqnparams = ['VSQUARED','P48']
    rootparams = ['4OHTRZ48','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P48 = (data['4OHTRZ48'].vals=='ON')*VSQUARED/79.5
    return (P48,data['4OHTRZ48'].times)


#-----------------------------------------------
def calcP49(t1,t2,*args):
    derrparam = 'P49'
    eqnparams = ['VSQUARED','P49']
    rootparams = ['4OHTRZ49','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P49 = (data['4OHTRZ49'].vals=='ON')*VSQUARED/34.8
    return (P49,data['4OHTRZ49'].times)


#-----------------------------------------------
def calcP50(t1,t2,*args):
    derrparam = 'P50'
    eqnparams = ['P50','VSQUARED']
    rootparams = ['ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P50 = VSQUARED/35.2
    return (P50,data['ELBV'].times)


#-----------------------------------------------
def calcP51(t1,t2,*args):
    derrparam = 'P51'
    eqnparams = ['P51','VSQUARED']
    rootparams = ['4OHTRZ51','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P51 = (data['4OHTRZ51'].vals=='ON')*VSQUARED/35.4
    return (P51,data['4OHTRZ51'].times)


#-----------------------------------------------
def calcP52(t1,t2,*args):
    derrparam = 'P52'
    eqnparams = ['VSQUARED','P52']
    rootparams = ['4OHTRZ52','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P52 = (data['4OHTRZ52'].vals=='ON')*VSQUARED/34.4
    return (P52,data['4OHTRZ52'].times)


#-----------------------------------------------
def calcP53(t1,t2,*args):
    derrparam = 'P53'
    eqnparams = ['VSQUARED','P53']
    rootparams = ['4OHTRZ53','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P53 = (data['4OHTRZ53'].vals=='ON')*VSQUARED/94.1
    return (P53,data['4OHTRZ53'].times)


#-----------------------------------------------
def calcP54(t1,t2,*args):
    derrparam = 'P54'
    eqnparams = ['P54','VSQUARED']
    rootparams = ['ELBV','4OHTRZ54']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P54 = (data['4OHTRZ54'].vals=='ON')*VSQUARED/124.4
    return (P54,data['ELBV'].times)


#-----------------------------------------------
def calcP55(t1,t2,*args):
    derrparam = 'P55'
    eqnparams = ['P55','VSQUARED']
    rootparams = ['ELBV','4OHTRZ55']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P55 = (data['4OHTRZ55'].vals=='ON')*VSQUARED/126.8
    return (P55,data['ELBV'].times)


#-----------------------------------------------
def calcP57(t1,t2,*args):
    derrparam = 'P57'
    eqnparams = ['P57','VSQUARED']
    rootparams = ['ELBV','4OHTRZ57']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P57 = (data['4OHTRZ57'].vals=='ON')*VSQUARED/142.3
    return (P57,data['ELBV'].times)


#-----------------------------------------------
def calcP58(t1,t2,*args):
    derrparam = 'P58'
    eqnparams = ['P58','VSQUARED']
    rootparams = ['4OHTRZ58','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P58 = (data['4OHTRZ58'].vals=='ON')*VSQUARED/83.7
    return (P58,data['4OHTRZ58'].times)


#-----------------------------------------------
def calcP59(t1,t2,*args):
    derrparam = 'P59'
    eqnparams = ['P59','VSQUARED']
    rootparams = ['4OHTRZ59','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P59 = (data['4OHTRZ59'].vals=='ON')*VSQUARED/29.7
    return (P59,data['4OHTRZ59'].times)


#-----------------------------------------------
def calcP60(t1,t2,*args):
    derrparam = 'P60'
    eqnparams = ['P60','VSQUARED']
    rootparams = ['4OHTRZ60','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P60 = (data['4OHTRZ60'].vals=='ON')*VSQUARED/30.7
    return (P60,data['4OHTRZ60'].times)


#-----------------------------------------------
def calcP61(t1,t2,*args):
    derrparam = 'P61'
    eqnparams = ['P61','VSQUARED']
    rootparams = ['4OHTRZ61','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P61 = (data['4OHTRZ61'].vals=='ON')*VSQUARED/33.7
    return (P61,data['4OHTRZ61'].times)


#-----------------------------------------------
def calcP62(t1,t2,*args):
    derrparam = 'P62'
    eqnparams = ['P62','VSQUARED']
    rootparams = ['4OHTRZ62','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P62 = (data['4OHTRZ62'].vals=='ON')*VSQUARED/36.1
    return (P62,data['4OHTRZ62'].times)


#-----------------------------------------------
def calcP63(t1,t2,*args):
    derrparam = 'P63'
    eqnparams = ['P63','VSQUARED']
    rootparams = ['4OHTRZ63','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P63 = (data['4OHTRZ63'].vals=='ON')*VSQUARED/36.1
    return (P63,data['4OHTRZ63'].times)


#-----------------------------------------------
def calcP64(t1,t2,*args):
    derrparam = 'P64'
    eqnparams = ['P64','VSQUARED']
    rootparams = ['ELBV','4OHTRZ64']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P64 = (data['4OHTRZ64'].vals=='ON')*VSQUARED/44.1
    return (P64,data['ELBV'].times)


#-----------------------------------------------
def calcP65(t1,t2,*args):
    derrparam = 'P65'
    eqnparams = ['P65','VSQUARED']
    rootparams = ['ELBV','4OHTRZ65']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P65 = (data['4OHTRZ65'].vals=='ON')*VSQUARED/37.5
    return (P65,data['ELBV'].times)


#-----------------------------------------------
def calcP66(t1,t2,*args):
    derrparam = 'P66'
    eqnparams = ['VSQUARED','P66']
    rootparams = ['ELBV','4OHTRZ66']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P66 = (data['4OHTRZ66'].vals=='ON')*VSQUARED/29.8
    return (P66,data['ELBV'].times)


#-----------------------------------------------
def calcP67(t1,t2,*args):
    derrparam = 'P67'
    eqnparams = ['VSQUARED','P67']
    rootparams = ['ELBV','4OHTRZ67']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P67 = (data['4OHTRZ67'].vals=='ON')*VSQUARED/52.0
    return (P67,data['ELBV'].times)


#-----------------------------------------------
def calcP68(t1,t2,*args):
    derrparam = 'P68'
    eqnparams = ['P68','VSQUARED']
    rootparams = ['4OHTRZ68','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P68 = (data['4OHTRZ68'].vals=='ON')*VSQUARED/29.0
    return (P68,data['4OHTRZ68'].times)


#-----------------------------------------------
def calcP69(t1,t2,*args):
    derrparam = 'P69'
    eqnparams = ['P69','VSQUARED']
    rootparams = ['4OHTRZ69','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P69 = (data['4OHTRZ69'].vals=='ON')*VSQUARED/37.5
    return (P69,data['4OHTRZ69'].times)


#-----------------------------------------------
def calcP75(t1,t2,*args):
    derrparam = 'P75'
    eqnparams = ['P75','VSQUARED']
    rootparams = ['4OHTRZ75','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P75 = (data['4OHTRZ75'].vals=='ON')*VSQUARED/130.2
    return (P75,data['4OHTRZ75'].times)


#-----------------------------------------------
def calcP76(t1,t2,*args):
    derrparam = 'P76'
    eqnparams = ['P76','VSQUARED']
    rootparams = ['4OHTRZ76','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P76 = (data['4OHTRZ76'].vals=='ON')*VSQUARED/133.4
    return (P76,data['4OHTRZ76'].times)


#-----------------------------------------------
def calcP77(t1,t2,*args):
    derrparam = 'P77'
    eqnparams = ['P77','VSQUARED']
    rootparams = ['4OHTRZ77','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P77 = (data['4OHTRZ77'].vals=='ON')*VSQUARED/131.5
    return (P77,data['4OHTRZ77'].times)


#-----------------------------------------------
def calcP78(t1,t2,*args):
    derrparam = 'P78'
    eqnparams = ['VSQUARED','P78']
    rootparams = ['ELBV','4OHTRZ78']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P78 = (data['4OHTRZ78'].vals=='ON')*VSQUARED/133.2
    return (P78,data['ELBV'].times)


#-----------------------------------------------
def calcP79(t1,t2,*args):
    derrparam = 'P79'
    eqnparams = ['VSQUARED','P79']
    rootparams = ['ELBV','4OHTRZ79']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P79 = (data['4OHTRZ79'].vals=='ON')*VSQUARED/133.1
    return (P79,data['ELBV'].times)


#-----------------------------------------------
def calcP80(t1,t2,*args):
    derrparam = 'P80'
    eqnparams = ['P80','VSQUARED']
    rootparams = ['ELBV','4OHTRZ80']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P80 = (data['4OHTRZ80'].vals=='ON')*VSQUARED/133.0
    return (P80,data['ELBV'].times)


#-----------------------------------------------
def calcPABH(t1,t2,*args):
    derrparam = 'PABH'
    eqnparams = ['VSQUARED','P53','P54','P55','P57','PABH']
    rootparams = ['4OHTRZ53','ELBV','4OHTRZ57','4OHTRZ55','4OHTRZ54']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P53 = (data['4OHTRZ53'].vals=='ON')*VSQUARED/94.1
    P54 = (data['4OHTRZ54'].vals=='ON')*VSQUARED/124.4
    P55 = (data['4OHTRZ55'].vals=='ON')*VSQUARED/126.8
    P57 = (data['4OHTRZ57'].vals=='ON')*VSQUARED/142.3
    PABH = P53+P54+P55+P57
    return (PABH,data['4OHTRZ53'].times)


#-----------------------------------------------
def calcPAFTCONE(t1,t2,*args):
    derrparam = 'PAFTCONE'
    eqnparams = ['VSQUARED','PAFTCONE','P49','P48','P50','P51','P52']
    rootparams = ['4OHTRZ48','4OHTRZ52','4OHTRZ51','ELBV','4OHTRZ49']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P48 = (data['4OHTRZ48'].vals=='ON')*VSQUARED/79.5
    P49 = (data['4OHTRZ49'].vals=='ON')*VSQUARED/34.8
    P50 = VSQUARED/35.2
    P51 = (data['4OHTRZ51'].vals=='ON')*VSQUARED/35.4
    P52 = (data['4OHTRZ52'].vals=='ON')*VSQUARED/34.4
    PAFTCONE = P48+P49+P50+P51+P52
    return (PAFTCONE,data['4OHTRZ48'].times)


#-----------------------------------------------
def calcPAFTCYL(t1,t2,*args):
    derrparam = 'PAFTCYL'
    eqnparams = ['P68','PAFTCYL','VSQUARED','P67','P66']
    rootparams = ['4OHTRZ68','ELBV','4OHTRZ66','4OHTRZ67']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P66 = (data['4OHTRZ66'].vals=='ON')*VSQUARED/29.8
    P67 = (data['4OHTRZ67'].vals=='ON')*VSQUARED/52.0
    P68 = (data['4OHTRZ68'].vals=='ON')*VSQUARED/29.0
    PAFTCYL = P66+P67+P68
    return (PAFTCYL,data['4OHTRZ68'].times)


#-----------------------------------------------
def calcPAHP(t1,t2,*args):
    derrparam = 'PAHP'
    eqnparams = ['P11','P12','P13','PAHP','VSQUARED']
    rootparams = ['ELBV','4OHTRZ13','4OHTRZ12','4OHTRZ11']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P11 = (data['4OHTRZ11'].vals=='ON')*VSQUARED/39.4
    P12 = (data['4OHTRZ12'].vals=='ON')*VSQUARED/40.3
    P13 = (data['4OHTRZ13'].vals=='ON')*VSQUARED/39.7
    PAHP = P11+P12+P13
    return (PAHP,data['ELBV'].times)


#-----------------------------------------------
def calcPCONE(t1,t2,*args):
    derrparam = 'PCONE'
    eqnparams = ['P61','P63','P62','PCONE','VSQUARED']
    rootparams = ['4OHTRZ62','4OHTRZ63','4OHTRZ61','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P61 = (data['4OHTRZ61'].vals=='ON')*VSQUARED/33.7
    P63 = (data['4OHTRZ63'].vals=='ON')*VSQUARED/36.1
    P62 = (data['4OHTRZ62'].vals=='ON')*VSQUARED/36.1
    PCONE = P61+P62+P63
    return (PCONE,data['4OHTRZ62'].times)


#-----------------------------------------------
def calcPFAP(t1,t2,*args):
    derrparam = 'PFAP'
    eqnparams = ['VSQUARED','P03','P02','P01','P07','P06','P05','P04','PFAP']
    rootparams = ['4OHTRZ04','4OHTRZ05','4OHTRZ06','4OHTRZ07','4OHTRZ01','4OHTRZ02','4OHTRZ03','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P01 = (data['4OHTRZ01'].vals=='ON')*VSQUARED/110.2
    P02 = (data['4OHTRZ02'].vals=='ON')*VSQUARED/109.7
    P03 = (data['4OHTRZ03'].vals=='ON')*VSQUARED/109.4
    P04 = (data['4OHTRZ04'].vals=='ON')*VSQUARED/175.9
    P05 = (data['4OHTRZ05'].vals=='ON')*VSQUARED/175.7
    P06 = (data['4OHTRZ06'].vals=='ON')*VSQUARED/175.6
    P07 = (data['4OHTRZ07'].vals=='ON')*VSQUARED/135.8
    PFAP = P01+P02+P03+P04+P05+P06+P07
    return (PFAP,data['4OHTRZ04'].times)


#-----------------------------------------------
def calcPFWDCONE(t1,t2,*args):
    derrparam = 'PFWDCONE'
    eqnparams = ['PFWDCONE','P40','VSQUARED','P38','P39','P32','P33','P31','P36','P37','P34','P35']
    rootparams = ['4OHTRZ39','4OHTRZ38','4OHTRZ31','4OHTRZ33','4OHTRZ32','4OHTRZ35','4OHTRZ34','4OHTRZ37','4OHTRZ36','4OHTRZ40','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P31 = (data['4OHTRZ31'].vals=='ON')*VSQUARED/32.2
    P32 = (data['4OHTRZ32'].vals=='ON')*VSQUARED/28.6
    P33 = (data['4OHTRZ33'].vals=='ON')*VSQUARED/36.9
    P34 = (data['4OHTRZ34'].vals=='ON')*VSQUARED/28.0
    P35 = (data['4OHTRZ35'].vals=='ON')*VSQUARED/32.2
    P36 = (data['4OHTRZ36'].vals=='ON')*VSQUARED/44.3
    P37 = (data['4OHTRZ37'].vals=='ON')*VSQUARED/32.1
    P38 = (data['4OHTRZ38'].vals=='ON')*VSQUARED/27.8
    P39 = (data['4OHTRZ39'].vals=='ON')*VSQUARED/36.8
    P40 = (data['4OHTRZ40'].vals=='ON')*VSQUARED/28.3
    PFWDCONE = P31+P32+P33+P34+P35+P36+P37+P38+P39+P40
    return (PFWDCONE,data['4OHTRZ39'].times)


#-----------------------------------------------
def calcPFWDCYL(t1,t2,*args):
    derrparam = 'PFWDCYL'
    eqnparams = ['P60','P58','VSQUARED','PFWDCYL','P59']
    rootparams = ['4OHTRZ60','ELBV','4OHTRZ58','4OHTRZ59']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P58 = (data['4OHTRZ58'].vals=='ON')*VSQUARED/83.7
    P59 = (data['4OHTRZ59'].vals=='ON')*VSQUARED/29.7
    P60 = (data['4OHTRZ60'].vals=='ON')*VSQUARED/30.7
    PFWDCYL = P58+P59+P60
    return (PFWDCYL,data['4OHTRZ60'].times)


#-----------------------------------------------
def calcPHRMA(t1,t2,*args):
    derrparam = 'PHRMA'
    eqnparams = ['PHRMA','P24','P10','P11','P12','P13','P14','P15','P16','P17','P18','P19','P20','P23','VSQUARED','P03','P02','P01','P07','P06','P05','P04','P09','P08']
    rootparams = ['4OHTRZ08','4OHTRZ09','4OHTRZ04','4OHTRZ05','4OHTRZ06','4OHTRZ07','4OHTRZ01','4OHTRZ02','4OHTRZ03','4OHTRZ19','4OHTRZ18','4OHTRZ17','4OHTRZ16','4OHTRZ15','4OHTRZ14','4OHTRZ13','4OHTRZ12','4OHTRZ11','4OHTRZ10','4OHTRZ24','ELBV','4OHTRZ23','4OHTRZ20']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P01 = (data['4OHTRZ01'].vals=='ON')*VSQUARED/110.2
    P02 = (data['4OHTRZ02'].vals=='ON')*VSQUARED/109.7
    P03 = (data['4OHTRZ03'].vals=='ON')*VSQUARED/109.4
    P04 = (data['4OHTRZ04'].vals=='ON')*VSQUARED/175.9
    P05 = (data['4OHTRZ05'].vals=='ON')*VSQUARED/175.7
    P06 = (data['4OHTRZ06'].vals=='ON')*VSQUARED/175.6
    P07 = (data['4OHTRZ07'].vals=='ON')*VSQUARED/135.8
    P08 = (data['4OHTRZ08'].vals=='ON')*VSQUARED/36.1
    P09 = (data['4OHTRZ09'].vals=='ON')*VSQUARED/32.6
    P10 = (data['4OHTRZ10'].vals=='ON')*VSQUARED/34.9
    P11 = (data['4OHTRZ11'].vals=='ON')*VSQUARED/39.4
    P12 = (data['4OHTRZ12'].vals=='ON')*VSQUARED/40.3
    P13 = (data['4OHTRZ13'].vals=='ON')*VSQUARED/39.7
    P14 = (data['4OHTRZ14'].vals=='ON')*VSQUARED/41.2
    P15 = (data['4OHTRZ15'].vals=='ON')*VSQUARED/40.5
    P16 = (data['4OHTRZ16'].vals=='ON')*VSQUARED/41.3
    P17 = (data['4OHTRZ17'].vals=='ON')*VSQUARED/116.0
    P18 = (data['4OHTRZ18'].vals=='ON')*VSQUARED/115.7
    P19 = (data['4OHTRZ19'].vals=='ON')*VSQUARED/95.3
    P20 = (data['4OHTRZ20'].vals=='ON')*VSQUARED/379.0
    P23 = (data['4OHTRZ23'].vals=='ON')*VSQUARED/386.0
    P24 = (data['4OHTRZ24'].vals=='ON')*VSQUARED/385.8
    PHRMA = P01+P02+P03+P04+P05+P06+P07+P08+P09+P10+P11+P12+P13+P14+P15+P16+P17+P18+P19+P20+P23+P24
    return (PHRMA,data['4OHTRZ08'].times)


#-----------------------------------------------
def calcPHRMASTRUTS(t1,t2,*args):
    derrparam = 'PHRMASTRUTS'
    eqnparams = ['VSQUARED','P25','P27','P26','P30','P29','P28','PHRMASTRUTS']
    rootparams = ['4OHTRZ30','4OHTRZ25','4OHTRZ26','4OHTRZ27','ELBV','4OHTRZ28','4OHTRZ29']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P25 = (data['4OHTRZ25'].vals=='ON')*VSQUARED/383.0
    P27 = (data['4OHTRZ27'].vals=='ON')*VSQUARED/383.0
    P26 = (data['4OHTRZ26'].vals=='ON')*VSQUARED/383.5
    P30 = (data['4OHTRZ30'].vals=='ON')*VSQUARED/383.0
    P29 = (data['4OHTRZ29'].vals=='ON')*VSQUARED/384.0
    P28 = (data['4OHTRZ28'].vals=='ON')*VSQUARED/382.3
    PHRMASTRUTS = P25+P26+P27+P28+P29+P30
    return (PHRMASTRUTS,data['4OHTRZ30'].times)


#-----------------------------------------------
def calcPIC(t1,t2,*args):
    derrparam = 'PIC'
    eqnparams = ['P24','PIC','VSQUARED','P23']
    rootparams = ['4OHTRZ24','ELBV','4OHTRZ23']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P23 = (data['4OHTRZ23'].vals=='ON')*VSQUARED/386.0
    P24 = (data['4OHTRZ24'].vals=='ON')*VSQUARED/385.8
    PIC = P23+P24
    return (PIC,data['4OHTRZ24'].times)


#-----------------------------------------------
def calcPMIDCONE(t1,t2,*args):
    derrparam = 'PMIDCONE'
    eqnparams = ['PMIDCONE','VSQUARED','P47','P46','P45','P44','P43','P42','P41']
    rootparams = ['4OHTRZ47','4OHTRZ41','4OHTRZ42','4OHTRZ43','4OHTRZ44','4OHTRZ45','4OHTRZ46','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P47 = (data['4OHTRZ47'].vals=='ON')*VSQUARED/52.3
    P46 = (data['4OHTRZ46'].vals=='ON')*VSQUARED/36.5
    P45 = (data['4OHTRZ45'].vals=='ON')*VSQUARED/36.8
    P44 = (data['4OHTRZ44'].vals=='ON')*VSQUARED/36.9
    P43 = (data['4OHTRZ43'].vals=='ON')*VSQUARED/36.8
    P42 = (data['4OHTRZ42'].vals=='ON')*VSQUARED/51.7
    P41 = (data['4OHTRZ41'].vals=='ON')*VSQUARED/61.7
    PMIDCONE = P41+P42+P43+P44+P45+P46+P47
    return (PMIDCONE,data['4OHTRZ47'].times)


#-----------------------------------------------
def calcPMNT(t1,t2,*args):
    derrparam = 'PMNT'
    eqnparams = ['PMNT','P14','VSQUARED','P16','P15']
    rootparams = ['4OHTRZ16','4OHTRZ15','4OHTRZ14','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P16 = (data['4OHTRZ16'].vals=='ON')*VSQUARED/41.3
    P15 = (data['4OHTRZ15'].vals=='ON')*VSQUARED/40.5
    P14 = (data['4OHTRZ14'].vals=='ON')*VSQUARED/41.2
    PMNT = P14+P15+P16
    return (PMNT,data['4OHTRZ16'].times)


#-----------------------------------------------
def calcPOBAT(t1,t2,*args):
    derrparam = 'POBAT'
    eqnparams = ['P28','P44','POBACONE','P76','P77','P75','P78','P79','P38','P39','P54','P55','P30','P57','P50','P51','P52','P35','P32','P33','P29','PSTRUTS','P31','POBAT','P36','P80','VSQUARED','P37','P25','P27','P26','P34','P49','P48','P47','P46','P45','P53','P43','P42','P41','P40']
    rootparams = ['4OHTRZ80','4OHTRZ26','4OHTRZ27','4OHTRZ53','4OHTRZ52','4OHTRZ51','4OHTRZ25','4OHTRZ79','4OHTRZ78','4OHTRZ55','4OHTRZ54','4OHTRZ75','4OHTRZ57','4OHTRZ77','4OHTRZ76','4OHTRZ39','4OHTRZ38','4OHTRZ31','4OHTRZ30','4OHTRZ33','4OHTRZ32','4OHTRZ35','4OHTRZ34','4OHTRZ37','4OHTRZ36','ELBV','4OHTRZ40','4OHTRZ41','4OHTRZ42','4OHTRZ43','4OHTRZ44','4OHTRZ45','4OHTRZ46','4OHTRZ47','4OHTRZ48','4OHTRZ49','4OHTRZ28','4OHTRZ29']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P25 = (data['4OHTRZ25'].vals=='ON')*VSQUARED/383.0
    P26 = (data['4OHTRZ26'].vals=='ON')*VSQUARED/383.5
    P27 = (data['4OHTRZ27'].vals=='ON')*VSQUARED/383.0
    P28 = (data['4OHTRZ28'].vals=='ON')*VSQUARED/382.3
    P29 = (data['4OHTRZ29'].vals=='ON')*VSQUARED/384.0
    P30 = (data['4OHTRZ30'].vals=='ON')*VSQUARED/383.0
    P31 = (data['4OHTRZ31'].vals=='ON')*VSQUARED/32.2
    P32 = (data['4OHTRZ32'].vals=='ON')*VSQUARED/28.6
    P33 = (data['4OHTRZ33'].vals=='ON')*VSQUARED/36.9
    P34 = (data['4OHTRZ34'].vals=='ON')*VSQUARED/28.0
    P35 = (data['4OHTRZ35'].vals=='ON')*VSQUARED/32.2
    P36 = (data['4OHTRZ36'].vals=='ON')*VSQUARED/44.3
    P37 = (data['4OHTRZ37'].vals=='ON')*VSQUARED/32.1
    P38 = (data['4OHTRZ38'].vals=='ON')*VSQUARED/27.8
    P39 = (data['4OHTRZ39'].vals=='ON')*VSQUARED/36.8
    P40 = (data['4OHTRZ40'].vals=='ON')*VSQUARED/28.3
    P41 = (data['4OHTRZ41'].vals=='ON')*VSQUARED/61.7
    P42 = (data['4OHTRZ42'].vals=='ON')*VSQUARED/51.7
    P43 = (data['4OHTRZ43'].vals=='ON')*VSQUARED/36.8
    P44 = (data['4OHTRZ44'].vals=='ON')*VSQUARED/36.9
    P45 = (data['4OHTRZ45'].vals=='ON')*VSQUARED/36.8
    P46 = (data['4OHTRZ46'].vals=='ON')*VSQUARED/36.5
    P47 = (data['4OHTRZ47'].vals=='ON')*VSQUARED/52.3
    P48 = (data['4OHTRZ48'].vals=='ON')*VSQUARED/79.5
    P49 = (data['4OHTRZ49'].vals=='ON')*VSQUARED/34.8
    P50 = VSQUARED/35.2
    P51 = (data['4OHTRZ51'].vals=='ON')*VSQUARED/35.4
    P52 = (data['4OHTRZ52'].vals=='ON')*VSQUARED/34.4
    P53 = (data['4OHTRZ53'].vals=='ON')*VSQUARED/94.1
    P54 = (data['4OHTRZ54'].vals=='ON')*VSQUARED/124.4
    P55 = (data['4OHTRZ55'].vals=='ON')*VSQUARED/126.8
    P57 = (data['4OHTRZ57'].vals=='ON')*VSQUARED/142.3
    P75 = (data['4OHTRZ75'].vals=='ON')*VSQUARED/130.2
    P76 = (data['4OHTRZ76'].vals=='ON')*VSQUARED/133.4
    P77 = (data['4OHTRZ77'].vals=='ON')*VSQUARED/131.5
    P78 = (data['4OHTRZ78'].vals=='ON')*VSQUARED/133.2
    P79 = (data['4OHTRZ79'].vals=='ON')*VSQUARED/133.1
    P80 = (data['4OHTRZ80'].vals=='ON')*VSQUARED/133.0
    POBACONE = P31+P32+P33+P34+P35+P36+P37+P38+P39+P40+P41+P42+P43+P44+P45+P46+P47+P48+P49+P50+P51+P52+P53+P54+P55+P57
    PSTRUTS = P75+P76+P77+P78+P79+P80+P25+P26+P27+P28+P29+P30
    POBAT = PSTRUTS+POBACONE
    return (POBAT,data['4OHTRZ80'].times)


#-----------------------------------------------
def calcPOC(t1,t2,*args):
    derrparam = 'POC'
    eqnparams = ['P18','P19','VSQUARED','POC','P17']
    rootparams = ['4OHTRZ17','ELBV','4OHTRZ19','4OHTRZ18']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P17 = (data['4OHTRZ17'].vals=='ON')*VSQUARED/116.0
    P18 = (data['4OHTRZ18'].vals=='ON')*VSQUARED/115.7
    P19 = (data['4OHTRZ19'].vals=='ON')*VSQUARED/95.3
    POC = P17+P18+P19
    return (POC,data['4OHTRZ17'].times)


#-----------------------------------------------
def calcPPL10(t1,t2,*args):
    derrparam = 'PPL10'
    eqnparams = ['P10','P08','PPL10','P09','VSQUARED']
    rootparams = ['ELBV','4OHTRZ08','4OHTRZ09','4OHTRZ10']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P10 = (data['4OHTRZ10'].vals=='ON')*VSQUARED/34.9
    P08 = (data['4OHTRZ08'].vals=='ON')*VSQUARED/36.1
    P09 = (data['4OHTRZ09'].vals=='ON')*VSQUARED/32.6
    PPL10 = P08+P09+P10
    return (PPL10,data['ELBV'].times)


#-----------------------------------------------
def calcPRADVNT(t1,t2,*args):
    derrparam = 'PRADVNT'
    eqnparams = ['P69','PRADVNT','P65','P64','VSQUARED']
    rootparams = ['4OHTRZ65','4OHTRZ69','4OHTRZ64','ELBV']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P69 = (data['4OHTRZ69'].vals=='ON')*VSQUARED/37.5
    P65 = (data['4OHTRZ65'].vals=='ON')*VSQUARED/37.5
    P64 = (data['4OHTRZ64'].vals=='ON')*VSQUARED/44.1
    PRADVNT = P64+P65+P69
    return (PRADVNT,data['4OHTRZ65'].times)


#-----------------------------------------------
def calcPSCSTRUTS(t1,t2,*args):
    derrparam = 'PSCSTRUTS'
    eqnparams = ['P76','P77','PSCSTRUTS','P75','P80','VSQUARED','P78','P79']
    rootparams = ['ELBV','4OHTRZ79','4OHTRZ78','4OHTRZ75','4OHTRZ80','4OHTRZ77','4OHTRZ76']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P76 = (data['4OHTRZ76'].vals=='ON')*VSQUARED/133.4
    P77 = (data['4OHTRZ77'].vals=='ON')*VSQUARED/131.5
    P75 = (data['4OHTRZ75'].vals=='ON')*VSQUARED/130.2
    P80 = (data['4OHTRZ80'].vals=='ON')*VSQUARED/133.0
    P78 = (data['4OHTRZ78'].vals=='ON')*VSQUARED/133.2
    P79 = (data['4OHTRZ79'].vals=='ON')*VSQUARED/133.1
    PSCSTRUTS = P75+P76+P77+P78+P79+P80
    return (PSCSTRUTS,data['ELBV'].times)


#-----------------------------------------------
def calcPTFTE(t1,t2,*args):
    derrparam = 'PTFTE'
    eqnparams = ['P61','P60','P63','P62','P65','P64','P67','P66','P69','P68','VSQUARED','P58','P59','PTFTE']
    rootparams = ['4OHTRZ61','4OHTRZ67','4OHTRZ68','4OHTRZ69','ELBV','4OHTRZ62','4OHTRZ63','4OHTRZ59','4OHTRZ58','4OHTRZ66','4OHTRZ60','4OHTRZ64','4OHTRZ65']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P61 = (data['4OHTRZ61'].vals=='ON')*VSQUARED/33.7
    P60 = (data['4OHTRZ60'].vals=='ON')*VSQUARED/30.7
    P63 = (data['4OHTRZ63'].vals=='ON')*VSQUARED/36.1
    P62 = (data['4OHTRZ62'].vals=='ON')*VSQUARED/36.1
    P65 = (data['4OHTRZ65'].vals=='ON')*VSQUARED/37.5
    P64 = (data['4OHTRZ64'].vals=='ON')*VSQUARED/44.1
    P67 = (data['4OHTRZ67'].vals=='ON')*VSQUARED/52.0
    P66 = (data['4OHTRZ66'].vals=='ON')*VSQUARED/29.8
    P69 = (data['4OHTRZ69'].vals=='ON')*VSQUARED/37.5
    P68 = (data['4OHTRZ68'].vals=='ON')*VSQUARED/29.0
    P58 = (data['4OHTRZ58'].vals=='ON')*VSQUARED/83.7
    P59 = (data['4OHTRZ59'].vals=='ON')*VSQUARED/29.7
    PTFTE = P58+P59+P60+P61+P62+P63+P64+P65+P66+P67+P68+P69
    return (PTFTE,data['4OHTRZ61'].times)


#-----------------------------------------------
def calcPTOTAL(t1,t2,*args):
    derrparam = 'PTOTAL'
    eqnparams = ['P51','P54','P52','P34','P53','PHRMA','P26','P44','POBACONE','P43','P76','P77','P75','P24','PTOTAL','P58','P27','P78','P79','P10','P11','P12','P13','P14','P15','P16','P17','P18','P19','PSTRUTS','P57','P36','P37','PTFTE','P20','P55','P59','P49','P42','P35','P38','P45','P32','P62','P33','P23','P68','P50','P30','P64','P61','P60','P63','P31','P65','POBAT','P67','P66','P69','P39','P80','VSQUARED','P28','P03','P02','P01','P48','P07','P06','P05','P04','P47','P46','P09','P08','P29','P25','P41','P40']
    rootparams = ['4OHTRZ34','4OHTRZ08','4OHTRZ09','4OHTRZ04','4OHTRZ05','4OHTRZ06','4OHTRZ07','4OHTRZ01','4OHTRZ02','4OHTRZ03','4OHTRZ42','4OHTRZ80','4OHTRZ54','4OHTRZ40','4OHTRZ52','4OHTRZ24','4OHTRZ43','4OHTRZ53','4OHTRZ31','4OHTRZ51','ELBV','4OHTRZ57','4OHTRZ78','4OHTRZ55','4OHTRZ30','4OHTRZ75','4OHTRZ79','4OHTRZ77','4OHTRZ76','4OHTRZ33','4OHTRZ23','4OHTRZ39','4OHTRZ38','4OHTRZ32','4OHTRZ46','4OHTRZ19','4OHTRZ18','4OHTRZ17','4OHTRZ16','4OHTRZ15','4OHTRZ14','4OHTRZ13','4OHTRZ12','4OHTRZ11','4OHTRZ10','4OHTRZ29','4OHTRZ48','4OHTRZ37','4OHTRZ49','4OHTRZ36','4OHTRZ25','4OHTRZ58','4OHTRZ35','4OHTRZ41','4OHTRZ45','4OHTRZ59','4OHTRZ26','4OHTRZ27','4OHTRZ68','4OHTRZ69','4OHTRZ44','4OHTRZ28','4OHTRZ20','4OHTRZ47','4OHTRZ62','4OHTRZ63','4OHTRZ60','4OHTRZ61','4OHTRZ66','4OHTRZ67','4OHTRZ64','4OHTRZ65']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    VSQUARED = data['ELBV'].vals*data['ELBV'].vals
    P51 = (data['4OHTRZ51'].vals=='ON')*VSQUARED/35.4
    P54 = (data['4OHTRZ54'].vals=='ON')*VSQUARED/124.4
    P52 = (data['4OHTRZ52'].vals=='ON')*VSQUARED/34.4
    P34 = (data['4OHTRZ34'].vals=='ON')*VSQUARED/28.0
    P53 = (data['4OHTRZ53'].vals=='ON')*VSQUARED/94.1
    P26 = (data['4OHTRZ26'].vals=='ON')*VSQUARED/383.5
    P44 = (data['4OHTRZ44'].vals=='ON')*VSQUARED/36.9
    P43 = (data['4OHTRZ43'].vals=='ON')*VSQUARED/36.8
    P76 = (data['4OHTRZ76'].vals=='ON')*VSQUARED/133.4
    P77 = (data['4OHTRZ77'].vals=='ON')*VSQUARED/131.5
    P75 = (data['4OHTRZ75'].vals=='ON')*VSQUARED/130.2
    P24 = (data['4OHTRZ24'].vals=='ON')*VSQUARED/385.8
    P58 = (data['4OHTRZ58'].vals=='ON')*VSQUARED/83.7
    P27 = (data['4OHTRZ27'].vals=='ON')*VSQUARED/383.0
    P78 = (data['4OHTRZ78'].vals=='ON')*VSQUARED/133.2
    P79 = (data['4OHTRZ79'].vals=='ON')*VSQUARED/133.1
    P10 = (data['4OHTRZ10'].vals=='ON')*VSQUARED/34.9
    P11 = (data['4OHTRZ11'].vals=='ON')*VSQUARED/39.4
    P12 = (data['4OHTRZ12'].vals=='ON')*VSQUARED/40.3
    P13 = (data['4OHTRZ13'].vals=='ON')*VSQUARED/39.7
    P14 = (data['4OHTRZ14'].vals=='ON')*VSQUARED/41.2
    P15 = (data['4OHTRZ15'].vals=='ON')*VSQUARED/40.5
    P16 = (data['4OHTRZ16'].vals=='ON')*VSQUARED/41.3
    P17 = (data['4OHTRZ17'].vals=='ON')*VSQUARED/116.0
    P18 = (data['4OHTRZ18'].vals=='ON')*VSQUARED/115.7
    P19 = (data['4OHTRZ19'].vals=='ON')*VSQUARED/95.3
    P57 = (data['4OHTRZ57'].vals=='ON')*VSQUARED/142.3
    P36 = (data['4OHTRZ36'].vals=='ON')*VSQUARED/44.3
    P37 = (data['4OHTRZ37'].vals=='ON')*VSQUARED/32.1
    P20 = (data['4OHTRZ20'].vals=='ON')*VSQUARED/379.0
    P55 = (data['4OHTRZ55'].vals=='ON')*VSQUARED/126.8
    P59 = (data['4OHTRZ59'].vals=='ON')*VSQUARED/29.7
    P49 = (data['4OHTRZ49'].vals=='ON')*VSQUARED/34.8
    P42 = (data['4OHTRZ42'].vals=='ON')*VSQUARED/51.7
    P35 = (data['4OHTRZ35'].vals=='ON')*VSQUARED/32.2
    P38 = (data['4OHTRZ38'].vals=='ON')*VSQUARED/27.8
    P45 = (data['4OHTRZ45'].vals=='ON')*VSQUARED/36.8
    P32 = (data['4OHTRZ32'].vals=='ON')*VSQUARED/28.6
    P62 = (data['4OHTRZ62'].vals=='ON')*VSQUARED/36.1
    P33 = (data['4OHTRZ33'].vals=='ON')*VSQUARED/36.9
    P23 = (data['4OHTRZ23'].vals=='ON')*VSQUARED/386.0
    P68 = (data['4OHTRZ68'].vals=='ON')*VSQUARED/29.0
    P50 = VSQUARED/35.2
    P30 = (data['4OHTRZ30'].vals=='ON')*VSQUARED/383.0
    P64 = (data['4OHTRZ64'].vals=='ON')*VSQUARED/44.1
    P61 = (data['4OHTRZ61'].vals=='ON')*VSQUARED/33.7
    P60 = (data['4OHTRZ60'].vals=='ON')*VSQUARED/30.7
    P63 = (data['4OHTRZ63'].vals=='ON')*VSQUARED/36.1
    P31 = (data['4OHTRZ31'].vals=='ON')*VSQUARED/32.2
    P65 = (data['4OHTRZ65'].vals=='ON')*VSQUARED/37.5
    P67 = (data['4OHTRZ67'].vals=='ON')*VSQUARED/52.0
    P66 = (data['4OHTRZ66'].vals=='ON')*VSQUARED/29.8
    P69 = (data['4OHTRZ69'].vals=='ON')*VSQUARED/37.5
    P39 = (data['4OHTRZ39'].vals=='ON')*VSQUARED/36.8
    P80 = (data['4OHTRZ80'].vals=='ON')*VSQUARED/133.0
    P28 = (data['4OHTRZ28'].vals=='ON')*VSQUARED/382.3
    P03 = (data['4OHTRZ03'].vals=='ON')*VSQUARED/109.4
    P02 = (data['4OHTRZ02'].vals=='ON')*VSQUARED/109.7
    P01 = (data['4OHTRZ01'].vals=='ON')*VSQUARED/110.2
    P48 = (data['4OHTRZ48'].vals=='ON')*VSQUARED/79.5
    P07 = (data['4OHTRZ07'].vals=='ON')*VSQUARED/135.8
    P06 = (data['4OHTRZ06'].vals=='ON')*VSQUARED/175.6
    P05 = (data['4OHTRZ05'].vals=='ON')*VSQUARED/175.7
    P04 = (data['4OHTRZ04'].vals=='ON')*VSQUARED/175.9
    P47 = (data['4OHTRZ47'].vals=='ON')*VSQUARED/52.3
    P46 = (data['4OHTRZ46'].vals=='ON')*VSQUARED/36.5
    P09 = (data['4OHTRZ09'].vals=='ON')*VSQUARED/32.6
    P08 = (data['4OHTRZ08'].vals=='ON')*VSQUARED/36.1
    P29 = (data['4OHTRZ29'].vals=='ON')*VSQUARED/384.0
    P25 = (data['4OHTRZ25'].vals=='ON')*VSQUARED/383.0
    P41 = (data['4OHTRZ41'].vals=='ON')*VSQUARED/61.7
    P40 = (data['4OHTRZ40'].vals=='ON')*VSQUARED/28.3
    PHRMA = P01+P02+P03+P04+P05+P06+P07+P08+P09+P10+P11+P12+P13+P14+P15+P16+P17+P18+P19+P20+P23+P24
    POBACONE = P31+P32+P33+P34+P35+P36+P37+P38+P39+P40+P41+P42+P43+P44+P45+P46+P47+P48+P49+P50+P51+P52+P53+P54+P55+P57
    PSTRUTS = P75+P76+P77+P78+P79+P80+P25+P26+P27+P28+P29+P30
    PTFTE = P58+P59+P60+P61+P62+P63+P64+P65+P66+P67+P68+P69
    POBAT = PSTRUTS+POBACONE
    PTOTAL = PHRMA+POBAT+PTFTE
    return (PTOTAL,data['4OHTRZ34'].times)


#-----------------------------------------------
def calcSUNANGLE(t1,t2,*args):
    derrparam = 'SUNANGLE'
    eqnparams = ['SUNANGLE']
    rootparams = ['AOSARES1']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    SUNANGLE = (90-data['AOSARES1'].vals)
    return (SUNANGLE,data['AOSARES1'].times)


#-----------------------------------------------
def calcTABMAX(t1,t2,*args):
    derrparam = 'TABMAX'
    eqnparams = ['TABMAX','ABMAX1']
    rootparams = ['OOBTHR47','OOBTHR42','OOBTHR43']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    ABMAX1 = (data['OOBTHR42'].vals<data['OOBTHR43'].vals)*data['OOBTHR43'].vals+(data['OOBTHR42'].vals>=data['OOBTHR43'].vals)*data['OOBTHR42'].vals
    TABMAX = (ABMAX1<data['OOBTHR47'].vals)*data['OOBTHR47'].vals+(ABMAX1>=data['OOBTHR47'].vals)*ABMAX1
    return (TABMAX,data['OOBTHR47'].times)


#-----------------------------------------------
def calcTABMIN(t1,t2,*args):
    derrparam = 'TABMIN'
    eqnparams = ['ABMIN1','TABMIN']
    rootparams = ['OOBTHR47','OOBTHR42','OOBTHR43']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    ABMIN1 = (data['OOBTHR42'].vals>data['OOBTHR43'].vals)*data['OOBTHR43'].vals+(data['OOBTHR42'].vals<=data['OOBTHR43'].vals)*data['OOBTHR42'].vals
    TABMIN = (ABMIN1>data['OOBTHR47'].vals)*data['OOBTHR47'].vals+(ABMIN1<=data['OOBTHR47'].vals)*ABMIN1
    return (TABMIN,data['OOBTHR47'].times)


#-----------------------------------------------
def calcTELAB_AVE(t1,t2,*args):
    derrparam = 'TELAB_AVE'
    eqnparams = ['TELAB_AVE']
    rootparams = ['OOBTHR47','OOBTHR42','OOBTHR43']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    TELAB_AVE = (data['OOBTHR42'].vals+data['OOBTHR43'].vals+data['OOBTHR47'].vals)/3
    return (TELAB_AVE,data['OOBTHR47'].times)


#-----------------------------------------------
def calcTELHS_AVE(t1,t2,*args):
    derrparam = 'TELHS_AVE'
    eqnparams = ['TELHS_AVE']
    rootparams = ['OOBTHR02','OOBTHR03','OOBTHR06','OOBTHR07','OOBTHR04','OOBTHR05']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    TELHS_AVE = (data['OOBTHR02'].vals+data['OOBTHR03'].vals+data['OOBTHR04'].vals+data['OOBTHR05'].vals+data['OOBTHR06'].vals+data['OOBTHR07'].vals)/6
    return (TELHS_AVE,data['OOBTHR02'].times)


#-----------------------------------------------
def calcTELSS_AVE(t1,t2,*args):
    derrparam = 'TELSS_AVE'
    eqnparams = ['TELSS_AVE']
    rootparams = ['OOBTHR51','OOBTHR50','OOBTHR53','OOBTHR52','OOBTHR54','OOBTHR49']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    TELSS_AVE = (data['OOBTHR49'].vals+data['OOBTHR50'].vals+data['OOBTHR51'].vals+data['OOBTHR52'].vals+data['OOBTHR53'].vals+data['OOBTHR54'].vals)/6
    return (TELSS_AVE,data['OOBTHR51'].times)


#-----------------------------------------------
def calcTHSMAX(t1,t2,*args):
    derrparam = 'THSMAX'
    eqnparams = ['HSMAX3','HSMAX2','HSMAX1','THSMAX','HSMAX4']
    rootparams = ['OOBTHR02','OOBTHR03','OOBTHR06','OOBTHR07','OOBTHR04','OOBTHR05']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    HSMAX1 = (data['OOBTHR02'].vals<data['OOBTHR03'].vals)*data['OOBTHR03'].vals+(data['OOBTHR02'].vals>=data['OOBTHR03'].vals)*data['OOBTHR02'].vals
    HSMAX2 = (HSMAX1<data['OOBTHR04'].vals)*data['OOBTHR04'].vals+(HSMAX1>=data['OOBTHR04'].vals)*HSMAX1
    HSMAX3 = (HSMAX2<data['OOBTHR05'].vals)*data['OOBTHR05'].vals+(HSMAX2>=data['OOBTHR05'].vals)*HSMAX2
    HSMAX4 = (HSMAX3<data['OOBTHR06'].vals)*data['OOBTHR06'].vals+(HSMAX3>=data['OOBTHR06'].vals)*HSMAX3
    THSMAX = (HSMAX4<data['OOBTHR07'].vals)*data['OOBTHR07'].vals+(HSMAX4>=data['OOBTHR07'].vals)*HSMAX4
    return (THSMAX,data['OOBTHR02'].times)


#-----------------------------------------------
def calcTHSMIN(t1,t2,*args):
    derrparam = 'THSMIN'
    eqnparams = ['HSMIN4','THSMIN','HSMIN1','HSMIN3','HSMIN2']
    rootparams = ['OOBTHR02','OOBTHR03','OOBTHR06','OOBTHR07','OOBTHR04','OOBTHR05']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    HSMIN1 = (data['OOBTHR02'].vals>data['OOBTHR03'].vals)*data['OOBTHR03'].vals+(data['OOBTHR02'].vals<=data['OOBTHR03'].vals)*data['OOBTHR02'].vals
    HSMIN2 = (HSMIN1>data['OOBTHR04'].vals)*data['OOBTHR04'].vals+(HSMIN1<=data['OOBTHR04'].vals)*HSMIN1
    HSMIN3 = (HSMIN2>data['OOBTHR05'].vals)*data['OOBTHR05'].vals+(HSMIN2<=data['OOBTHR05'].vals)*HSMIN2
    HSMIN4 = (HSMIN3>data['OOBTHR06'].vals)*data['OOBTHR06'].vals+(HSMIN3<=data['OOBTHR06'].vals)*HSMIN3
    THSMIN = (HSMIN4>data['OOBTHR07'].vals)*data['OOBTHR07'].vals+(HSMIN4<=data['OOBTHR07'].vals)*HSMIN4
    return (THSMIN,data['OOBTHR02'].times)


#-----------------------------------------------
def calcTILT_AXIAL(t1,t2,*args):
    derrparam = 'TILT_AXIAL'
    eqnparams = ['TILT_AXIAL','DTAXIALP']
    rootparams = ['OOBAGRD3']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    DTAXIALP = np.abs(1.0*data['OOBAGRD3'].vals)
    TILT_AXIAL = DTAXIALP*0.1084
    return (TILT_AXIAL,data['OOBAGRD3'].times)


#-----------------------------------------------
def calcTILT_BULK(t1,t2,*args):
    derrparam = 'TILT_BULK'
    eqnparams = ['DTBULKP','TILT_BULK']
    rootparams = ['OHRTHR43','OHRTHR42']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    DTBULKP = np.abs((data['OHRTHR42'].vals+data['OHRTHR43'].vals)/2.0-70.0)
    TILT_BULK = DTBULKP*0.0704
    return (TILT_BULK,data['OHRTHR43'].times)


#-----------------------------------------------
def calcTILT_DIAM(t1,t2,*args):
    derrparam = 'TILT_DIAM'
    eqnparams = ['DTDIAMP','TILT_DIAM']
    rootparams = ['OOBAGRD6']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    DTDIAMP = np.abs(1.0*data['OOBAGRD6'].vals)
    TILT_DIAM = DTDIAMP*0.3032
    return (TILT_DIAM,data['OOBAGRD6'].times)


#-----------------------------------------------
def calcTILT_MAX(t1,t2,*args):
    derrparam = 'TILT_MAX'
    eqnparams = ['TILT_BULK','DTDIAMP','DTBULKP','DTAXIALP','TILT_DIAM','TILT_MAX','TILT_AXIAL']
    rootparams = ['OOBAGRD6','OOBAGRD3','OHRTHR43','OHRTHR42']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    DTDIAMP = np.abs(1.0*data['OOBAGRD6'].vals)
    DTBULKP = np.abs((data['OHRTHR42'].vals+data['OHRTHR43'].vals)/2.0-70.0)
    DTAXIALP = np.abs(1.0*data['OOBAGRD3'].vals)
    TILT_DIAM = DTDIAMP*0.3032
    TILT_AXIAL = DTAXIALP*0.1084
    TILT_BULK = DTBULKP*0.0704
    TILT_MAX = (TILT_BULK+TILT_AXIAL+TILT_DIAM)
    return (TILT_MAX,data['OOBAGRD6'].times)


#-----------------------------------------------
def calcTILT_RSS(t1,t2,*args):
    derrparam = 'TILT_RSS'
    eqnparams = ['TILT_BULK','DTDIAMP','TILT_RSS','DTBULKP','DTAXIALP','TILT_DIAM','TILT_AXIAL']
    rootparams = ['OOBAGRD6','OOBAGRD3','OHRTHR43','OHRTHR42']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    DTDIAMP = np.abs(1.0*data['OOBAGRD6'].vals)
    DTBULKP = np.abs((data['OHRTHR42'].vals+data['OHRTHR43'].vals)/2.0-70.0)
    DTAXIALP = np.abs(1.0*data['OOBAGRD3'].vals)
    TILT_DIAM = DTDIAMP*0.3032
    TILT_AXIAL = DTAXIALP*0.1084
    TILT_BULK = DTBULKP*0.0704
    TILT_RSS = np.sqrt(TILT_BULK**2+TILT_AXIAL**2+TILT_DIAM**2)
    return (TILT_RSS,data['OOBAGRD6'].times)


#-----------------------------------------------
def calcTSSMAX(t1,t2,*args):
    derrparam = 'TSSMAX'
    eqnparams = ['SSMAX4','SSMAX2','SSMAX3','TSSMAX','SSMAX1']
    rootparams = ['OOBTHR51','OOBTHR50','OOBTHR53','OOBTHR52','OOBTHR54','OOBTHR49']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    SSMAX1 = (data['OOBTHR49'].vals<data['OOBTHR50'].vals)*data['OOBTHR50'].vals+(data['OOBTHR49'].vals>=data['OOBTHR50'].vals)*data['OOBTHR49'].vals
    SSMAX2 = (SSMAX1<data['OOBTHR51'].vals)*data['OOBTHR51'].vals+(SSMAX1>=data['OOBTHR51'].vals)*SSMAX1
    SSMAX3 = (SSMAX2<data['OOBTHR52'].vals)*data['OOBTHR52'].vals+(SSMAX2>=data['OOBTHR52'].vals)*SSMAX2
    SSMAX4 = (SSMAX3<data['OOBTHR53'].vals)*data['OOBTHR53'].vals+(SSMAX3>=data['OOBTHR53'].vals)*SSMAX3
    TSSMAX = (SSMAX4<data['OOBTHR54'].vals)*data['OOBTHR54'].vals+(SSMAX4>=data['OOBTHR54'].vals)*SSMAX4
    return (TSSMAX,data['OOBTHR51'].times)


#-----------------------------------------------
def calcTSSMIN(t1,t2,*args):
    derrparam = 'TSSMIN'
    eqnparams = ['SSMIN4','TSSMIN','SSMIN1','SSMIN2','SSMIN3']
    rootparams = ['OOBTHR51','OOBTHR50','OOBTHR53','OOBTHR52','OOBTHR54','OOBTHR49']
    if args:
        data = fetch_eng.MSIDset(rootparams,t1,t2,stat=args[0])
    else:
        data = fetch_eng.MSIDset(rootparams,t1,t2,filter_bad=True)
    timestep = np.min([np.median(np.diff(data[name].times)) for name in rootparams])
    data.interpolate(dt=timestep)
    SSMIN1 = (data['OOBTHR49'].vals>data['OOBTHR50'].vals)*data['OOBTHR50'].vals+(data['OOBTHR49'].vals<=data['OOBTHR50'].vals)*data['OOBTHR49'].vals
    SSMIN2 = (SSMIN1>data['OOBTHR51'].vals)*data['OOBTHR51'].vals+(SSMIN1<=data['OOBTHR51'].vals)*SSMIN1
    SSMIN3 = (SSMIN2>data['OOBTHR52'].vals)*data['OOBTHR52'].vals+(SSMIN2<=data['OOBTHR52'].vals)*SSMIN2
    SSMIN4 = (SSMIN3>data['OOBTHR53'].vals)*data['OOBTHR53'].vals+(SSMIN3<=data['OOBTHR53'].vals)*SSMIN3
    TSSMIN = (SSMIN4>data['OOBTHR54'].vals)*data['OOBTHR54'].vals+(SSMIN4<=data['OOBTHR54'].vals)*SSMIN4
    return (TSSMIN,data['OOBTHR51'].times)
