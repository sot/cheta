from .version import __version__, __git_version__

def test(*args, **kwargs):
    from . import tests
    tests.test(*args, **kwargs)
