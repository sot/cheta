import os
import platform
from setuptools import setup

from Ska.engarchive.version import package_version

# Write GIT revisions and SHA tag into <this_package/git_version.py>
# (same directory as version.py)
package_version.write_git_version_file()


if platform.system() in ('Darwin', 'Linux'):
    if not os.path.exists('sken'):
        os.symlink('Ska/engarchive', 'sken')

    setup(name='sken',
          author='Tom Aldcroft',
          description='Modules supporting Ska engineering telemetry archive',
          author_email='aldcroft@head.cfa.harvard.edu',
          py_modules=['sken.fetch', 'sken.converters', 'sken.utils', 'sken.get_telem'],
          version=package_version.version,
          zip_safe=False,
          packages=['sken', 'sken.derived', 'sken.tests'],
          package_data={'sken': ['*.dat', 'units_*.pkl', 'GIT_VERSION'],
                        'sken.tests': ['*.dat']},
          )

setup(name='Ska.engarchive',
      author='Tom Aldcroft',
      description='Modules supporting Ska engineering telemetry archive',
      author_email='aldcroft@head.cfa.harvard.edu',
      entry_points={'console_scripts': ['ska_fetch = Ska.engarchive.get_telem:main']},
      py_modules=['Ska.engarchive.fetch', 'Ska.engarchive.converters', 'Ska.engarchive.utils',
                  'Ska.engarchive.get_telem'],
      version=package_version.version,
      zip_safe=False,
      namespace_packages=['Ska'],
      packages=['Ska', 'Ska.engarchive', 'Ska.engarchive.derived', 'Ska.engarchive.tests'],
      package_dir={'Ska': 'Ska'},
      package_data={'Ska.engarchive': ['*.dat', 'units_*.pkl', 'GIT_VERSION'],
                    'Ska.engarchive.tests': ['*.dat']},
      )
