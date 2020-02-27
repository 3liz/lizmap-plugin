from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication, QgsFields

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


# noinspection PyCallByClass,PyArgumentList
def variant_type_icon(field_type) -> QIcon:
    if field_type == QVariant.Bool:
        return QgsApplication.getThemeIcon('/mIconFieldBool.svg')
    elif field_type in [QVariant.Int, QVariant.UInt, QVariant.LongLong, QVariant.ULongLong]:
        return QgsApplication.getThemeIcon('/mIconFieldInteger.svg')
    elif field_type == QVariant.Double:
        return QgsApplication.getThemeIcon('/mIconFieldFloat.svg')
    elif field_type == QVariant.String:
        return QgsApplication.getThemeIcon('/mIconFieldText.svg')
    elif field_type == QVariant.Date:
        return QgsApplication.getThemeIcon('/mIconFieldDate.svg')
    elif field_type == QVariant.DateTime:
        return QgsApplication.getThemeIcon('/mIconFieldDateTime.svg')
    elif field_type == QVariant.Time:
        return QgsApplication.getThemeIcon('/mIconFieldTime.svg')
    elif field_type == QVariant.ByteArray:
        return QgsApplication.getThemeIcon('/mIconFieldBinary.svg')
    else:
        return QIcon()


def provider_fields(fields):
    flds = QgsFields()
    for i in range(fields.count()):
        if fields.fieldOrigin(i) == QgsFields.OriginProvider:
            flds.append(fields.at(i))
    return flds
