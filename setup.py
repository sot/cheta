from setuptools import setup
setup(name='Ska.engarchive',
      author = 'Tom Aldcroft',
      description='Modules supporting Ska engineering telemetry archive',
      author_email = 'aldcroft@head.cfa.harvard.edu',
      py_modules = ['Ska.engarchive.fetch', 'Ska.engarchive.converters', 'Ska.engarchive.utils'],
      version='0.12',
      zip_safe=False,
      namespace_packages=['Ska'],
      packages=['Ska', 'Ska.engarchive'],
      package_dir={'Ska' : 'Ska'},
      package_data={'': ['units_*.pkl']},
      )
