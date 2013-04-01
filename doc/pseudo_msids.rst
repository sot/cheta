========================================
Pseudo-MSIDs in the engineering archive
========================================

A small selection of pseudo-MSIDs that do not come in the engineering telemetry
stream are also available in the archive.  These are:

* ACIS DEA housekeeping: status from the DEA (including detector focal plane temperature)
* Ephemeris: predictive and definitive orbital (Chandra), solar, and lunar ephemeris values
* SIM telemetry: SIM position and moving status
* Derived parameters: values computed from other MSIDs in the archive

ACIS DEA housekeeping
--------------------------------------------------

The ACIS DEA telemeters a variety of useful information that is sent
in an event-based format via queries to the processor.  The engineering
archive reformats those telemetry queries (one per psuedo-MSID) into
records that match the engineering archive format where all queries with the
same time stamp are place in a single record.

The time sample of these data vary but are typically around once per 16 seconds.
Because of what appears to be an issue with CXCDS decom there are frequently
bad values at the beginning of an archive file.  For this reason it is
especially important to perform a fetch with the ``filter_bad=True`` setting.

==================== ====== =======================================
MSID                 Unit   Description
==================== ====== =======================================
tmp_bep_pcb          K      DPA Thermistor 1 - BEP PC Board
tmp_bep_osc          K      DPA Thermistor 2 - BEP Oscillator
tmp_fep0_mong        K      DPA Thermistor 3 - FEP 0 Mongoose
tmp_fep0_pcb         K      DPA Thermistor 4 - FEP 0 PC Board
tmp_fep0_actel       K      DPA Thermistor 5 - FEP 0 ACTEL
tmp_fep0_ram         K      DPA Thermistor 6 - FEP 0 RAM
tmp_fep0_fb          K      DPA Thermistor 7 - FEP 0 Frame Buf
tmp_fep1_mong        K      DPA Thermistor 8 - FEP 1 Mongoose
tmp_fep1_pcb         K      DPA Thermistor 9 - FEP 1 PC Board
tmp_fep1_actel       K      DPA Thermistor 10 - FEP 1 ACTEL
tmp_fep1_ram         K      DPA Thermistor 11 - FEP 1 RAM
tmp_fep1_fb          K      DPA Thermistor 12 - FEP 1 Frame Buf
fptemp_12            K      Focal Plane Temp. Board 12
fptemp_11            K      Focal Plane Temp. Board 11
dpagndref1           V      DPA Ground Reference 1
dpa5vhka             V      DPA 5V Housekeeping A
dpagndref2           V      DPA Ground Reference 2
dpa5vhkb             V      DPA 5V Housekeeping B
dea28volta           V      Primary Raw DEA 28V DC
dea24volta           V      Primary Raw DEA 24V DC
deam15volta          V      Primary Raw DEA -15.5V
deap15volta          V      Primary Raw DEA +15.5V
deam6volta           V      Primary Raw DEA -6V DC
deap6volta           V      Primary Raw DEA +6V DC
rad_pcb_a                   Relative Dose Rad. Monitor Side A
gnd_1                V      Interface Ground Reference
dea28voltb           V      Backup Raw DEA 28V DC
dea24voltb           V      Backup DEA 24V DC
deam15voltb          V      Backup DEA -15.5V DC
deap15voltb          V      Backup DEA +15.5V DC
deam6voltb           V      Backup DEA -6V DC
deap6voltb           V      Backup DEA +6V DC
rad_pcb_b                   Relative Dose Rad. Monitor Side B
gnd_2                V      Ground
==================== ====== =======================================

Ephemeris
---------

CXC processing generates definitive and predictive ephemeris files for the
Chandra, the Moon, and the Sun.  Values are given with respect to Earth (ECI).
Predictive values are available into the near future while definitive values
will be a few weeks behind the present.  (Note that daily and 5-minute
statistics are only available up to the present time).  These values are
contained within the following content types:

============ ======== ===========
Content      Object   Type
============ ======== ===========
orbitephem0  Chandra  Predictive
lunarephem0  Moon     Predictive
solarephem0  Sun      Predictive
orbitephem1  Chandra  Definitive
lunarephem1  Moon     Definitive
solarephem1  Sun      Definitive
============ ======== ===========

The psuedo-MSIDs for each of the ephemeris elements is given in the
following table, where <CONTENT> is replaced by the appropriate Content value
from the previous table.

==================== ====== =================
MSID                 Unit   Description
==================== ====== =================
<CONTENT>_x          m      X position (ECI)
<CONTENT>_y          m      Y position (ECI)
<CONTENT>_z          m      Z position (ECI)
<CONTENT>_vx         m/s    X velocity (ECI)
<CONTENT>_vy         m/s    Y velocity (ECI)
<CONTENT>_vz         m/s    Z velocity (ECI)
==================== ====== =================

In addition there is a set of pseudo-MSIDs that provide a number of
higher-level definitive angle and distance values that are useful.

==================== ====== =========================================
MSID                 Unit   Description
==================== ====== =========================================
Point_X                     Unit Pointing (X)
Point_Y                     Unit Pointing (Y)
Point_Z                     Unit Pointing (Z)
Point_SunCentAng     deg    Pointing-Solar angle (from center)
Point_SunLimbAng     deg    Pointing-Solar angle (from limb)
Point_MoonCentAng    deg    Pointing-Lunar angle (from center)
Point_MoonLimbAng    deg    Pointing-Lunar angle (from limb)
Point_EarthCentAng   deg    Pointing-Earth angle (from center)
Point_EarthLimbAng   deg    Pointing-Earth angle (from limb)
Dist_SatEarth        m      Sat-Earth distance (from Earth center)
Sun_EarthCentAng     deg    Sun-Earth angle (from center)
Sun_EarthLimbAng     deg    Sun-Earth angle (from limb)
Point_RamVectorAng   deg    Pointing-Ram angle
==================== ====== =========================================

Science Instrument Module
-------------------------

Information about the SIM is available via the two following pseudo-MSIDs
categories.

SEA telemetry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The units shown below are for the CXC and ENG unit systems, respectively.

============ ========= ===============================================
MSID         Unit      Description
============ ========= ===============================================
3FAFLAAT     K [degC]  SEA FA flexure a temp a                        
3FAFLBAT     K [degC]  SEA FA flexure b temp a                        
3FAFLCAT     K [degC]  SEA FA flexure c temp a                        
3FAMOVE                SEA FA in motion flag                          
3FAMTRAT     K [degC]  SEA-A focus drive motor temp                   
3FAPOS       mm [step] SEA FA position                                
3FAPSAT      K [degC]  SEA-A power supply temp                        
3FASEAAT     K [degC]  SEA-A box temp                                 
3LDRTMEK               SEA mechanism for last detected reference tab  
3LDRTNO                SEA tab number of reference tab last detected  
3LDRTPOS     mm [step] SEA last detected ref tab position             
3MRMMXMV        [step] SEA max pwm level most recent move             
3SEAID                 SEA identification                             
3SEAINCM               SEA invalid command group flag                 
3SEARAMF               SEA ram failure detection flag                 
3SEAROMF               SEA prom checksum fail flag                    
3SEARSET               SEA reset flag                                 
3SEATMUP               SEA tlm update flag (toggle w/ea update)       
3SFLXAST     K [degC]  SEA flexure a temperature setpoint             
3SFLXBST     K [degC]  SEA flexure b temperature setpoint             
3SFLXCST     K [degC]  SEA flexure c temperature setpoint             
3SHTREN                SEA heater power relay status                  
3SMOTOC      cnts      SEA motor drive overcurrent counter            
3SMOTPEN               SEA motor driver power relay status            
3SMOTSEL               SEA motor selection relay status               
3SMOTSTL     cnts      SEA motor stall counter                        
3SPENDC      cnts      SEA pending cmd count                          
3STAB2EN               SEA tab2 auto position update enab/disa status 
3TRMTRAT     K [degC]  SEA a translation drive motor temp             
3TSCMOVE               SEA TSC in motion flag                         
3TSCPOS      mm [step] SEA TSC position                               
TLMSTATUS              SEA telemetry status (updated or not updated)
============ ========= ===============================================

The state codes for these MSIDs (where applicable) are defined by the CXC `SIM level-0
decom specification <http://icxc.harvard.edu/icd/Sim/Level0/1.2/l0icd.ps>`_ and differ
from the values found in the TDB.  The engineering archive state codes are:

======== ======= ========
MSID     Raw=0   Raw=1
======== ======= ========
3TSCMOVE F       T
3FAMOVE  F       T
3SEAID   SEA-A   SEA-B
3SEARSET F       T
3SEAROMF F       T
3SEAINCM F       T
3STAB2EN DISABLE ENABLE
3SMOTPEN ENABLE  DISABLE
3SMOTSEL TSC     FA
3SHTREN  DISABLE ENABLE
3SEARAMF F       T
======== ======= ========

SIMCOOR (CXC high-level values)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. Note::  These pseudo-MSIDs are deprecated in favor of the standard
   versions such as 3TSCPOS, 3FAPOS, 3TSCMOV, 3TRMTRAT, etc. which
   are available in the SEA telemetry described above.

==================== ====== =========================================
MSID                 Unit   Description
==================== ====== =========================================
SEAIDENT                     SEA identification
SIM_X                mm      X position (FA)
SIM_Y                mm      Y position (not meaningful)
SIM_Z                mm      Z position (TSC)
SIM_X_MOVED                  FA moved
SIM_Z_MOVED                  TSC moved
==================== ====== =========================================

EPHIN
------

Information about the EPHIN instrument is available via the following pseudo-MSIDs:

==================== ====== =========================================
MSID                 Unit   Description
==================== ====== =========================================
TLMBLKCNT                    EIO TLMBLK count
EIOBITCNT                    EIO bit counter
HKOPMODE                     HK operational Mode
HKRESET                      HK reset Flag
HKDOWNLOAD                   HK down load flag
HKUPLOAD                     HK upload Flag
HKFRAMECNTR                  HK internal frame Counter
HKRINGSEGW                   HK ring segment auto switching
HKFAILMODEA                  HK failure mode detector A
HKFAILMODEB                  HK failure mode detector B
HKHVDETG                     HK high voltage detector G
HKHVDETAF                    HK high voltage detectors A-F
HKANALOGPWR                  HK analog power switchs
HKFAILMODEGC                 HK failure mode detectors G-C
HKP5V                 V      HK +5V rail voltage
HKP27V                V      HK +27V rail voltage
HKP6V                 V      HK +6V rail voltage
HKN6V                 V      HK -6V rail voltage
HKP5I                 mA     HK +5V rail current
HKP27I                mA     HK +27V rail current
HKP6I                 mA     HK +6V rail current
HKN6I                 mA     HK -6V rail current
HKEBOXTEMP            K      HK EBox temperature (5EHSE300)
HKABIASLEAKI          uA     HK A bias leakage current
HKBBIASLEAKI          uA     HK B bias leakage current
HKCBIASLEAKI          uA     HK C bias leakage current
HKDBIASLEAKI          uA     HK D bias leakage current
HKEBIASLEAKI          uA     HK E bias leakage current
HKFBIASLEAKI          uA     HK F bias leakage current
HKGHV                 V      HK G high voltage
SCOPMODE                     Sci operational mode
SCSTATUS                     Sci status flags
SCFRAMECNTR                  Sci internal Frame Counter
SCCONTROL                    Sci control flags
SCRINGSEGSW                  Sci ring segment auto switching
SCFAILMODEA                  Sci failure mode detectors A
SCFAILMODEB                  Sci failure mode detectors B
SCHVDETG                     Sci high voltage detector G
SCHVDETAF                    Sci high voltage detectors A-F
SCANALOGPWR                  Sci analog power switches
SCFAILMODEGC                 Sci failure mode detectors G-C
SCPHAPRIPTR                  Sci PHA Priority pointer
SCG0                         Sci single detector counter G0
SCA00                        Sci single detector counter A00
SCA01                        Sci single detector counter A01
SCA02                        Sci single detector counter A02
SCA03                        Sci single detector counter A03
SCA04                        Sci single detector counter A04
SCA05                        Sci single detector counter A05
SCB00                        Sci single detector counter B00
SCB01                        Sci single detector counter B01
SCB02                        Sci single detector counter B02
SCB03                        Sci single detector counter B03
SCB04                        Sci single detector counter B04
SCB05                        Sci single detector counter B05
SCC0                         Sci single detector counter C0
SCD0                         Sci single detector counter D0
SCE0                         Sci single detector counter E0
SCF0                         Sci single detector counter F0
SCP4GM                       Sci single detector counter P4GM
SCP4GR                       Sci single detector counter P4GR
SCP4S                        Sci single detector counter P4S
SCP8GM                       Sci single detector counter P8GM
SCP8GR                       Sci single detector counter P8GR
SCP8S                        Sci single detector counter P8S
SCH4GM                       Sci single detector counter H4GM
SCH4GR                       Sci single detector counter H4GR
SCH4S1                       Sci single detector counter H4S1
SCH4S23                      Sci single detector counter H4S23
SCH8GM                       Sci single detector counter H8GM
SCH8GR                       Sci single detector counter H8GR
SCH8S1                       Sci single detector counter H8S1
SCH8S23                      Sci single detector counter H8S23
SCE150                       Sci single detector counter E150
SCE300                       Sci single detector counter E300
SCE1300                      Sci single detector counter E1300
SCE3000                      Sci single detector counter E3000
SCINT                        Sci single detector counter INT
SCP25GM                      Sci single detector counter P25GM
SCP25GR                      Sci single detector counter P25GR
SCP25S                       Sci single detector counter P25S
SCP41GM                      Sci single detector counter P41GM
SCP41GR                      Sci single detector counter P41GR
SCP41S                       Sci single detector counter P41S
SCH25GM                      Sci single detector counter H25GM
SCH25GR                      Sci single detector counter H25GR
SCH25S1                      Sci single detector counter H25S1
SCH25S23                     Sci single detector counter H25S23
SCH41GM                      Sci single detector counter H41GM
SCH41GR                      Sci single detector counter H41GR
SCH41S1                      Sci single detector counter H41S1
SCH41S23                     Sci single detector counter H41S23
SCCT0                        Sci single detector counter CT0
SCCT1                        Sci single detector counter CT1
SCCT2                        Sci single detector counter CT2
SCCT3                        Sci single detector counter CT3
SCCT4                        Sci single detector counter CT4
SCCT5                        Sci single detector counter CT5
==================== ====== =========================================


Derived Parameters
------------------

The engineering archive has pseudo-MSIDs that are derived via computation from
telemetry MSIDs.  All derived parameter names begin with the characters ``DP_``
(not case sensitive as usual).  Otherwise there is no difference from standard
MSIDs.

Definition
^^^^^^^^^^^

Derived parameters are defined by inheriting from the ``DerivedParameter`` base
class.  Each class definition requires three class attributes:
``content_root``, ``rootparams``, and ``time_step``.  The ``time_step`` should
be an integral multiple of 0.25625.  In the example below a large number of
definition classes have the same content root so another class
``DerivedParameterThermal`` has been created to avoid repeating the
``content_root`` definition every time.

Each definition class also requires a ``calc(self, data)`` method.  The
``data`` argument will be an MSIDset (dict of fetch MSID objects) with
values for each of the ``rootparams`` MSIDs.  The data values in the
MSIDset will be filtered for bad values and aligned to a common time
sequence with step size ``time_step``.
::

  class DerivedParameterThermal(base.DerivedParameter):
      content_root = 'thermal'

  class DP_EE_DIAM(DerivedParameterThermal):
      """Kodak diametrical encircled energy"""
      rootparams = ['OHRMGRD6', 'OHRMGRD3']
      time_step = 32.8

      def calc(self, data):
          VAL2 = np.abs(1.0 * data['OHRMGRD6'].vals)
          VAL1 = np.abs(1.0 * data['OHRMGRD3'].vals)
          DTDIAM = np.max([VAL1, VAL2], axis=0)
          EE_DIAM = DTDIAM * 0.401
          return EE_DIAM

  class DP_P01(DerivedParameterThermal):
      """Zone 1 heater power"""
      rootparams = ['ELBV', '4OHTRZ01']
      time_step = 0.25625

      def calc(self, data):
          VSQUARED = data['ELBV'].vals * data['ELBV'].vals
          P01 = data['4OHTRZ01'].vals * VSQUARED / 110.2
          return P01

  class DP_DPA_POWER(base.DerivedParameter):
      """ACIS total DPA-A and DPA-B power"""
      rootparams = ['1dp28avo', '1dpicacu', '1dp28bvo', '1dpicbcu']
      time_step = 32.8
      content_root = 'acispow'

      def calc(self, data):
          power = (data['1dp28avo'].vals * data['1dpicacu'].vals +
                   data['1dp28bvo'].vals * data['1dpicbcu'].vals)
          return power


ACIS Power
^^^^^^^^^^^
.. automodule:: Ska.engarchive.derived.acispow
   :members:

PCAD
^^^^^
.. automodule:: Ska.engarchive.derived.pcad
   :members:

Thermal
^^^^^^^^^
.. automodule:: Ska.engarchive.derived.thermal
   :members:
   :undoc-members:
