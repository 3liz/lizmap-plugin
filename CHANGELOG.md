# CHANGELOG

## Version 3.0.1

* [FEATURE] auto add the link from metadataUrl in QGIS
* [FEATURE] Api: new class to get lizmap JSON config from project
* [FEATURE] Add open cycle map as base layer
* Dataviz - Fix plot type localized list
* Update popup max features maximum constraint to 199
* Fix - Enable popup configuration of a project layer
* Add command line tool for generating config with API
* Add a warning about losing Z M values
* Install lizmap api as standard python package
* Add Brazilian, Dutch, Hungarian, Norwegian, Romanian, Czech and Slovenian locales
* Update locales German, French, Italian, Polish, Swedish and Hungarian

## Version 3.0.0

* First version of lizmap plugin for QGIS 3 created from the version 2.4.1 for QGIS 2

## Version 2.4.1

* Do not save project from lizmap plugin but let the user do it
* Fix icons in plugin manager, remove unused imports
* UI - fix issue with qgscollapsiblegroupbox import
* Update locales
* Change of default mode of popup source to 'auto'
* Dataviz - add of a button in Dataviz who permit you to hide parent plot

## Version 2.4.0

This version add new features which are only usable with upcoming Lizmap Web Client 3.2.*

* [FEATURE] Dataviz - new tool to add charts based on layers data
* [FEATURE] Dataviz - Add an option to display the child plot filtered in parent layer popup
* [FEATURE] Dataviz - Add an option to group the values: sum, count, average, etc.
* [FEATURE] Popup - Allow to use popup in bottom dock or in right dock
* [BUGFIX] Fix bug when the layer scale is not set
* [BUGFIX] Support MySQL Layer
* [FEATURE] Dataviz - Add a field to enter a HTML template for plot positionning
* [BUGFIX] Python - replace modules import *
* [FEATURE] New Atlas tool to navigate through a layer features
* [FEATURE] Configure the amount of features per layer displayed in popup
* [BUGFIX] Allow layers with datasource starting with HTTP
* Update locales
* [BUGFIX] Baselayers - fix get startup baselayer from project #56



## Version 2.3.0

* Interface - Improve look & feel

## Version 2.2.0

This version add new features which are only usable with upcoming Lizmap Web Client 3.1

* Interface - Add toolips and blue background for new features
* Plugin - Improve makefile for transup and transcompile
* Attribute table - Option to fetch data only within map extent && layer scale visibility
* Tools layer limit linked to combobox size
* Map - fix bug with startup baselayer for accentuated layers/groups
* UI - fix issue with qgscollapsiblegroupbox import
* Editing - Add option to pass list of groups to restrict editing for each layer
* Locales - Add Euskara and Swedish, update other languages
* Add Stamen Toner external baselayer (and remove Maquest and OSM CycleMap)
* Popup - Option to display related children under each parent object
* Attribute table - Add an option to hide the layer in the list (first tab of attribute table tool)
* Add an option to restrict access to project for given groups
* Interface - Reorganize layers options

## Version 2.1.2

* Add locales: Finnish, Galician
* Update locales: Portuguese, Russian


## Version 2.1.1

* Add and update locales: English, Spanish, German, French, Russian, Polish, Italian, Portuguese, Greek
* Menu - Change menu label from LizMap to Lizmap
* Baselayers - Get the startup baselayer from configuration #56
* Layers - Enable WMS checkbox only for WMS layers
* Remove option to transform groups as legend blocks #57

## Version 2.1.0

This version add new features which are only usable with upcoming Lizmap Web Client 3.0.

  * Baselayers - Choose active baselayer at map startup
  * Map - Add options to configure tolerances for popup activation in pixels
  * Layers - New option to choose popup source: auto, lizmap advanced or QGIS maptip
  * Map - New map option to choose info popup container: dock, mini-dock or map
  * Tools - Allow virtual fields in layer fields comboboxes

## Version 2.0.0

* Add more options to Attribute layer tools ( compatible with Limap Web Client >= 3.0 : QGIS relations support, filter, export, search, selection
* Add new Tooltip tool (compatible with LWC >= 3.0 )
* Advance popup dialog with colored syntax ( thanks to @slarosa )
* Disable FTP tab : we advise users to use a real FTP client instead (Filezilla for example )
* Locate by layer - Add an option to trigger a filter on selected item  (compatible with LWC >= 3.0 )
* Layers - Set default value to True for option 'Hide group checkboxes'
* Layers - use Single Tile option by default at startup
* Support multiple styles for a layer (compatible with LWC >= 3.0 )
* Handle layers with no geometry to be used for attribute table and edition tools
* Minor UI improvements

## Version 1.9.10

* Close Lizmap plugin when a new project is loaded - fixes #35
* Feature - add option to filter layers and data by authenticated user login (and not only by group as previously)
* Feature - New tool to display attribute tables for vector layers
* Map - add options to hide some interface items - funded by CIRAD - Environnements et Sociétés
* Layers - Option to hide groups checkboxes in legend - funded by CIRAD - Environnements et Sociétés
* Translation - Add Greek language file thanks to Arnaud Deleurme

## Version 1.9.9

* [BUGFIX] #22 Ask the user to deactivate Layer name capitalization in QGIS option
* Improve management of layers option tables such as "Locate by Layers" (remove layers from table if not in the project anymore or if removed during work session, rename layer in the table when renamed from the project)
* Minor GUI modifications in the Layers tab to improve readibility
* Add minLength option for Locate by layer

## Version 1.9.8

* Speed up lizmap start (was bad since embedded layers feature)
* New feature - hide layer in Legend but displayed in map
* External baselayer - Add Osm Cyclemap
* Lizmap external baselayers - add image format option

## Version 1.9.7

* Baselayers - option to add an empty baselayer with project background color - #25
* Change default scales list in Map tab (add 10k and 50k)
* Automatic configuration for some Project parameters : title, advertised extent, EPSG:3857 if needed
* Italian translation - Build qm file
* IT translation
* Adress Search - Add Google and IGN (france) API
* Option to get tiles directly from WMS server for external WMS layers
* Manage embedded groups and layers - allow to configure lizmap repository
* Layers - add option to call directly external WMS layers
* Edition - allow to have 10 editable layers (instead of 5)
* Option to hide legend image for a layer
* Configuration file - do not order alphabetically to keep layers order
* Avoid error when layer has no provider type (e.g. OpenLayers plugin)

## Version 1.9.6

* Tools - Add "time manager" optional tool to animate vector layers based on date/time attribute
* Map - add option to hide the project in LizmapWebClient
* Baselayers - option to add external Lizmap project layers as baselayers
* Table widgets - refactor code to retrieve options from json config
* Baselayers - Add OpenCycleMap, IGN (plan, aerial, scans), Bing Maps

## Version 1.9.5.1

* Locate by layer - debug : Do not save filterFieldName if not set ( "--" )

## Version 1.9.5

* Locate by layer - add optional group field to create parent category filter
* New option : set the initial map extent at map loading
* Debug: remove old sip api translation methods
* Translation : corrections for english translation (by @ewsterrenburg )

## Version 1.9.4.1

* Debug filterByLogin configuration reading

## Version 1.9.4

* Remove python module simplejson dependancy (replaced by module json)
* New tool : filter layer data based on authenticated user

## Version 1.9.3

* Minor fixes after new SIP api migration

## Version 1.9.2

* Complete migration to QGIS 2.0. The plugin is not compatible with QGIS version < 2.0 anymore
* Remove message box for Linux users when lftp not installed
* Help button and menu item now lead to an external web help page

## Version 1.9.1

* Save the FTP remote dir per each QGIS project, not globally
* Force toggle between Single Tile and Server cache
* Debug inactive dialog tab when no FTP sync possibility: deactivate FTP, not Tools
* Italian translation update

## Version 1.9.0

* New feature : edition tool which replaces the annotation tool.
* Update translations
* Design: add scroll areas to allow users to resize the dialog for small screens

## Version 1.8.0

* New tools : annotations, locate by layer, simple print, address search, zoom history, measure, etc.
* New layer option - Configure Client browser Cache expiration
* Redesign the UI with group boxes (thanks to Salvatore Larrosa)
* Bug fix - fix global options with checkboxes which were reused for next opened QGIS project
* New Vector api merge - adapt Lizmap code
* Change the way relative path are tracked
* Change needed projection 4 external layers: 900913(deprecated)->3857
* Bug fix : error handling when using lizmap on windows with multiple drives

## Version 1.7.2

* Improvement: Allow the user to use layers from a parent folder or a brother folder of the root project folder. Can be used to have a Data folder at the same level of the repositories.
* Bug Fix: Fix the toggled option for layers wich was always on
* Bug Fix: Winscp - a password can be empty if the winScp session field is filled.

## Version 1.7.1

* Improvement: Allow the user to choose a WinSCP pre-saved session. Can be used to deal with TLS connections.
* Improvement: Allow the user to choose the winSCP mirror criteria : between 'size' and 'time'
* Improvement: LFTP (linux only) automatically accepts SSL certificate

## Version 1.7.0

* New feature: Popup - add a checkbox to enable/disable popup for each layer
* New feature: Ability to write templates for popup
* Bug fix:  Project properties - checks the BBOX is really set in the OWS tab.
* Bug fix: FTP windows sync - protect the winscp path with double quote when running the sync

## Version 1.6.1

* Bug fix : correctlu use layer.setAbstract instead of setTitle to set back the abstract

## Version 1.6.0

* New : addition of more cache parameters : cache expiration and metatile
* Enhancement : Heavy refactoring of the code ("data driven") to easy addition of new layers properties.

## Version 1.5.0

* New : translation into Italian, thanks to Salvatore Larosa (@lrssvt)
* Debug : Groups as layer was not remembered since v1.4.0

## Version 1.4.0

* New : check that the project title is correctly defined in the project properties dialog, tab OWS
* Improvement : Interface - automatic widgets resizing thanks to Salvatore Larosa @lrssvt

## Version 1.3.0

* New feature : Choose the image type (png, png 8bit or jpeg) for each layer and not globally anymore

## Version 1.2.2

* Bug fix : type which prevented from synchronizing over FTP

## Version 1.2.1

* New : Get layer title and abstract from Qgis layer properties (for qgis >= 1.8)
* Refactoring : method to populate the plugin layer tree
* Bug fix : add missing i18n *.qm translation files

## Version 1.2.0

* New : support for plugin internationalization : english and french languages available
* Modify : integrate Lizmap in the Qgis Web menu
* Modify : remove warning dialog when closing Lizmap window and auto-save the configuration
* Modify : move help and about dialogs to the plugin Menu
* Bug fix : error when the sync button is pressed and no sync was running

## Version 1.1.1

* bug correction : closing window and reopening it led to plugin actions launched several times (e.g. save button)
* check if lizmap window is hidden and warn the user (which put lizmap window in the front)
* add a question to save lizmap configuration when closing the window
* clean the json export of lizmap project configuration (e.g. escaping double quotes) : use of simplejson.dumps() method

## Version 1.1

* addition of Google and OpenStreetMap public baselayers option in the "Map" tab
* ignore non-geometric vector layers
* only one lizmap plugin window available at a time
