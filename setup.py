# Licensed under a 3-clause BSD style license - see LICENSE.rst
from setuptools import setup

try:
    from testr.setup_helper import cmdclass
except ImportError:
    cmdclass = {}

setup(name='Ska.engarchive',
      author='Tom Aldcroft',
      description='Modules supporting Ska engineering telemetry archive',
      author_email='aldcroft@head.cfa.harvard.edu',
      use_scm_version=True,
      setup_requires=['setuptools_scm'],
      entry_points={'console_scripts': ['ska_fetch = Ska.engarchive.get_telem:main']},
      zip_safe=False,
      package_dir={'Ska': 'Ska', 'cheta': 'Ska/engarchive'},
      packages=['Ska', 'Ska.engarchive', 'Ska.engarchive.derived', 'Ska.engarchive.tests',
                'cheta', 'cheta.derived', 'cheta.tests'],
      package_data={'Ska.engarchive': ['*.dat', 'units_*.pkl'],
                    'Ska.engarchive.tests': ['*.dat'],
                    'cheta': ['*.dat', 'units_*.pkl'],
                    'cheta.tests': ['*.dat']},

      tests_require=['pytest'],
      cmdclass=cmdclass,
      )
