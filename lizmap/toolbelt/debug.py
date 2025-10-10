from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QComboBox


def _debug_combobox(combo: QComboBox, data_start: int = Qt.ItemDataRole.UserRole, data_max: int = 0):
    """Debug a QComboBox."""
    for i in range(combo.count()):
        print("=== NEW ITEM ===")
        print(combo.itemText(i))
        for x in range(data_max):
            print(f"→ {data_start + x} : {combo.itemData(data_start + x)}")
        print("==== END ITEM ====")
