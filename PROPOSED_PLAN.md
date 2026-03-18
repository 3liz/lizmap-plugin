
### Identified functional areas

1. **Plugin initialization** (~300 lines): Constructor `__init__` - settings, dialogs, translations, layer tables, combo boxes
2. **GUI initialization** (~300 lines): `initGui` method - creating actions, menus, connecting signals
3. **Layer tree management** (~400 lines): `populate_layer_tree`, `process_node`, `set_tree_item_data`, tree state methods
4. **Layer configuration UI** (~500 lines): `from_data_to_ui_for_layer_group`, `save_value_layer_group_data`, `set_layer_metadata`, etc.
5. **Base layers** (~150 lines): Adding OSM, IGN layers
6. **Project config file I/O** (~300 lines): `read_cfg_file`, `write_project_config_file`, `project_config_file`
7. **Project checking/validation** (~500 lines): `check_project` and related validation methods
8. **WebDAV/Upload** (~300 lines): `send_files`, `upload_media`, `upload_thumbnail`, etc.
9. **Server management** (~200 lines): Server manager, capabilities checking
10. **Training/Workshop** (~200 lines): Training workshop functionality
11. **Helpers/Utilities** (~300 lines): Various small methods
12. **Scales**: Scales manager 


### Submodules

| Submodule | Description | Approx. Lines |
|-----------|-------------|----------------|
| **`plugin/core.py`** | Main class stub that imports from submodules | ~200 |
| **`plugin/init.py`** | Constructor (`__init__`), settings, translations, UI setup | ~400 |
| **`plugin/gui.py`** | `initGui` method - actions, menus, signals | ~250 |
| **`plugin/layer_tree.py`** | Layer tree population, processing, state management | ~350 |
| **`plugin/layer_config.py`** | Layer property UI binding, metadata handling | ~400 |
| **`plugin/baselayers.py`** | Adding OSM, IGN, and other base layers | ~150 |
| **`plugin/project_io.py`** | Read/write CFG files, config serialization | ~300 |
| **`plugin/project_check.py`** | Project validation, checking, safeguards | ~500 |
| **`plugin/upload.py`** | WebDAV, file upload, media handling | ~300 |
| **`plugin/server.py`** | Server management, capabilities | ~200 |
| **`plugin/training.py`** | Training workshop functionality | ~200 |
| **`plugin/helpers.py`** | Miscellaneous utility methods | ~300 |
| **`plugin/scales.py`** | Scales methods | - |


