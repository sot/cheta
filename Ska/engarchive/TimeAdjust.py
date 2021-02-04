import numpy as np
from Chandra.Time import DateTime
from Ska.engarchive.utils import logical_intervals
from Ska.tdb import msids
from Ska.tdb import tables
from cheta import fetch_eng as fetch
import copy

def TimeAdjust(msid,ts,tp):
    ''' 
    Inputs:
        msid =  MSID for which to calculate the time adjustments statistics for.  
                instance of  from ska.engarchive.fetch.MSID or Msid  Needs to have a .times field and a .msid field
                **IMPORTANT** msid must have been retrieved from a 'cxc' data source. 'maude' retrieved msids already have the correct timestamp                                
        ts   =  string containing start time in a Chandra.time compatible format, e.g. '2020:100:12:12:12'
        tp   =  string containing stop time in a Chandra.time compatible format, e.g. '2020:100:12:12:12'        
    Outputs:
        out_msid = copy of msid with adjusted times
            
    Notes/Improvements: 
        TBD: Should accept MSIDSet in addition to MSID as input, but this could interfere with the current MSIDSet.interpolate() behavior
        TBD: add an option for in-place adjustment
        TBD: - maybe take msid as string, but manually set data source to avoid 'maude' 'cxc' differences...
        NOTE: Could use times from the msid.times span, but may create problems at the beginning and end since these are subject to adjustment.  Should use time query that generated the MSID
    '''    
    samp_rate = tables['tsmpl'][msid.msid]['SAMPLE_RATE']
    str_num = tables['tsmpl'][msid.msid]['STREAM_NUMBER']
    start_minor_frame = tables['tloc'][msid.msid]['START_MINOR_FRAME']
    fmt_dict = {1: 'FMT1',2: 'FMT2',3: 'FMT3',4: 'FMT4',5: 'FMT5',72:'FMT6',6:'FMT6'}  # stream# to FMT name converter. Unsure if FMT6/SHuttle data needs to be handled    
    # for each format, generate time offset based on stream number,  sample rate and  start minor frame...
    t_off = {}
    t_samp = {}
    str_num_2_idx = {}
    idx = 0
    for stream in str_num:     # Build stream number to index decoder ring.  For each MSID there will be N stream number entries in the table.  There's probably a list comprehension way to do this
        str_num_2_idx[stream] = idx
        idx +=1        
 
    for stream in str_num:          #Now  calculate the offset and sample rate for each stream
        fmt = fmt_dict[stream]       #off_secs = 128/samp_rate -1 # magnitude of offset.  for SR = 128 it's 0, for SR = 64 it's 0,1, for SR = 32, it's 0,1,2,3 &c.
        off_phase = 0.25625 * start_minor_frame[str_num_2_idx[stream]] # note this will fail for very long data sets.  Should use average mission rate or clock look up table
        t_off[fmt] = off_phase        
        t_samp[fmt] = (128 /  samp_rate[str_num_2_idx[stream]] ) * 0.25625  # 128 -> 0.25625, 64 -> 0.51250 , &c.            
    # get Telemetry format for the time interval in question.  CCSDSTMF is updated 128x per MjF, so it's at max time resolution
    tmf = fetch.Msid('CCSDSTMF',ts,tp)
    # generate list of intervals for each format using logical intervals
    fmts = ('FMT1','FMT2','FMT3','FMT4','FMT5','FMT6')
    tmf_intervals = {}
    for fmt in fmts:
        tmf_intervals[fmt] = logical_intervals(tmf.times,tmf.vals==fmt,complete_intervals=False)
    times = msid.times # make scratchpad copy to avoid in-place effects (I think need to check by ref or by val convention)        
    for fmt in fmts:
        for interval in tmf_intervals[fmt]:
            #   now traverse each interval in the msid to be adjusted and add the appropriate offet
            times[(msid.times>=interval['tstart']) & (msid.times < interval['tstop'])] += t_off[fmt]    # not positive on >= convention
    out_msid = copy.copy(msid)  # this is abusing the MSID class a bit.  Not sure how to create 'empty' MSID object
    out_msid.times = times        
    return out_msid
    
    
# DEBUG/TEST SECTION
def main():
    print("---CPA2PWR-------------------")
    print("--- This has start minor frame of 1, so adjusted time should be offset by 0.25625 from even VCDU counts")
    CPA2PWR = fetch.Msid('CPA2PWR', '2020:230:00:00:01','2020:230:00:00:04')
    for t in CPA2PWR.times:
        print(f"{DateTime(t).greta} - unadjusted")
    print("-----------------------------")
    CPA2PWR_adj = TimeAdjust(CPA2PWR,'2020:230:00:00:01','2020:230:00:00:04')
    for t in CPA2PWR_adj.times:
        print(f"{DateTime(t).greta} - adjusted")
    print("-----------------------------")
    CCSDSVCD = fetch.Msid('CCSDSVCD','2020:230:00:00:01','2020:230:00:00:04')
    for ii in range(len(CCSDSVCD.vals)):
        print(f"VCDU CNT: {CCSDSVCD.vals[ii]} - {DateTime(CCSDSVCD.times[ii]).greta}")
if __name__ == "__main__":
    # execute only if run as a script
    main()

   