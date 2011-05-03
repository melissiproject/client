import os
#from distutils.core import setup
#from distutils.extension import Extension
try:
    from setuptools  import setup, find_packages
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()

from distutils.command.build import build
from distutils.command.install_data import install_data

#TODO Os check
#compilers
#libraries paths
#TODO change to setuptools

include_dirs=[]
version_string='0.1.0'

<<<<<<< HEAD
_data_files = [('share/man/man1',
    ['docs/man/man1.txt']),
    ('share/doc/melissi',
	['CHANGELOG.txt',
	'LICENCE.txt',
	'README.txt'])
	]

setup(
    name='melissi',
    version='0.1.0',
    author='Logiotatidis Giorgos',
    author_email='seadog@sealabs.net',
    url='www.melissi.org',
    licence='GPLv3',
    keywords=['file synchronization','client','python'],
	description='File Synchronization client',
	long_description=open('README.txt').read(),

	#TODO classifiers for the Pypi
    data_files=_data_files,
	package_data = {'melissi':
        ['data/images/*.svg',
        'data/glade/*.glade',
        'data/glade/*.png',
		'data/glade/*.css',
		'data/glade/*.html']
        },
    packages = find_packages(exclude=['docs','data']),
#	ext_modules= [Extension('melissi._librsyncmodules',
#			['_librsyncmodule.c'],
#			include_dirs,
#			libraries=["rsync"])],
    entry_points = {'console_scripts':['melissi = melissi.melissi:main']},
=======
_data_files = [
    ('share/man/man1', ['docs/man/man1.txt']),
    ('share/doc/melissi', ['CHANGES.txt',
                           'LICENCE.txt',
                           'README.txt']
     )
    ]

setup(
    name='melissi',
    version=version_string,
    author='Giorgos Logiotatidis',
    author_email='seadog@sealabs.net',
    maintainer='Tasos Katsoulas',
    maintainer_email='akatsoulas@gmail.com',
    url='http://www.melissi.org',
    licence='LICENCE.txt',
    keywords=['file synchronization', 'cloud storage', 'client', 'python'],
    description='Cloud Storage Client',
    long_description=open('README.txt').read(),

    #TODO classifiers for the Pypi
    package_dir={'melissi':'melissi'},
    packages=['melissi','melissi.actions'],
    package_data = {'melissi':['data/images/*.svg',
                               'data/glade/*.glade',
                               'data/glade/*.png',
                               'data/glade/*.css',
                               'data/glade/*.html']},
    # ext_modules= [Extension('melissi._librsyncmodules',
    #                         ['_librsyncmodule.c'],
    #                         include_dirs,
    #                         libraries=["rsync"]
    #                         )
    #               ],
    data_files = _data_files,
    entry_points = {
        'console_scripts':['melissi = melissi.melissi.mail']
        },
>>>>>>> 01ece62fb67af917abc8fee706745eba0a537104
    )
