from .version import __version__, __git_version__


def test(*args, **kwargs):
    """
    Run py.test unit tests.  This requires a subpackage `tests` within
    the package.
    """
    import os
    import pytest

    # Goal is to change to the directory above the package location and
    # then do equivalent of something like `py.test Ska/engarchive ...`.
    # This will discover and run tests within the package directory.
    from . import tests
    pkg_names = tests.__name__.split('.')[:-1]
    pkg_paths = [os.path.dirname(__file__)] + ['..'] * len(pkg_names)
    os.chdir(os.path.join(*pkg_paths))
    pkg_dir = os.path.join(*pkg_names)

    return pytest.main([pkg_dir] + list(args), **kwargs)
