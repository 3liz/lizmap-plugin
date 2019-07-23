# QGIS Plugin CI

Contains scripts to perform automated testing and deployment for QGIS plugins.
These scripts are written for and tested on GitHub, Travis-CI and Transifex.

 - Deploy plugin releases on QGIS official plugin repository
 - Publish plugin in Github releases, option to deploy a custom repository
 - Easily integrated in Travis-CI
 - Completely handle translations with Transifex: create the project and the languages, pull and push translations 
   
# Base functionality

## Command line

```commandline
usage: qgis-plugin-ci [-h] [-v]
                      {package,release,pull-translation,push-translation} ...

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         print the version and exit

commands:
  qgis-plugin-ci command

  {package,release,pull-translation,push-translation}
    package             creates an archive of the plugin
    release             release the plugin
    pull-translation    pull translations from Transifex
    push-translation    update strings and push translations
```

#### Package

```commandline
usage: qgis-plugin-ci package [-h] [--transifex-token TRANSIFEX_TOKEN]
                              release_version

positional arguments:
  release_version       The version to be released

optional arguments:
  -h, --help            show this help message and exit
  --transifex-token TRANSIFEX_TOKEN
                        The Transifex API token. If specified translations
                        will be pulled and compiled.
```

#### Release

```commandline
usage: qgis-plugin-ci release [-h] [--transifex-token TRANSIFEX_TOKEN]
                              [--github-token GITHUB_TOKEN]
                              [--create-plugin-repo]
                              [--osgeo-username OSGEO_USERNAME]
                              [--osgeo-password OSGEO_PASSWORD]
                              release_version

positional arguments:
  release_version       The version to be released

optional arguments:
  -h, --help            show this help message and exit
  --transifex-token TRANSIFEX_TOKEN
                        The Transifex API token. If specified translations
                        will be pulled and compiled.
  --github-token GITHUB_TOKEN
                        The Github API token. If specified, the archive will
                        be pushed to an already existing release.
  --create-plugin-repo  Will create a XML repo as a Github release asset.
                        Github token is required.
  --osgeo-username OSGEO_USERNAME
                        The Osgeo user name to publish the plugin.
  --osgeo-password OSGEO_PASSWORD
                        The Osgeo password to publish the plugin.
```

#### Pull translations

```commandline
usage: qgis-plugin-ci pull-translation [-h] transifex_token

positional arguments:
  transifex_token  The Transifex API token

optional arguments:
  -h, --help       show this help message and exit
```

#### Push translations

```commandline
usage: qgis-plugin-ci push-translation [-h] transifex_token

positional arguments:
  transifex_token  The Transifex API token

optional arguments:
  -h, --help       show this help message and exit
```

## QRC and UI files

- any .qrc file in the source top directory (plugin_path) will be compiled and output as filename_rc.py. You can then import it using ``import plugin_path.resources_rc``
- currently, qgis-plugin-ci does not compile any .ui file.

## Publishing plugins

When releasing, you can publish the plugin :

1. In the official QGIS plugin repository. You need to provide user name and password for your Osgeo account.
2. As a custom repository in Github releases and which can be added later in QGIS. The address will be: https://github.com/__ORG__/__REPO__/releases/latest/download/plugins.xml

## Automatic deployment on Travis

One can easily set up a deployment using Travis.

1. Add `qgis-plugin-ci` to `requirements.txt` or have `pip install qgis-plugin-ci` in `install` step.
2. Specify the environment variables required to connect to the different platforms (Osgeo, Github, Transifex). You can add them either using the Travis CLI with `travis encrypt` or use the web interface to add the variables.
3. Add a deploy step to release the plugin:

```
deploy:
  provider: script
  script: qgis-plugin-ci release ${TRAVIS_TAG} --github-token ${GH_TOKEN} --osgeo-username ${OSGEO_USERNAME} --osgeo-password {OSGEO_PASSWORD}
  on:
    tags: true
```

# Using Transifex to translate your plugin




# Advanced functionality

## Debug

In any Python module, you can have a global variable as `DEBUG = True`, which will be changed to `False` when packaging the plugin.

## Excluding files in the plugin archive

If you want to avoid some files to be shipped with your plugin, create a ``.gitattributes`` file in which you can specify the files to ignore. For instance:
```
resources.qrc export-ignore
```

# Sample plugins

* https://github.com/VeriVD/qgis_VeriVD

  
