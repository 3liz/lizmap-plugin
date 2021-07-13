# Changelog

## Unreleased

## 3.5.4 - 2010-07-13

* Fix the visibility used on container in QGIS Form with level upper than 1
* Server - Always log when there is a Python exception
* Server - Make the plugin compatible Python 3.5
* Server - Rename variable about conflict

## 3.5.3 - 2010-07-05

* Refactor some imports and class names in the server part

## 3.5.2 - 2010-06-23

* Fix an issue on QGIS Desktop about a Python exception again

## 3.5.1 - 2021-06-23

* Fix an issue on QGIS Desktop about a Python exception
* Fix an issue on QGIS Server about primary keys not using integers

## 3.5.0 - 2021-06-21

* New "form" popup type for a vector layer using straight the Drag&Drop form layout 
  (Lizmap Web Client 3.5 and Lizmap plugin on the server side are needed)
* Files have chmod 755 by default to make it easier to deploy on a server

## 3.4.4 - 2021-04-01

* Add a link to open the online help for each edition form
* Fix some users experience issues
  * Read only checkbox was not obvious
  * Wrong warning about QGIS Desktop version in the CFG file
* Fix a Python exception if no layer was compatible for the edition capabilities
* Some minor updates on the Lizmap plugin server side

## 3.4.3 - 2021-03-03

* Fix loading the plugin on QGIS < 3.10

## 3.4.2 - 2021-03-02

* Disable some French IGN layers if some API keys are provided
* Add a warning according to :
  * the QGIS Desktop version and LWC target version if needed
  * the previous QGIS Desktop version which was used and ask to check QGIS Server if necessary
* Add a button to have the online help from the QGIS native help menu

## 3.4.1 - 2021-02-25

* Fix time manager widgets behavior
* Add project validity and QGIS desktop version in the metadata section
* Fix open in web browser external links

## 3.4.0 - 2020-12-30

* Server - Re-enable Lizmap expression filtering on server, follow up #321
* UX - Review tooltip sentence in edition 
* Fix #323 inverted checkbox in layer edition 
* CFG - Increase performance if using Lizmap Web Client >= 3.4.0. 
  You should re-generate the Lizmap configuration for (by clicking the edit button to add these new keys)
  * layer edition capabilities
  * layer attribute table
* Feature - Add new information panel about user server

## 3.3.2 - 2020-12-10

* Server, fix an issue about layer filtering with access control
* Make links clickable to open a Lizmap Web Client release
* Increase the limit of max children features in a parent popup
* Add layer provider name automatically for the edition tool (LWC >= 3.3.13)

## 3.3.1 - 2020-12-02

* Fix issue when reading the legend
* Fix issue about the Lizmap version selector
* Fix reading UTF8 in the metadata.txt

## 3.3.0 - 2020-11-25

* Add support for Lizmap Web Client 3.4 :
  * Add Lizmap as a QGIS Server side plugin to evaluate QGIS Expression from Lizmap Web Client
    * Group visibility
    * Default value
    * Constraint
    * Form drilldown using Value Relation widget
  * Allow multiple Lizmap atlas
  * Add option for layer visibility according to a Lizmap group
  * Add option to activate the first map theme defined in QGIS
  * Improvements about the Dataviz
    * Add description
    * A chart can now have a multiple Y fields
    * Add Sunburst chart (and Z field)
    * Add HTML template chart
    * Add stacked and horizontal options for a bar chart
    * Add option to display the legend
    * Add black/light theme
    * Add option to display the chart only if the layer is visible
    * Dataviz can be customized with a JSON object
  * Improvements about the Time Manager
    * Review the settings
    * Add buttons to compute min/max values
  * Improvements about the Edition
    * Add options to snap on layers
    * Set tolerance for snapping
    * Add option to allow geometryless feature
  * Access rights
    * Add option to filter by user for edition only
    * Add option to hide a layer for some groups
  * Map tools
    * Add option to enable or not drawing tools
* User experience :
  * Disable the "toggled" option for groups
  * Add a version feed to be aware of new versions of Lizmap Web Client

## 3.2.18 - 2020-09-07

* Add missing translations coming from UI files
* Enable QGIS Popup if QGIS ⩾ 3.10
* Do not generate the QGIS Popup if the form contains an invalid input widget
* Fix display of the Drag&Drop form button

## 3.2.17 - 2020-08-14

* Fix and improve the UX when setting up a popup

## 3.2.16 - 2020-07-28

* Fix an issue about copying Drag&Drop from to the maptip

## 3.2.15 - 2020-07-27

* Fix bug when the user set a link on a layer
* Add a button to fetch the dataUrl in the layer properties and fill the link
* Add some checks about the layer geometry type

## 3.2.14 - 2020-07-01

* Check project validity when running with QGIS 3.14
* Change icon for group in the layer tree
* Review some HIG guidelines
* Some small code cleanup

## 3.2.13 - 2020-05-06

* Fix bug about Box chart without aggregation
* Fix bug when removing a layer from the legend and the layer was in the Lizmap configuration too
* Improve continuous integration

## 3.2.12 - 2020-04-03

* Fix bug about popup QGIS using the drag&drop layout
* Improve the plugin management for releasing the plugin

## 3.2.11 - 2020-03-19

* Escape characters in tooltips (drag and drop form)
* Fix horizontal expanding of the layer list
* Fix on group visibility expression in Drag&Drop form
* Improve UI for Histogram 2D in Dataviz
* Improve continuous integration

## 3.2.10 - 2020-03-09

* Conditional display expression for tabs in drag&drop tooltip
* Improve form validation when a field is required
* Add missing icons in dataviz panel
* Fix default color when editing a row
* Add feature ID in tabs when using drag&drop tooltip
* Fix inverted HStore in valuemap when using drag&drop tooltip
* Allow double click in table for editing

## 3.2.9 - 2020-03-03

* Work on ValueMap widget

## 3.2.8 - 2020-03-03

* Fix using the plugin with QGIS 3.10
* Refactoring the code about drag&drop forms layout
* Move up/down tooltip layers
* Alternate row colors in all tables

## 3.2.7 - 2020-02-24

* Refactor dataviz to be editable
* Warn the user if there is an existing tooltip when using drap/drop layout
* Add a Lizmap Web Client version combobox
* Use icons in enums when possible

## 3.2.6

* Refactor form filter to be editable
* Some UX issues with table headers
* Fix missing translations
* Display field alias when possible
* Disable color in tooltip if disabled

## 3.2.5

* Fix Python syntax
* Refactor Time Manager panel to be editable

## 3.2.4

* Display color in table
* Re-enable color button
* Switch to a list to select fields

## 3.2.3

* Fix crash about color button

## 3.2.2:

* Fix bug about the new form with locate by layer #210
* Refactor Edition panel to be editable
* Refactor Attribute Table panel to be editable
* Refactor Tooltip panel to be editable
* Fix compulsory field in Filter by login

## 3.2.1

* Remove experimental from 3.2.0
* Refactor Locate by layer to be editable
* Refactor Filter by login to be editable
* Remove Lizmap submenu for help and about

## 3.2.0

* Version experimental
* Add tooltip about the layer name
* Add support for editing existing rows in atlas panel
* Some code cleanup about UI connections

## 3.1.8

* Review button box
* Add apply and close button
* Move back embedded layer and group from another project
* Add icon for add/remove button
* Add checkable fields input in forms
* Add autosave project option
* Fix add new layer without fields
* Fix typo
* Some code cleanup

## 3.1.7

* Fix some tooltips
* Fix allow empty field X in dataviz

## 3.1.6

* Add a lot of tooltips in forms
* Fix icon in the menu about logs and form filtering
* Add icons to plots in combobox

## 3.1.5

* Improve UX when editing layer with a form filter

## 3.1.4

* [Bugfix] In build tooltip from Drag and Drop form, outside fields are not outside tabs
* [Bugfix] With QgsFieldComboBox use currentField instead of currentText
* Add icon to Lizmap menu
* Fix unicode in TS files
* check QGZ files when we open lizmap (#171)
* Add travis
* Some code refactoring
* Move Popup code to its own file
* Fix wrong stylesheet
* Improve UX for the user about popup and server cache
* Remove ghost layer
* Remove Qt resource file

## 3.1.3

* Remove limitation of two layers in the locate tool
* Add icons for layers
* Remove legacy code

## 3.1.2

* Fix adding more than one layer into the edition tool
* Disable edit triggers in all tables

## 3.1.1

* Fix Python error #153

## 3.1.0


* [FEATURE] Improve Lizmap API
* [FEATURE] Add French Address database BAN
* [FEATURE] Create HTML tooltip from drag&drop form
* [Bugfix] Fix QGIS widgets paths
* Improve the HTML tooltip form: get the represented value
* Use QGIS native maplayer combobox in panels (except base layer)
* Hide by default the external Lizmap project panel
* Code refactoring
* Update locales

## 3.0.3

* [FEATURE] Add new tool to configure Form filtering based on db layers
* automatic fix from PyCharm about PEP8
* review TAB order in QtDesigner

## 3.0.2

* Update Czech, Finnish, Hungarian, Spanish and Italian locales
* [Bugfix] dataviz plot aggregation localize list
* [Bugfix] support wms urls thet have parameters with no =
* [Bugfix] fix #122 with reversed min and maxscales

## 3.0.1

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

## 3.0.0

* First version of lizmap plugin for QGIS 3 created from the version 2.4.1 for QGIS 2

## 2.4.1

* Do not save project from lizmap plugin but let the user do it
* Fix icons in plugin manager, remove unused imports
* UI - fix issue with qgscollapsiblegroupbox import
* Update locales
* Change of default mode of popup source to 'auto'
* Dataviz - add of a button in Dataviz who permit you to hide parent plot

## 2.4.0

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



## 2.3.0

* Interface - Improve look & feel

## 2.2.0

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

## 2.1.2

* Add locales: Finnish, Galician
* Update locales: Portuguese, Russian


## 2.1.1

* Add and update locales: English, Spanish, German, French, Russian, Polish, Italian, Portuguese, Greek
* Menu - Change menu label from LizMap to Lizmap
* Baselayers - Get the startup baselayer from configuration #56
* Layers - Enable WMS checkbox only for WMS layers
* Remove option to transform groups as legend blocks #57

## 2.1.0

This version add new features which are only usable with upcoming Lizmap Web Client 3.0.

  * Baselayers - Choose active baselayer at map startup
  * Map - Add options to configure tolerances for popup activation in pixels
  * Layers - New option to choose popup source: auto, lizmap advanced or QGIS maptip
  * Map - New map option to choose info popup container: dock, mini-dock or map
  * Tools - Allow virtual fields in layer fields comboboxes

## 2.0.0

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

## 1.9.10

* Close Lizmap plugin when a new project is loaded - fixes #35
* Feature - add option to filter layers and data by authenticated user login (and not only by group as previously)
* Feature - New tool to display attribute tables for vector layers
* Map - add options to hide some interface items - funded by CIRAD - Environnements et Sociétés
* Layers - Option to hide groups checkboxes in legend - funded by CIRAD - Environnements et Sociétés
* Translation - Add Greek language file thanks to Arnaud Deleurme

## 1.9.9

* [BUGFIX] #22 Ask the user to deactivate Layer name capitalization in QGIS option
* Improve management of layers option tables such as "Locate by Layers" (remove layers from table if not in the project anymore or if removed during work session, rename layer in the table when renamed from the project)
* Minor GUI modifications in the Layers tab to improve readibility
* Add minLength option for Locate by layer

## 1.9.8

* Speed up lizmap start (was bad since embedded layers feature)
* New feature - hide layer in Legend but displayed in map
* External baselayer - Add Osm Cyclemap
* Lizmap external baselayers - add image format option

## 1.9.7

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

## 1.9.6

* Tools - Add "time manager" optional tool to animate vector layers based on date/time attribute
* Map - add option to hide the project in LizmapWebClient
* Baselayers - option to add external Lizmap project layers as baselayers
* Table widgets - refactor code to retrieve options from json config
* Baselayers - Add OpenCycleMap, IGN (plan, aerial, scans), Bing Maps

## 1.9.5.1

* Locate by layer - debug : Do not save filterFieldName if not set ( "--" )

## 1.9.5

* Locate by layer - add optional group field to create parent category filter
* New option : set the initial map extent at map loading
* Debug: remove old sip api translation methods
* Translation : corrections for english translation (by @ewsterrenburg )

## 1.9.4.1

* Debug filterByLogin configuration reading

## 1.9.4

* Remove python module simplejson dependancy (replaced by module json)
* New tool : filter layer data based on authenticated user

## 1.9.3

* Minor fixes after new SIP api migration

## 1.9.2

* Complete migration to QGIS 2.0. The plugin is not compatible with QGIS version < 2.0 anymore
* Remove message box for Linux users when lftp not installed
* Help button and menu item now lead to an external web help page

## 1.9.1

* Save the FTP remote dir per each QGIS project, not globally
* Force toggle between Single Tile and Server cache
* Debug inactive dialog tab when no FTP sync possibility: deactivate FTP, not Tools
* Italian translation update

## 1.9.0

* New feature : edition tool which replaces the annotation tool.
* Update translations
* Design: add scroll areas to allow users to resize the dialog for small screens

## 1.8.0

* New tools : annotations, locate by layer, simple print, address search, zoom history, measure, etc.
* New layer option - Configure Client browser Cache expiration
* Redesign the UI with group boxes (thanks to Salvatore Larrosa)
* Bug fix - fix global options with checkboxes which were reused for next opened QGIS project
* New Vector api merge - adapt Lizmap code
* Change the way relative path are tracked
* Change needed projection 4 external layers: 900913(deprecated)->3857
* Bug fix : error handling when using lizmap on windows with multiple drives

## 1.7.2

* Improvement: Allow the user to use layers from a parent folder or a brother folder of the root project folder. Can be used to have a Data folder at the same level of the repositories.
* Bug Fix: Fix the toggled option for layers wich was always on
* Bug Fix: Winscp - a password can be empty if the winScp session field is filled.

## 1.7.1

* Improvement: Allow the user to choose a WinSCP pre-saved session. Can be used to deal with TLS connections.
* Improvement: Allow the user to choose the winSCP mirror criteria : between 'size' and 'time'
* Improvement: LFTP (linux only) automatically accepts SSL certificate

## 1.7.0

* New feature: Popup - add a checkbox to enable/disable popup for each layer
* New feature: Ability to write templates for popup
* Bug fix:  Project properties - checks the BBOX is really set in the OWS tab.
* Bug fix: FTP windows sync - protect the winscp path with double quote when running the sync

## 1.6.1

* Bug fix : correctlu use layer.setAbstract instead of setTitle to set back the abstract

## 1.6.0

* New : addition of more cache parameters : cache expiration and metatile
* Enhancement : Heavy refactoring of the code ("data driven") to easy addition of new layers properties.

## 1.5.0

* New : translation into Italian, thanks to Salvatore Larosa (@lrssvt)
* Debug : Groups as layer was not remembered since v1.4.0

## 1.4.0

* New : check that the project title is correctly defined in the project properties dialog, tab OWS
* Improvement : Interface - automatic widgets resizing thanks to Salvatore Larosa @lrssvt

## 1.3.0

* New feature : Choose the image type (png, png 8bit or jpeg) for each layer and not globally anymore

## 1.2.2

* Bug fix : type which prevented from synchronizing over FTP

## 1.2.1

* New : Get layer title and abstract from Qgis layer properties (for qgis >= 1.8)
* Refactoring : method to populate the plugin layer tree
* Bug fix : add missing i18n *.qm translation files

## 1.2.0

* New : support for plugin internationalization : english and french languages available
* Modify : integrate Lizmap in the Qgis Web menu
* Modify : remove warning dialog when closing Lizmap window and auto-save the configuration
* Modify : move help and about dialogs to the plugin Menu
* Bug fix : error when the sync button is pressed and no sync was running

## 1.1.1

* bug correction : closing window and reopening it led to plugin actions launched several times (e.g. save button)
* check if lizmap window is hidden and warn the user (which put lizmap window in the front)
* add a question to save lizmap configuration when closing the window
* clean the json export of lizmap project configuration (e.g. escaping double quotes) : use of simplejson.dumps() method

## 1.1

* addition of Google and OpenStreetMap public baselayers option in the "Map" tab
* ignore non-geometric vector layers
* only one lizmap plugin window available at a time
