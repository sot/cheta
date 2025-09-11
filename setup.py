# Licensed under a 3-clause BSD style license - see LICENSE.rst
from setuptools import setup
from ska_helpers.setup_helper import duplicate_package_info

console_scripts = [
    "ska_fetch = cheta.get_telem:main",
    "cheta_sync = cheta.update_client_archive:main",
    "cheta_update_server_sync = cheta.update_server_sync:main",
    "cheta_update_server_archive = cheta.update_archive:main",
    "cheta_check_integrity = cheta.check_integrity:main",
    "cheta_fix_bad_values = cheta.fix_bad_values:main",
    "cheta_add_derived = cheta.add_derived:main",
]


name = "cheta"
namespace = "Ska.engarchive"

package_dir = {name: name}
packages = ["cheta", "cheta.derived", "cheta.comps", "cheta.tests"]
package_data = {
    "cheta": ["task_schedule.cfg", "*.dat", "units_*.pkl", "archfiles_def.sql"],
    "cheta.tests": ["*.dat", "data/*.stk"],
}

# Duplicate cheta packages and package_data to cheta
duplicate_package_info(packages, name, namespace)
duplicate_package_info(package_dir, name, namespace)
duplicate_package_info(package_data, name, namespace)

setup(
    name=name,
    author="Tom Aldcroft",
    description="Modules supporting cheta telemetry archive",
    author_email="taldcroft@cfa.harvard.edu",
    entry_points={"console_scripts": console_scripts},
    use_scm_version=True,
    setup_requires=["setuptools_scm", "setuptools_scm_git_archive"],
    zip_safe=False,
    package_dir=package_dir,
    packages=packages,
    package_data=package_data,
)
