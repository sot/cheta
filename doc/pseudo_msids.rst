========================================
Pseudo-MSIDs in the engineering archive
========================================

A small selection of pseudo-MSIDs that do not come in the engineering telemetry
stream are also available in the archive.  These are:

* ACIS DEA housekeeping: status from the DEA (including detector focal plane temperature)
* Ephemeris: predictive and definitive orbital (Chandra), solar, and lunar ephemeris values
* SIM telemetry: SIM position and moving status

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

Information about the SIM is available via the following pseudo-MSIDs:

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

Note that 3TSCPOS (steps) = SIM_Z (mm) * 397.7225924607.  No such simple
conversion is available for 3FAPOS because the calibration is a 6th order
polynomial.
