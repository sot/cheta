# Licensed under a 3-clause BSD style license - see LICENSE.rst
import shutil
import sys
import os
from setuptools import setup
from setuptools.command.test import test as TestCommand

from Ska.engarchive.version import package_version

try:
    from testr.setup_helper import cmdclass
except ImportError:
    cmdclass = {}

# Write GIT revisions and SHA tag into <this_package/git_version.py>
# (same directory as version.py)
package_version.write_git_version_file()

# On Windows the `cheta` soft link can turn into a plain file, so work
# around this by temporarily moving that file to the side and doing a
# full tree copy of Ska/engarchive => cheta.
replace_cheta = sys.platform.startswith('win') and os.path.isfile('cheta')

try:
    if replace_cheta:
        os.rename('cheta', 'cheta-TEMPORARY')
        shutil.copytree(os.path.join('Ska', 'engarchive'), 'cheta')

    setup(name='Ska.engarchive',
          author='Tom Aldcroft',
          description='Modules supporting Ska engineering telemetry archive',
          author_email='aldcroft@head.cfa.harvard.edu',
          entry_points={'console_scripts': ['ska_fetch = Ska.engarchive.get_telem:main']},
          version=package_version.version,
          zip_safe=False,
          packages=['Ska', 'Ska.engarchive', 'Ska.engarchive.derived', 'Ska.engarchive.tests',
                    'cheta', 'cheta.derived', 'cheta.tests'],
          package_data={'Ska.engarchive': ['*.dat', 'units_*.pkl', 'GIT_VERSION'],
                        'Ska.engarchive.tests': ['*.dat'],
                        'cheta': ['*.dat', 'units_*.pkl', 'GIT_VERSION'],
                        'cheta.tests': ['*.dat']},

          tests_require=['pytest'],
          cmdclass=cmdclass,
          )

finally:
    if replace_cheta:
        shutil.rmtree('cheta')
        os.rename('cheta-TEMPORARY', 'cheta')
