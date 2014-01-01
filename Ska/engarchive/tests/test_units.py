from .. import fetch as fetch_cxc
from .. import fetch_eng as fetch_eng
from .. import fetch_sci as fetch_sci

start = '2011:001:00:00:00'
stop = '2011:001:00:30:00'


def test_initial_units():
    assert fetch_cxc.get_units() == 'cxc'
    assert fetch_eng.get_units() == 'eng'
    assert fetch_sci.get_units() == 'sci'


def test_fetch_units_MSID():
    cxc = fetch_cxc.MSID('tephin', start, stop)
    sci = fetch_sci.MSID('tephin', start, stop)
    eng = fetch_eng.MSID('tephin', start, stop)

    assert cxc.unit == 'K'
    assert sci.unit == 'DEGC'
    assert eng.unit == 'DEGF'


def test_fetch_units_Msid():
    cxc = fetch_cxc.Msid('tephin', start, stop)
    sci = fetch_sci.Msid('tephin', start, stop)
    eng = fetch_eng.Msid('tephin', start, stop)

    assert cxc.unit == 'K'
    assert sci.unit == 'DEGC'
    assert eng.unit == 'DEGF'


def test_fetch_units_MSIDset():
    cxc = fetch_cxc.MSIDset(['tephin'], start, stop)
    sci = fetch_sci.MSIDset(['tephin'], start, stop)
    eng = fetch_eng.MSIDset(['tephin'], start, stop)

    assert cxc['tephin'].unit == 'K'
    assert sci['tephin'].unit == 'DEGC'
    assert eng['tephin'].unit == 'DEGF'


def test_fetch_units_Msidset():
    cxc = fetch_cxc.Msidset(['tephin'], start, stop)
    sci = fetch_sci.Msidset(['tephin'], start, stop)
    eng = fetch_eng.Msidset(['tephin'], start, stop)

    assert cxc['tephin'].unit == 'K'
    assert sci['tephin'].unit == 'DEGC'
    assert eng['tephin'].unit == 'DEGF'


def test_change_units():
    cxc1 = fetch_cxc.MSID('tephin', start, stop)
    assert fetch_cxc.UNITS['system'] == 'cxc'

    fetch_cxc.set_units('eng')
    cxc2 = fetch_cxc.MSID('tephin', start, stop)

    assert fetch_cxc.UNITS['system'] == 'eng'
    assert cxc1.units['system'] == 'cxc'
    assert cxc1.unit == 'K'
    assert cxc2.units['system'] == 'eng'
    assert cxc2.unit == 'DEGF'

    fetch_cxc.set_units('cxc')


def test_versions():
    assert fetch_cxc.__version__ == fetch_sci.__version__
    assert fetch_cxc.__version__ == fetch_eng.__version__


def test_deahk_units():
    cxc = fetch_cxc.MSID('fptemp_11', start, stop)
    sci = fetch_sci.MSID('fptemp_11', start, stop)
    eng = fetch_eng.MSID('fptemp_11', start, stop)
    assert cxc.unit == 'K'
    assert sci.unit == 'DEGC'
    assert eng.unit == 'DEGC'
    assert cxc.vals[0] > 100
    assert sci.vals[0] < -80
    assert eng.vals[0] < -80
