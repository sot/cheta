import numpy as np
import pytest

from .. import fetch


date1 = '2016:001:00:00:00.1'
date2 = '2016:001:00:00:02.0'
date3 = '2016:001:00:00:05.0'


try:
    import maude
    maude.get_msids(msids='ccsdsid', start=date1, stop=date2)
except Exception as err:
    HAS_MAUDE = False
else:
    HAS_MAUDE = True


def test_data_source():
    """Unit test of _DataSource class"""
    assert fetch.data_source.get() == ('cxc',)

    # Context manager
    with fetch.data_source('maude'):
        assert fetch.data_source.get() == ('maude',)
    assert fetch.data_source.get() == ('cxc',)

    with fetch.data_source('cxc', 'maude'):
        assert fetch.data_source.get() == ('cxc', 'maude',)
    assert fetch.data_source.get() == ('cxc',)

    fetch.data_source.set('maude')
    assert fetch.data_source.get() == ('maude',)
    fetch.data_source.set('cxc')
    assert fetch.data_source.get() == ('cxc',)

    with pytest.raises(ValueError) as err:
        fetch.data_source.set('blah')
    assert 'data_sources' in str(err)


@pytest.mark.skipif("not HAS_MAUDE")
def test_maude_data_source():
    """Fetch data from MAUDE"""
    with fetch.data_source('cxc'):
        datc = fetch.Msid('aogyrct1', date1, date3)
        assert len(datc.vals) == 19
        assert datc.data_source == {'cxc': ('2016:001:00:00:00.287', '2016:001:00:00:04.900')}

    with fetch.data_source('maude'):
        datm = fetch.Msid('aogyrct1', date1, date3)
        assert np.all(datm.vals == datc.vals)
        assert not np.all(datm.times == datc.times)
        assert datm.data_source == {'maude': ('2016:001:00:00:00.203', '2016:001:00:00:04.815')}

    with fetch.data_source('cxc', 'maude', 'test-drop-half'):
        datcm = fetch.Msid('aogyrct1', date1, date3)
        assert np.all(datcm.vals == datc.vals)
        assert datcm.data_source == {'cxc': ('2016:001:00:00:00.287', '2016:001:00:00:02.337'),
                                     'maude': ('2016:001:00:00:02.509', '2016:001:00:00:04.815')}
