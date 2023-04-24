__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

from qgis.PyQt.QtCore import QDir, QTemporaryFile


def temporary_file_path(prefix: str = 'test', extension: str = 'qgs') -> str:
    """ Temporary filepath. """
    # noinspection PyArgumentList
    temporary = QTemporaryFile(QDir.tempPath() + '/' + f'{prefix}-XXXXXX.{extension}')
    temporary.open()
    file_path = temporary.fileName()
    temporary.close()

    return file_path
