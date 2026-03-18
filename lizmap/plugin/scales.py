"""Map scales management for the Lizmap plugin.

This module provides the ScalesManager class which handles map scale
operations using the delegate pattern.
"""
import contextlib

from typing import (
    TYPE_CHECKING,
    Optional,
)

from qgis.core import QgsCoordinateReferenceSystem
from qgis.PyQt.QtWidgets import (
    QMessageBox,
)

from ..definitions.definitions import LwcVersions
from ..toolbelt.i18n import tr

if TYPE_CHECKING:
    from ..dialogs.main import LizmapDialog


from .. import logger


class ScalesManager:
    """Manager for map scale operations in the Lizmap plugin.

    This class handles all map scale related functionality using the delegate
    pattern, providing a cleaner separation of concerns.
    """
    def __init__(
        self,
        *,
        dlg: "LizmapDialog",
        global_options: dict,
        is_dev_version: bool,
        lwc_version: LwcVersions,
    ):
        """Initialize the ScalesManager."""
        self.dlg = dlg
        self.global_options = global_options
        self.is_dev_version = is_dev_version
        self.lwc_version = lwc_version

    def map_scales(self) -> list:
        """ Whe writing CFG file, return the list of map scales. """
        use_native = self.dlg.use_native_scales.isChecked()
        if use_native:
            return [self.dlg.minimum_scale.value(), self.dlg.maximum_scale.value()]
        return [int(a) for a in self.dlg.list_map_scales.text().split(', ') if a.isdigit()]

    def minimum_scale_value(self) -> int:
        """ Return the minimum scale value. """
        value = self.dlg.minimum_scale.text()
        if not value:
            value = self.global_options['minScale']['default']
        return int(value)

    def maximum_scale_value(self) -> int:
        """ Return the maximum scale value. """
        value = self.dlg.maximum_scale.text()
        if not value:
            value = self.global_options['maxScale']['default']
        return int(value)

    def set_map_scales_in_ui(
        self,
        *,
        map_scales: list,
        min_scale: int,
        max_scale: int,
        use_native: Optional[bool],
        project_crs: str,
    ):
        """ From CFG or default values into the user interface. """
        scales_widget = (
            self.dlg.minimum_scale,
            self.dlg.maximum_scale,
        )
        max_value = 2000000000

        if max_scale > max_value:
            # Avoid an OverflowError Python error
            max_scale = max_value

        for widget in scales_widget:
            widget.setMinimum(1)
            widget.setMaximum(max_value)
            widget.setSingleStep(5000)

        map_scales = [str(i) for i in map_scales]

        self.dlg.use_native_scales.toggled.connect(self.native_scales_toggled)

        if self.lwc_version <= LwcVersions.Lizmap_3_6:
            # From CFG and default, scales are int, we need text
            self.dlg.list_map_scales.setText(', '.join(map_scales))
            self.dlg.minimum_scale.setValue(min_scale)
            self.dlg.maximum_scale.setValue(max_scale)
            self.connect_map_scales_min_max()
            self.dlg.use_native_scales.setChecked(False)
            return

        if use_native is None:
            # Coming from a 3.6 CFG file
            crs = QgsCoordinateReferenceSystem(project_crs)
            if crs in (QgsCoordinateReferenceSystem('EPSG:3857'), QgsCoordinateReferenceSystem('EPSG:900913')):
                use_native = True
            else:
                use_native = False

            # We set the scale bar only if it wasn't set
            self.dlg.hide_scale_value.setChecked(use_native)

        # CFG file from 3.7
        self.dlg.use_native_scales.setChecked(use_native)
        self.dlg.list_map_scales.setText(', '.join(map_scales))
        self.dlg.minimum_scale.setValue(min_scale)
        self.dlg.maximum_scale.setValue(max_scale)
        self.disconnect_map_scales_min_max()

    def connect_map_scales_min_max(self):
        """ Connect the list of scales to min/max fields. """
        self.dlg.list_map_scales.editingFinished.connect(self.get_min_max_scales)

    def disconnect_map_scales_min_max(self):
        """ Disconnect the list of scales to min/max fields. """
        with contextlib.suppress(TypeError):
            # Raise if it wasn't connected
            self.dlg.list_map_scales.editingFinished.disconnect(self.get_min_max_scales)

    def native_scales_toggled(self):
        """ When the checkbox native scales is toggled. """
        use_native = self.dlg.use_native_scales.isChecked()

        if self.lwc_version <= LwcVersions.Lizmap_3_6:
            use_native = False
            self.dlg.use_native_scales.setChecked(use_native)

        self.dlg.minimum_scale.setReadOnly(not use_native)
        self.dlg.maximum_scale.setReadOnly(not use_native)
        # The list of map scales is used for printing as well, this must be checked
        # self.dlg.list_map_scales.setVisible(not use_native)
        # self.dlg.button_reset_scales.setVisible(not use_native)
        # self.dlg.label_scales.setVisible(not use_native)

        if use_native:
            msg = tr("When using native scales, you can set minimum and maximum scales.")
        else:
            msg = tr("The minimum and maximum scales are defined by your minimum and maximum values in the list.")
        ui_items = (
            self.dlg.list_map_scales,
            self.dlg.label_min_scale,
            self.dlg.label_max_scale,
            self.dlg.min_scale_pic,
            self.dlg.max_scale_pic,
            self.dlg.minimum_scale,
            self.dlg.maximum_scale,
            self.dlg.label_scales,
        )
        for item in ui_items:
            item.setToolTip(msg)

        if use_native:
            self.disconnect_map_scales_min_max()
        else:
            self.connect_map_scales_min_max()

    def get_min_max_scales(self):
        """ Get minimum/maximum scales from scales input field. """
        logger.info('Getting min/max scales')
        in_map_scales = self.dlg.list_map_scales.text()

        map_scales = [int(a.strip(' \t')) for a in in_map_scales.split(',') if str(a.strip(' \t')).isdigit()]
        # Remove scales which are lower or equal to 0
        map_scales = [i for i in map_scales if int(i) > 0]
        map_scales.sort()
        if len(map_scales) < 2:
            QMessageBox.critical(
                self.dlg,
                tr('Lizmap Error'),
                tr(
                    'Map scales: Write down integer scales separated by comma. '
                    'You must enter at least 2 min and max values.'),
                QMessageBox.StandardButton.Ok)
            min_scale = 1
            max_scale = 1000000000
        else:
            min_scale = min(map_scales)
            max_scale = max(map_scales)

        cleaned = ', '.join([str(i) for i in map_scales])

        self.dlg.list_map_scales.setText(cleaned)
        self.dlg.minimum_scale.setValue(min_scale)
        self.dlg.maximum_scale.setValue(max_scale)
