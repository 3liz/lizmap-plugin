# Changelog

## Unreleased

## 4.3.12 - 2024-05-21

* Fix `Browser for media` button if `Cancel` was clicked
* Add button to generate the HTML table in the ToolTip feature for Lizmap Web Client 3.8

## 4.3.11 - 2024-04-30

* Fix language detection

## 4.3.10 - 2024-04-29

* Fix language detection

## 4.3.9 - 2024-04-26

* Follow up previous version

## 4.3.8 - 2024-04-25

* Improve workflow when publishing a project for the first time
* Add a new "Browser media" button
* Allow HTML template for the Lizmap tooltip feature (Lizmap Web Client 3.8 feature, funded by PNR Ballons des Vosges)
* Check for editing capabilities before to warn for Z or M values lost in Lizmap Web Client

## 4.3.7 - 2024-04-24

* Remove FTP support from the plugin
* Check for duplicated label within a layer legend

## 4.3.6 - 2024-04-10

* Minor UX fix about dataviz
* Disable legend label check temporary

## 4.3.5 - 2024-04-05

* Add check for duplicated label in the legend within the same layer
* Add WebP format

## 4.3.4 - 2024-03-26

* Improve safeguards for beginners
* Fix HTML table about checks when pressing the "Run" button
* Various bug fixes

## 4.3.3 - 2024-03-25

* Bugfix about the previous version

## 4.3.2 - 2024-03-25

* Bugfix about the previous version

## 4.3.1 - 2024-03-25

* Bugfix about the previous version

## 4.3.0 - 2024-03-22

* Warn about a possible regression with QGIS 3.36 when saving the layer extent
* Improve support of QGIS 3.34 when generating the popup HTML in the QGIS HTML maptip
* Better support of QGIS Server 3.34 about the default background color support.
  * CFG must be regenerated with an up-to-date version of Lizmap Web Client as well
* Fix URL check about the French IGN provider with the new GeoPlateforme
* Better support of remote server management

## 4.2.7 - 2024-03-12

* New check about duplicated layer with different filters which are next to each other
* Fix checking for some French IGN URLs
* Add a new key in the CFG to prepare to QGIS 3.34 about base layers

## 4.2.6 - 2024-03-07

* Fix detection of simplification on the provider side

## 4.2.5 - 2024-03-07

* Improve checks for PostgreSQL layers

## 4.2.4 - 2024-02-28

* Fix a Python error when saving the file if a layer was removed from the project and used in the configuration before
* Improve error messages about these two checks :
  * "Duplicated keys in the legend"
  * "Duplicated layers with different filters", only in the HTML output

## 4.2.3 - 2024-02-26

* New checks about :
  * duplicated keys in the legend
  * French IGN map provider
* Fix loading the "default-background-color" in the legend
* Fix link to online documentation about "Actions"
* Add project loading time in the CFG file for testing purpose only
* Some UX issues
* Remove some code in backend

## 4.2.2 - 2024-02-16

* Fix a Python error when logging

## 4.2.1 - 2024-02-15

* New option to Add checkbox to choose single WMS layer loading, contribution from @ghtmtt
* Fix loading the Dataviz HTML template from a configuration file
* Do not make the "Overview" group mutually exclusive
* Avoid a Python error if the maximum scale is too big
* Fixing some signals about the Lizmap Web Client version
* Check project CRS if the projection has inverted axes and 3.7.0 <= LWC <= 3.7.3

## 4.2.0 - 2024-02-06

* Add two new checks :
  * layers missing from the WFS
  * fields missing from the WFS
* Remove all mentions to Stamen tiles which was removed in October 2023
* Remove the external Lizmap layer feature which was deprecated since 2019
* If LWC 3.7, disable the legacy checkbox "Add empty base layer"
* Minor UX improvements

## 4.1.8 - 2024-01-30

* Improve the workflow when a new version is published
* Some fixes about the detected version of Lizmap Web Client
* Improve the error message when incomplete CFG is being saved
* Enable more widgets when the layer or the group is located in `baselayers`

## 4.1.7 - 2024-01-25

* Move API keys outside the deprecated panel

## 4.1.6 - 2024-01-25

* Enable more widgets when the layer or the group is located in `baselayers`
* Fix issue about the action file
* Some UX issues and Python error fixed

## 4.1.5 - 2024-01-18

* Fix the graphical user interface of the plugin according to the Lizmap Web Client server version
* Fix the dropdown manu when changing the server
* Fix link about the help on "Actions"
* Add a new check about QGIS Server version for some customers

## 4.1.4 - 2024-01-16

* Fix display of buttons to fix the project

## 4.1.3 - 2024-01-16

* Improve welcoming new users on Lizmap
* Add a missing pyramid check on raster layer
* Display the list of fonts installed on QGIS Server
* Fix opening the wizard for setting the visibility on a group in the legend
* Rephrase error messages

## 4.1.2 - 2023-12-22

* Fix a Python exception about path using `\\vsicurl` protocol on Windows
* Add two new checks :
  * Empty group `baselayers`
  * QGIS server version versus QGIS desktop version

## 4.1.1 - 2023-12-14

* Fix some auto-fix buttons
* Fix some Python exceptions

## 4.1.0 - 2023-12-12

* Raise QGIS minimum version to 3.16
* Better UX when using the clipboard
* Improve the user experience about the new auto-fix buttons, add a dedicated panel for them
* Fix translations about checks/rules in the project
* Add a button to export the results of validation as text
* Export the list of safeguards and their settings
* Add two new checkboxes for LWC 3.7 :
  * "Use native scales" according to project CRS
  * "Hide numeric scale", because the scale might be computed from the "native scale" and not be a rounded value
* The "Map options" panel uses a native extent selector with more buttons and following the project CRS by default
* The `baselayers` group has now the legend collapsed by default and is mutually exclusive
* Catch a Python error if the CFG file has some invalid layer in the Lizmap configuration file when saving

## 4.0.2 - 2023-12-04

* Increase to 1 the maximum of atlas features in a `GetPrint` request automatically
* Fix some columns in the "Filter by form" panel
* Add a notice if the layer is stored in PostgreSQL when setting up the "Locate by layer" tool
* Add a link to PgService documentation on qgis.org website
* Add more CSS files from the server in the HTML Maptip preview dock
* Use a scroll widget for the settings panel
* Fix translations about checks/rules/explanations
* Add new blocker rule when the layer or group has a trailing space
* Fix some casting issue with SIP about the legend
* Add a waiting cursor when saving the CFG file

## 4.0.1 - 2023-11-27

* Fix some missing features from 4.0.0 release

## 4.0.0 - 2023-11-23

* Add a new dock for the HTML popup preview within QGIS desktop directly (with some CSS from Lizmap)
  * Use the QGIS "Apply" button in the vector layer properties to update the HTML preview in the background
* Add a new tool for checking the project against some rules :
  * Possibility to set some safeguards, according to the user level and the current selected server
  * These safeguards are defined according to your level in QGIS to design the project
  * Some rules might be blocking the CFG file (depending on the server, QGIS Desktop version etc.)
* Following the previous features about rules, add new buttons to auto fix the project :
  * Use estimated metadata
  * Use geometry simplification
  * Use project trust option
  * Use SSL
* New helper for checking groups IDs in an attribute table, when doing an attribute filtering
* Disable the "Layers" panel if the layer is excluded from WMS capabilities
* Avoid a Python error about missing primary key
* Moving the Google API key as the base-layer panel is deprecated, it's still needed for the address search
* Add new base layers for Lizmap Web Client 3.7
  * OpenTopoMap
  * French QGIS users only : IGN orthophoto, IGN plan, IGN Cadastre layers
* Add attributions on layers which are provided by the plugin (layers above and OpenStreetMap)
* Possibility to open the plugin even if some layers are temporary unavailable
  and to no loose some Lizmap configuration if the layer was used in a tool
* Display some warning icons if the layer or the field was not loaded correctly or not existing anymore
* Better management if there is a single maintained branch of Lizmap Web Client
* Follow up the new updates about the French IGN GeoPlateforme

## 4.0.0-beta.1 - 2023-11-20

* Add a new dock for the HTML popup preview within QGIS desktop directly (with some CSS from Lizmap)
  * Use the QGIS "Apply" button in the vector layer properties to update the HTML preview in the background
* Add a new tool for checking the project against some rules :
  * Possibility to set some safeguards, according to the user level and the current selected server
  * These safeguards are defined according to your level in QGIS to design the project
  * Some rules might be blocking the CFG file (depending on the server, QGIS Desktop version etc.)
* Following the previous features about rules, add new buttons to auto fix the project :
  * Use estimated metadata
  * Use geometry simplification
  * Use project trust option
  * Use SSL
* New helper for checking groups IDs in an attribute table, when doing an attribute filtering
* Disable the "Layers" panel if the layer is excluded from WMS capabilities
* Avoid a Python error about missing primary key
* Add two buttons for French QGIS users only :
  * French IGN orthophoto and French IGN plan layers
* Add attributions on layers which are provided by the plugin (layers above and OpenStreetMap)
* Possibility to open the plugin even if some layers are temporary unavailable
  and to no loose some Lizmap configuration if the layer was used in a tool
* Display some warning icons if the layer or the field was not loaded correctly or not existing anymore

## 3.18.1 - 2023-10-27

* Warn the user if the field is coming from a join, or it is a virtual one when setting a filter form
* Better warning for Stamen tiles

## 3.18.0 - 2023-10-19

* Disabling Stamen base-maps checkbox, see https://stamen.com/faq
* Fix an error on Windows when the path of a layer is on a different drive
* Improve links to documentation
* Add a new panel for some settings and tools coming soon
* Add an SSL connection checker for PostgreSQL layers
* Add a link to the project folder if the thumbnail is not found
* Review help about `@lizmap_user_groups`
* Various minor fixes :
  * Py-QGIS-Server version
  * new layouts configuration for LWC 3.7

## 3.17.1 - 2023-10-04

* Add links to the corresponding blog post announcing a new release, if available
* Support the "text widget" from QGIS 3.30 in the tooltip, contribution from @ghtmtt
* Add the possibility to open the online documentation for the current panel in the plugin
* Do not generate the HTML for a field if the field is excluded from WMS
* Add an option to show empty rows in the HTML map tip to generate another QGIS expression

## 3.17.0 - 2023-09-18

* Some GUI updates about :
  * Message bars which are displayed
  * Layer which is renamed
  * Thumbnail detection
* Review links to open the online documentation
* New panel about "Actions" to make it easier to discover
* Add button to open the https://www.lizmap.com/ online cloud help if necessary
* For Lizmap Web Client 3.7, include buttons to add a base layer
* Add some more links to social networks

## 3.16.4 - 2023-08-22

* Improve the QGIS server version check, it's now displayed in the server table
* Add a reminder to open the plugin after a new layer is added in the project
* Fix a wrong error message about missing the API key for the address search
* Improve the error message about the QGIS authentication database for PostgreSQL layers

## 3.16.3 - 2023-08-10

* Fix some display about the new log panel

## 3.16.2 - 2023-08-09

* Report all layers having a primary key which is not in the layer's fields.

## 3.16.1 - 2023-08-09

* Fix the use of OpenTopoMap background

## 3.16.0 - 2023-08-08

* Check for any duplicated layer or group before storing them in the configuration.
  These names need to be unique.
* Add some new project checks for PostgreSQL layers :
  * Use estimated metadata
  * Use server side geometry simplification
* Some refactoring about the "legacy" log panel.
  Warnings will be displayed in the panel instead of some popups soon.
* Add helpers about groups in the legend
* Disable field checkbox when the plugin is asking for a primary key and the layer is stored in PostgreSQL.
* For Lizmap Web Client 3.7 minimum, disable for now some options in the UX in the "Layers" tab.
* Check if all scales are greater than 0.
* Internal code refactoring about the layer tree
* For developers, add more shortcuts to debug a PostgreSQL layer

## 3.15.1 - 2023-07-18

* The UX is improved about the checkbox "Activate first map theme on startup"
* Refactor the server wizard to avoid a possible crash

## 3.15.0 - 2023-07-12

* Add the HTML code editor for the abstract on a layer
* UX - Add note about popup must be activated in the atlas form
* Fix some UX issues about a checkbox
* Possible to override URLs in an `urls.ini` file
* Follow HTTP redirections when connecting the Lizmap Web Client server
* Check for duplicated layer having different filters, when used with Lizmap Web Client 3.7
* Check the plugin version when possible with the native QGIS plugin manager
* Check for ECW layers

## 3.14.3 - 2023-07-03

* Add support for the "Attribute Editor Relation" when generating the tooltip. It needs Lizmap Web Client 3.7.
* Fix some User Experience issues
* Improve the QGIS version checks between server and desktop
* Fix a Python error when displaying the dataviz plot preview
* Enable the HTML builtin editor, easier to write HTML content in Lizmap
* Fix possible crash when adding a new server in the wizard
* Add a file logger for Lizmap users not using a production version.
  * Logs are stored in the OS temporary directory, then in the `QGIS_Lizmap` directory.

## 3.14.2 - 2023-06-23

* Add wizard for setting up the PostgreSQL database
* Fix a Python error about a wrong variable name
* Fix concatenate with number in aggregate (contribution from @ghtmtt)
* Some cleaning in the CFG file about legacy keys

## 3.14.1 - 2023-06-12

* Fix check on composite primary keys for PostgreSQL layers
* Rework the new panel for Lizmap Web Client 3.7 about the dataviz Drag&Drop layout
* Start deprecating the base layer panel for Lizmap Web Client 3.7 as well
* Code refactoring to display some warnings to the user

## 3.14.0 - 2023-05-30

* Improve some UX forms about checkbox.
* Fix the new server button display
* Fix opening the online help from the wizard, it will choose the correct language if possible
* Some Python refactoring about reading the CFG file with boolean values
* Improve the new wizard for setting up the new server
* Fix the wrong project home folder when checking if all paths are correct when it's hosted on Lizmap.com
* Try to fix the popup when "Autosaver" plugin is installed
* Add a new panel about LWC 3.7 and Drag&Drop layout for the dataviz

## 3.13.0 - 2023-05-01

* Add a new wizard for the server/instance creation, it will allow more options soon in a future version
* Improve the server dropdown menu and server metadata
* Display the message bar if the branch of Lizmap Web Client is outdated
* Fix shortname generation when the layer has been duplicated in the project
* Fix saving the output of the group wizard
* Fix wrong warning about previous QGS project file without finding the Lizmap CFG file
* Fix opening the Lizmap popup dialog
* Hide the provider type from the user interface for edition layers
* Improve unittests of the plugin from QGIS 3.10 to the latest QGIS
* Under the hood cleanup in Python files

## 3.12.0 - 2023-04-19

* Check for space in the Lizmap URL before requesting metadata
* Remove the target version dropdown menu, it will now use the server dropdown menu
* The server must have a valid status before using the plugin
* The metadata for each server is stored for maximum seven days
* Fix the shortname generation when the layer name contains a `-`
* Fix the last used repository used in the dropdown menu
* Fix the new thumbnail checker

## 3.11.5 - 2023-04-11

* Display the current size of the project thumbnail if found
* Avoid a warning when reading the CFG file and an address provider was found with an API key
* Add some Python functions to make it easier to upgrade a bunch of projects automatically.
  Read the README.md on GitHub for the Python script to update a folder with some QGIS projects.
* Add QGIS desktop 3.22 for automatic testing

## 3.11.4 - 2023-04-05

* Fix possible regressions from 3.11.2

## 3.11.3 - 2023-03-31

* Fix a possible regression from 3.11.2

## 3.11.2 - 2023-03-31

* Set shortnames when it's possible for layers, groups and project when Lizmap Web Client ≥ 3.6
* Better handling when a QGIS project has been renamed :
  * Either from QGIS when "save as" is used
  * Or when the QGIS project has the `lizmap_user` project variable but no CFG file
* Some Python cleaning about handling file path, related to CFG file for instance
* When running Lizmap Web Client 3.6, the QGIS server must be OK before going in other tabs of the plugin
* Disable or replace graphical components if Qt Webkit is not available on the computer.
* Fix the launching of the plugin on QGIS 3.10

## 3.11.1 - 2023-03-21

* Add more translated sentences
* Fix saving an HTML dataviz
* Avoid a Python error if the metadata couldn't have been fetched before saving the CFG file

## 3.11.0 - 2023-03-09

* Improve the editing form with non-spatial layers
* Add a new HTML wizard for the
  * QGIS HTML Maptip popup
  * HTML template in the dataviz
  * HTML layout in the dataviz
  * plot description in the dataviz
* Improve the new layout panel for Lizmap Web Client 3.7

## 3.10.1 - 2023-02-07

* Add a feature selector for the plot preview in the dataviz panel
* Disable HTML plot preview
* Fix the plot preview with some URL configuration
* Fix the HTML is not saved in the CFG in the layer tab, abstract field
* Fix an issue when a project is closed, and we open the plugin again
* Fix editing a table was raising an error about duplicated row
* Move the spinbox about the maximum feature in the popup dock outside the relation group box

## 3.10.0 - 2023-01-17

* Allow to open the first tab in Lizmap without a project, to be able to visit links, documentation
* Fix the converter from Lizmap HTML popup to QGIS HTML popup when the alias/field has an underscore or other
  accented characters.
* Add the Lizmap Web Client target version in the copy/paste text available on a server
* New with Lizmap Web Client 3.6.1:
  * Add a preview about a plot in the dataviz panel
  * Better error message if the credentials to connect to Lizmap Web Client is wrong
  * Group wizard
* New with Lizmap Web Client 3.7.0:
  * For a layer in the dataviz, it's possible to define a specific title when displayed in a popup
  * For plot can now be "not refreshed" if the layer data has been filtered
* Help users about layers which can not be valid when hosted on lizmap.com such as QGIS authentication database for PostgreSQL

## 3.9.10 - 2023-01-05

* Fix the dropdown menu about the Lizmap Web Client target version
* Reduce some logs
* Review some strings in English

## 3.9.9 - 2023-01-04

* Fix issue when reading the CFG file about the new configuration legend image option.
* Fix the theme selector in the dataviz panel
* Add a converter from Lizmap HTML popup to QGIS HTML popup
* Check the login and server URL before saving in the authentication database
* Make the default version Lizmap Web Client 3.6 if no settings was found, instead of 3.5
* Review the server information panel, it's now more readable
* Internal code refactoring about signals and slots in the plugin

## 3.9.8 - 2022-12-08

* Improve the user interface about the server table.
* Fix regression when using QGIS Desktop < 3.20 when saving credentials.

## 3.9.7 - 2022-12-07

* The legacy "Lizmap HTML" popup is now deprecated for vector layer. A warning is raised when saving the CFG file.
* Fix the "OK" button was not closing the dialog.

## 3.9.6 - 2022-12-05

* Add new "maximum field" for Lizmap Web Client ≥ 3.7 about the form filter with numeric values
* Remove notes about the Lizmap QGIS server plugin
* Add new field in the server list to set a custom name
* Allow the plugin to have many development versions such as Lizmap Web Client 3.6 and 3.7
* All logins must be filled before saving a CFG file

## 3.9.5 - 2022-11-29

* Review the user interface about
  * address search provider and the error if no API key was provided
  * setting up popup on a layer
* Some code refactoring and review the user interface about the login and password for a Lizmap server
* Always show the next version of Lizmap Web Client (3.6 for now)
* Add more translated strings in the translation system

## 3.9.3 - 2022-11-14

* Fix the edit server dialog, as it is now required to have login&password.

## 3.9.2 - 2022-11-07

* Add a new option "Use the geometry centroid" for the filtering by polygon. An index on the PostgreSQL layer is required.
  Available in the 1.2.0 version of the server plugin.
* Fix an issue when using Lizmap Web Client 3.6 RC 2
* Add a warning if Google or IGN is used for the address search without an API key
* Better warning about the QGIS master password when it was not set yet
* Make login on each server required

## 3.9.1 - 2022-10-04

* Add a link to GIS Stackexchange on the first tab
* Fix missing translations in the user interface of the plugin
* Improve the panel about server information
* Improve metadata in the CFG file about the status of the current Lizmap Web Client version which is used
* Improve a little the UX about the initial scales

## 3.9.0 - 2022-07-25

* Spatial filtering - Add a new checkbox "Filter by user" to filter by users and not by user groups only.
  This feature is compatible for Lizmap Web Client ≥ 3.5 if the server plugin is updated as well to version 1.1.0.

## 3.8.3 - 2022-06-29

* Fix a Python error if the legacy key `noLegendImage` was not found in the CFG file
* Check if the QGIS Server property "Use layer ID as name" is checked for Lizmap Web Client ≥ 3.6

## 3.8.2 - 2022-06-13

* Improve the user experience about dropdown menu in the layer panel by providing icon, tooltip, proper label
* Fixing an issue when saving the CFG file about the popup source and the image format

## 3.8.1 - 2022-06-08

* Fix configuration reading about the new setting legend image option when using Lizmap Web Client < 3.6

## 3.8.0 - 2022-06-07

* Check that the Lizmap Web Client target version exists in the table before saving the CFG file
* Improve the CFG generation when the attribute table has a custom configuration
* Always export the new checkbox for a fixed scale in the overview map
* Remove the code related to the server side. It's a new plugin called "Lizmap server" now.
* Raise the QGIS minimum version to 3.10
* New option for automatic legend display at startup, Lizmap Web Client 3.6
* Add OpenTopoMap background for Lizmap Web Client 3.6

## 3.7.7 - 2022-04-13

* Desktop - Better message if there is an error when fetching data from QGIS Server
* Desktop - Fix link to the documentation about the PostgreSQL search `lizmap_search`
* Desktop - Always check if the layer is published as WFS when opening the dialog instead of at the end
* Desktop - Add a new button to generate an HTML table from layer fields, like the auto popup
* Desktop - Add some checks about spaces or accents in filename when opening the QGS file
* Desktop and server - Fix a Python exception when using the tooltip from Drag&Drop if the date format is not set yet

## 3.7.6 - 2022-03-25

* Desktop - Fix possible python exception about the QGIS desktop plugin manager

## 3.7.5 - 2022-03-22

* Desktop - Better display of the QGIS Server version when it's not available
* Server - Always register the API if possible, raise the error only when requested instead
* Server - Add the commit ID of QGIS if available in the JSON metadata
* Server - Set a custom application name when connecting to PostgreSQL on the server side

## 3.7.4 - 2022-02-15

* Desktop - Improve the parsing of LWC server versions
* Desktop - Fix saving the configuration file if a layer is not available with the filter by polygon

## 3.7.3 - 2022-02-14

* Desktop - Improve the server version comparaison and fix some errors
* Desktop - Fix a Python error if the QGIS version is not correct when registering a Lizmap server

## 3.7.2 - 2022-02-10

* Server : fix a SQL query for the "filtering by polygon" when the field is a string

## 3.7.1 - 2022-01-17

* Update the user experience when no master password is set in QGIS Desktop
* Add new actions in the right click on a server such as "Copy versions in the clipboard"
* Fix a Python error with a project having some deleted layers
* Fix duplicated entry in the web menu when reloading the plugin

## 3.7.0 - 2022-01-12

* Add the possibility to add a login and a password for a given Lizmap server URL
* Server - Add API to fetch server information on the URL http://your.qgis.server/lizmap/server.json.
  Read the documentation how to set up this API
  https://docs.lizmap.com/3.5/en/install/pre_requirements.html#lizmap-server-plugin

## 3.6.5 - 2021-12-15

* Tooltip : Fix generation of the tooltip expression when using `@current_geometry` and `current_value()` when it's
  used outside the form context.
* Enable Lizmap Web Client 3.5 for the default version
* Update the user interface for the new API for the French IGN provider

## 3.6.4 - 2021-11-15

* Desktop - Add link to the Lizmap IRC channel on libera.chat.
* Desktop - Improve user experience when using the checkbox "Third-party WMS layers"
  by disabling the format option if needed.
* Desktop - Add `@lizmap_user` and `@lizmap_user_groups` in the project with empty string/list.
* Desktop - Display if the plot or popup is available for the given Lizmap Web Client version
* Server - Display the current plugin version in the logs when loading the plugin.

## 3.6.3 - 2021-10-07

* Follow up from version 3.6.0 about not supporting spatialite for editing capabilities, the plugin will
  now remove these lines from the CFG file.
* Variables `@lizmap_user` and `@lizmap_user_groups` are available at the project level with current Lizmap
  user and its groups. It's possible to use them in QGIS Desktop manually to try symbology, default value in
  form etc.
* Fix the GetFeatureInfo request on the server side when there is a short name set on the layer.

## 3.6.2 - 2021-09-23

* Fix an issue in the user interface saving the CFG file

## 3.6.1 - 2021-09-23

* Fix an issue in the user interface when switching panels

## 3.6.0 - 2021-09-23

* First "Information panel" :
  * It's now recommended having at least one Lizmap URL provided
  * The plugin shows more information when the user is not running the latest bug fix version
  * Open the Lizmap URL instance from a right click in the "Information" panel
* New feature in Lizmap Web Client 3.5 :
  * Filtering data by polygon for a given user
* If running QGIS 3.10 or higher, display the file name when using a drag&drop layout with an attachement widget
* Removing Spatialite from available provider for editing capabilities, only PostgreSQL is supported (fix #361)
* Removing the check if all layers are in a sub folder of the project. Users on their own server might have data where they want (fix #346)
* Allow to open the documentation in Japanese
* Refactor some code on the server side

## 3.5.7 - 2021-08-31

* Server - Avoid issue about GetFeatureInfo
* Server - Refactor some code about logging

## 3.5.6 - 2021-08-10

* Server - Avoid registering twice the Lizmap service
* Server - Add some more info level message in the server

## 3.5.5 - 2021-08-09

* Desktop - Show dialog in front of QGIS Desktop if a dialog is already opened (contribution from @Kanahiro)
* Server - Improve debug for GetFeatureInfo on the server side
* Server - Check headers content before reading config file to improve performance

## 3.5.4 - 2021-07-13

* Fix the visibility used on container in QGIS Form with level upper-more than 1
* Server - Always log when there is a Python exception
* Server - Make the plugin compatible Python 3.5
* Server - Rename variable about conflict

## 3.5.3 - 2021-07-05

* Refactor some imports and class names in the server part

## 3.5.2 - 2021-06-23

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
    * Form drill-down using Value Relation widget
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
    * Add option to allow geometry-less feature
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
* Fix inverted HStore in **Value map** when using drag&drop tooltip
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
* Add a check-able field input in forms
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
* Use QGIS native map layer combobox in panels (except base layer)
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
* [Bugfix] support wms urls when they have parameters with no =
* [Bugfix] fix #122 with reversed min and max scales

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
* UI - fix issue with QgsCollapsibleGroupBox import
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
* [FEATURE] Dataviz - Add a field to enter an HTML template for plot positioning
* [BUGFIX] Python - replace modules import *
* [FEATURE] New Atlas tool to navigate through a layer features
* [FEATURE] Configure the amount of features per layer displayed in popup
* [BUGFIX] Allow layers with datasource starting with HTTP
* Update locales
* [BUGFIX] Base-layers - fix get startup base-layer from project #56



## 2.3.0

* Interface - Improve look & feel

## 2.2.0

This version add new features which are only usable with upcoming Lizmap Web Client 3.1

* Interface - Add tooltips and blue background for new features
* Plugin - Improve makefile for `transup` and `transcompile`
* Attribute table - Option to fetch data only within map extent && layer scale visibility
* Tools layer limit linked to combobox size
* Map - fix bug with startup base-layer for accentuated layers/groups
* UI - fix issue with QgsCollapsibleGroupBox import
* Editing - Add option to pass list of groups to restrict editing for each layer
* Locales - Add Euskara and Swedish, update other languages
* Add Stamen Toner external base-layer (and remove Mapquest and OSM CycleMap)
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
* Base-layers - Get the startup base-layer from configuration #56
* Layers - Enable WMS checkbox only for WMS layers
* Remove option to transform groups as legend blocks #57

## 2.1.0

This version add new features which are only usable with upcoming Lizmap Web Client 3.0.

  * Base-layers - Choose active base-layer at map startup
  * Map - Add options to configure tolerances for popup activation in pixels
  * Layers - New option to choose popup source: auto, lizmap advanced or QGIS map-tip
  * Map - New map option to choose info popup container: dock, mini-dock or map
  * Tools - Allow virtual fields in layer fields combo-boxes

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
* Minor GUI modifications in the Layers tab to improve readability
* Add minLength option for Locate by layer

## 1.9.8

* Speed up lizmap start (was bad since embedded layers feature)
* New feature - hide layer in Legend but displayed in map
* External base-layer - Add OsmCycleMap
* Lizmap external base-layers - add image format option

## 1.9.7

* Base-layers - option to add an empty base-layer with project background color - #25
* Change default scales list in Map tab (add 10k and 50k)
* Automatic configuration for some Project parameters : title, advertised extent, EPSG:3857 if needed
* Italian translation - Build qm file
* IT translation
* Address Search - Add Google and IGN (france) API
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
* base-layers - option to add external Lizmap project layers as base-layers
* Table widgets - refactor code to retrieve options from json config
* base-layers - Add OpenCycleMap, IGN (plan, aerial, scans), Bing Maps

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

* Remove python module simplejson dependency (replaced by module json)
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

* Improvement: Allow the user to use layers from a parent folder or a brother folder of the root project folder.
  Can be used to have a Data folder at the same level of the repositories.
* Bug Fix: Fix the toggled option for layers which was always on
* Bug Fix: Win-scp - a password can be empty if the winScp session field is filled.

## 1.7.1

* Improvement: Allow the user to choose a WinSCP pre-saved session. Can be used to deal with TLS connections.
* Improvement: Allow the user to choose the winSCP mirror criteria : between 'size' and 'time'
* Improvement: LFTP (linux only) automatically accepts SSL certificate

## 1.7.0

* New feature: Popup - add a checkbox to enable/disable popup for each layer
* New feature: Ability to write templates for popup
* Bug fix:  Project properties - checks the BBOX is really set in the OWS tab.
* Bug fix: FTP windows sync - protect the win-scp path with double quote when running the sync

## 1.6.1

* Bug fix : correctly use `layer.setAbstract` instead of setTitle to set back the abstract

## 1.6.0

* New : addition of more cache parameters : cache expiration and meta tile
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

* New : support for plugin internationalization : english and French languages available
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

* addition of Google and OpenStreetMap public base-layers option in the "Map" tab
* ignore non-geometric vector layers
* only one lizmap plugin window available at a time
