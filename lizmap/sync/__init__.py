"""Bidirectional synchronisation between a local project directory and a Lizmap repository.

The modules in this package are pure Python, without any dependency on Qt or QGIS,
so the comparison logic can be tested without a server:

* ``paths``: normalisation and validation of relative paths,
* ``model``: entries, statuses and actions,
* ``manifest``: parser of the JSON manifest sent by the server (see ``manifest.schema.json``),
* ``filters``: exclusion rules,
* ``scanner``: scan of the local directory,
* ``state``: state of the last synchronisation, used for the three-way comparison,
* ``diff``: the comparison engine.
"""
