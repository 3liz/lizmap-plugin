## Install lizmap api as standadrd python package

from setuptools import setup

kwargs = {}

# Read tag from metadata

import configparser
metadata = configparser.ConfigParser()
metadata.read('metadata.txt')

version_tag = metadata['general']['version'].replace("version","").strip()

with open('README.md') as f:
    kwargs['long_description'] = f.read()

setup(
    name='lizmap-api',
    version=version_tag,
    author='3Liz',
    author_email='infos@3liz.org',
    maintainer='Michael Douchin',
    maintainer_email='mdouchin@3liz.org',
    description="Python API to create lizmap configuration",
    url='https://github.com/3liz/lizmap-plugin',
    packages=['lizmap_api'],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    **kwargs
)

