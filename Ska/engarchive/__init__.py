# Licensed under a 3-clause BSD style license - see LICENSE.rst

from pkg_resources import get_distribution, DistributionNotFound

try:
    _dist = get_distribution('Ska.engarchive')  # hard-code only for this dual-name package
    __version__ = _dist.version

    # Check if this file is the same as what was found in the distribution.
    # Windows does not necessarily respect the case so downcase everything.
    assert __file__.lower().startswith(_dist.location.lower())

except (AssertionError, DistributionNotFound):
    try:
        # get_distribution found a different package from this file, must be in source repo
        from setuptools_scm import get_version
        from pathlib import Path

        root = Path('..')
        try:
            __version__ = get_version(root=root, relative_to=__file__)
        except LookupError:
            __version__ = get_version(root=root / '..', relative_to=__file__)

    except Exception:
        import warnings
        warnings.warn('Failed to find a package version, setting to 0.0.0')
        __version__ = '0.0.0'


def test(*args, **kwargs):
    '''
    Run py.test unit tests.
    '''
    import testr
    return testr.test(*args, **kwargs)
