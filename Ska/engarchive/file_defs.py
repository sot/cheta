"""
Directory and file location definitions for telemetry archive applications.
This is to be used to define corresponding ContextDict objects.

'ft' is expected to be a ContexDict represent an archive file as well with
content (e.g. ACIS2ENG), msid (1PDEAAT), year, doy and basename (archive file
basename) defined.

Msid files are the hdf5 files containing the entire mission telemetry for one MSID.
Arch files are the CXC archive files containing a short interval of telemetry for
all MSIDs in the same content-type group (e.g. ACIS2ENG).
"""
import os

SKA = os.environ.get('SKA') or '/proj/sot/ska'
ENG_ARCHIVE = os.getenv('ENG_ARCHIVE') or SKA + '/data/eng_archive'

# Root directories for MSID files.  msid_root is prime, others are backups.
# NOTE: msid_root(s) used ONLY in one-off or legacy code, not in update_archive.py or
# transfer_stage.py
msid_root = os.path.join(SKA, 'data', 'eng_archive')
msid_roots = [msid_root]

msid_files = {'filetypes':    'filetypes.dat',
              'msid_bad_times': 'msid_bad_times.dat',
              'contentdir':   'data/{{ft.content}}/',
              'headers':      'data/{{ft.content}}/headers.pickle',
              'archfiles':    'data/{{ft.content}}/archfiles.db3',
              'colnames':     'data/{{ft.content}}/colnames.pickle',
              'colnames_all': 'data/{{ft.content}}/colnames_all.pickle',
              'msid':         'data/{{ft.content}}/{{ft.msid | upper}}.h5',
              'data':         'data/{{ft.content}}/{{ft.msid | upper}}.h5',
              'statsdir':     'data/{{ft.content}}/{{ft.interval}}/',
              'stats':        'data/{{ft.content}}/{{ft.interval}}/{{ft.msid | upper}}.h5',
              }


# NOTE: arch_root used ONLY in one-off or legacy code, not in update_archive.py or
# transfer_stage.py
arch_root = '/data/cosmos2/eng_archive'
arch_files = {'stagedir': 'stage/{{ft.content}}/',
              'rootdir': '',
              'archrootdir':  'data/{{ft.content}}/arch/',
              'archdir':      'data/{{ft.content}}/arch/{{ft.year}}/{{ft.doy}}/',
              'archfile':     'data/{{ft.content}}/arch/{{ft.year}}/{{ft.doy}}/{{ft.basename}}',
              }

# Used when originally creating database.
orig_arch_root = '/data/cosmos2/tlm'
orig_arch_files = {'contentdir':   '{{ft.content}}/'}
