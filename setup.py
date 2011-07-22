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

_data_files = [
    ('share/man/man1', ['docs/man/man1.txt']),
    ('share/doc/melissi', ['CHANGES',
                           'LICENCE',
                           'README.org']
     ),
    ('share/icons/scalable/apps', ['melissi/data/icons/scalable/apps/melissi.svg']),
    ('share/applications', ['melissi/data/share/applications/melissi.desktop']),
    ]

setup(
    name = 'melissi',
    version = version_string,
    author = 'Giorgos Logiotatidis',
    author_email = 'seadog@sealabs.net',
    maintainer = 'Tasos Katsoulas',
    maintainer_email = 'akatsoulas@gmail.com',
    url = 'http://www.melissi.org',
    license = 'LICENCE.txt',
    keywords = ['file synchronization', 'cloud storage', 'client', 'python'],
    description = 'Cloud Storage Client',
    # long_description = open('README.txt').read(),

    # TODO classifiers for the Pypi
    # package_dir = {'melissi':'melissi'},
    packages = ['melissi','melissi.actions'],
    package_data = {'melissi':['data/pixmaps/*.svg',
                               'data/glade/*',
                               ]
                    },
    # ext_modules= [Extension('melissi._librsyncmodules',
    #                         ['_librsyncmodule.c'],
    #                         include_dirs,
    #                         libraries=["rsync"]
    #                         )
    #               ],
    data_files = _data_files,
    entry_points = {
        'console_scripts':['melissi = melissi.melissi_client:main',
		'cmelissi = melissi.cmelissi:main']
        
        },
    install_requires=['Twisted', 'storm']
)
