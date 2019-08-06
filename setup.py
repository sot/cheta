# Licensed under a 3-clause BSD style license - see LICENSE.rst
import sys
import glob
import os

from setuptools import setup

from Ska.engarchive.version import package_version

try:
    from testr.setup_helper import cmdclass
except ImportError:
    cmdclass = {}

# Write GIT revisions and SHA tag into <this_package/git_version.py>
# (same directory as version.py)
package_version.write_git_version_file()

console_scripts = ['ska_fetch = cheta.get_telem:main',
                   'cheta_update_client_archive = cheta.update_client_archive:main',
                   'cheta_update_server_sync = cheta.update_server_sync:main'
                   'cheta_update_server_archive = cheta.update_archive:main',
                   'cheta_check_integrity = cheta.check_integrity:main',
                   'cheta_fix_bad_values = cheta.fix_bad_values:main']

# Install following into sys.prefix/share/eng_archive/ via the data_files directive.
if "--user" not in sys.argv:
    share_path = os.path.join(sys.prefix, "share", "eng_archive")
    task_files = glob.glob('task_schedule*.cfg')
    data_files = [(share_path, task_files)]
else:
    data_files = None

setup(name='Ska.engarchive',
      author='Tom Aldcroft',
      description='Modules supporting Ska engineering telemetry archive',
      author_email='taldcroft@cfa.harvard.edu',
      entry_points={'console_scripts': console_scripts},
      version=package_version.version,
      zip_safe=False,
      package_dir={'Ska': 'Ska', 'cheta': 'Ska/engarchive'},
      packages=['Ska', 'Ska.engarchive', 'Ska.engarchive.derived', 'Ska.engarchive.tests',
                'cheta', 'cheta.derived', 'cheta.tests'],
      package_data={'Ska.engarchive': ['*.dat', 'units_*.pkl'],
                    'Ska.engarchive.tests': ['*.dat'],
                    'cheta': ['*.dat', 'units_*.pkl'],
                    'cheta.tests': ['*.dat']},
      data_files=data_files,
      tests_require=['pytest'],
      cmdclass=cmdclass,
      )
