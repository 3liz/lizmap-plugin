from setuptools import setup
import sys

python_min_version=(3, 7)

if sys.version_info < python_min_version:
    sys.exit('qgis-plugin-ci requires at least Python version {vmaj}.{vmin}.\n'
             'You are currently running this installation with\n\n{curver}'.format(
        vmaj=python_min_version[0],
        vmin=python_min_version[1],
        curver=sys.version))

setup(
    name='qgis-plugin-ci',
    packages=[
        'qgispluginci'
    ],
    scripts=[
        'scripts/qgis-plugin-ci'
    ],
    package_data={'qgispluginci': ['plugins.xml.template']},
    include_package_data=True,  # required for files in MANIFEST.in
    version='__VERSION__',
    description='Let QGIS-plugin-ci package and release your QGIS plugins for you. Have a tea or go hiking meanwhile.',
    author='Denis Rouzaud',
    author_email='denis.rouzaud@gmail.com',
    url='https://github.com/opengisch/qgis-plugin-ci',
    download_url='https://github.com/opengisch/qgis-plugin-ci/archive/__VERSION__.tar.gz',
    keywords=['QGIS'],
    classifiers=[
        'Topic :: Scientific/Engineering :: GIS',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Information Technology',
        'Development Status :: 3 - Alpha'
    ],
    install_requires=[
        'python-slugify',
        'pyyaml',
        'pytransifex',
        'gitpython',
        'PyQt5',
        'PyGithub',
        'pyqt5ac'
    ],
    python_requires=">={vmaj}.{vmin}".format(vmaj=python_min_version[0], vmin=python_min_version[1]),
)
