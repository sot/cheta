from distutils.core import setup
from grace.version import version

setup(name='grace',
      author='Tom Aldcroft',
      description='Modules supporting Ska engineering telemetry archive',
      author_email='aldcroft@head.cfa.harvard.edu',
      py_modules=['grace.fetch', 'grace.converters', 'grace.utils'],
      version=version,
      zip_safe=False,
      packages=['grace', 'grace.derived', 'grace.tests'],
      package_data={'grace': ['*.dat', 'units_*.pkl'],
                    'grace.tests': ['*.dat']},
      )
