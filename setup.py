# Licensed under a 3-clause BSD style license - see LICENSE.rst
import glob
import os
import sys

from setuptools import setup

try:
    from testr.setup_helper import cmdclass
except ImportError:
    cmdclass = {}

console_scripts = [
    "ska_fetch = cheta.get_telem:main",
    "cheta_sync = cheta.update_client_archive:main",
    "cheta_update_server_sync = cheta.update_server_sync:main",
    "cheta_update_server_archive = cheta.update_archive:main",
    "cheta_check_integrity = cheta.check_integrity:main",
    "cheta_fix_bad_values = cheta.fix_bad_values:main",
    "cheta_add_derived = cheta.add_derived:main",
]

# Install following into sys.prefix/share/eng_archive/ via the data_files directive.
if "--user" not in sys.argv:
    share_path = os.path.join("share", "eng_archive")
    task_files = glob.glob("task_schedule*.cfg")
    data_files = [(share_path, task_files)]
else:
    data_files = None

# Duplicate Ska.engarchive packages and package_data to cheta
packages = ["Ska", "Ska.engarchive", "Ska.engarchive.derived", "Ska.engarchive.tests"]
for package in list(packages)[1:]:
    packages.append(package.replace("Ska.engarchive", "cheta"))

package_data = {
    "Ska.engarchive": ["*.dat", "units_*.pkl", "archfiles_def.sql"],
    "Ska.engarchive.tests": ["*.dat"],
}
for key in list(package_data):
    cheta_key = key.replace("Ska.engarchive", "cheta")
    package_data[cheta_key] = package_data[key]

setup(
    name="Ska.engarchive",
    author="Tom Aldcroft",
    description="Modules supporting Ska engineering telemetry archive",
    author_email="taldcroft@cfa.harvard.edu",
    entry_points={"console_scripts": console_scripts},
    use_scm_version=True,
    setup_requires=["setuptools_scm", "setuptools_scm_git_archive"],
    zip_safe=False,
    package_dir={"Ska": "Ska", "cheta": "Ska/engarchive"},
    packages=packages,
    package_data=package_data,
    data_files=data_files,
    tests_require=["pytest"],
    cmdclass=cmdclass,
)
