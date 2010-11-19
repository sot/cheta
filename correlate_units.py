import pickle

cxcunits = pickle.load(open('cxcunits.pkl'))
occunits = pickle.load(open('occunits.pkl'))

conversions = {}
for cxcmsid, cxcunit in cxcunits.items():
    if cxcmsid not in occunits:
        print cxcmsid, 'missing'
    else:
        conversions[cxcmsid] = (cxcunit, occunits[cxcmsid])
        
