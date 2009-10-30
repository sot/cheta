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

# Root directories for MSID files.  Multiple dirs => multiple copies of archive.
# This is done for redundancy.
msid_root = '/data/baffin3/telem_archive/data'
# '/data/drivel/ska/eng_archive/data',

msid_files = {'contentdir':   '{{ft.content}}/',
              'headers':      '{{ft.content}}/headers.pickle',
              'archfiles':    '{{ft.content}}/archfiles.db3',
              'colnames':     '{{ft.content}}/colnames.pickle',
              'colnames_all': '{{ft.content}}/colnames_all.pickle',
              'msid':         '{{ft.content}}/{{ft.msid}}.h5',
              'data':         '{{ft.content}}/{{ft.msid}}.h5',
              }

arch_root = '/data/cosmos2/eng_archive/data'
arch_files = {'archrootdir':  '{{ft.content}}/arch/',
              'archdir':      '{{ft.content}}/arch/{{ft.year}}/{{ft.doy}}/',
              'archfile':     '{{ft.content}}/arch/{{ft.year}}/{{ft.doy}}/{{ft.basename}}',
              }

# Used when originally creating database.
orig_arch_root = '/data/cosmos2/tlm'
orig_arch_files = {'contentdir':   '{{ft.content}}/'}
