# QGIS Plugin CI

Contains scripts to perform automated testing and deployment for QGIS plugins.
These scripts are written for and tested on GitHub, Travis-CI and Transifex.

## Base functionality

 - Deploy plugin releases on QGIS official plugin repository
 - Publish plugin in Github releases, option to deploy a custom repository
 - Easily integrated in Travis-CI
 - Completely handle translations with Transifex: create the project and the languages, pull and push translations 
   
# Quickstart guide

 
# QRC and UI files

- any .qrc file in the source top directory (plugin_path) will be compiled and output as filename_rc.py. You can then import it using ``import plugin_path.resources_rc``
- currently, qgis-plugin-ci does not compile any .ui file.

# Debug

In any Python module, you can have a global variable as `DEBUG = True`, which will be changed to `False` when packaging the plugin.


# Activating unit tests


# Sample plugins

  
