from setuptools import setup
from Ska.engarchive.version import version

setup(name='Ska.engarchive',
      author='Tom Aldcroft',
      description='Modules supporting Ska engineering telemetry archive',
      author_email='aldcroft@head.cfa.harvard.edu',
      py_modules=['Ska.engarchive.fetch', 'Ska.engarchive.converters', 'Ska.engarchive.utils'],
      version=version,
      zip_safe=False,
      namespace_packages=['Ska'],
      packages=['Ska', 'Ska.engarchive', 'Ska.engarchive.derived', 'Ska.engarchive.tests'],
      package_dir={'Ska': 'Ska'},
      package_data={'Ska.engarchive': ['*.dat', 'units_*.pkl'],
                    'Ska.engarchive.tests': ['*.dat']},
      )

setup(name='sken',
      author='Tom Aldcroft',
      description='Modules supporting Ska engineering telemetry archive',
      author_email='aldcroft@head.cfa.harvard.edu',
      py_modules=['sken.fetch', 'sken.converters', 'sken.utils'],
      version=version,
      zip_safe=False,
      packages=['sken', 'sken.derived', 'sken.tests'],
      package_data={'sken': ['*.dat', 'units_*.pkl'],
                    'sken.tests': ['*.dat']},
      )
