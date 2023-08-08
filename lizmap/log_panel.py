__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import sys

from qgis.core import Qgis
from qgis.PyQt.QtCore import QDateTime, QLocale
from qgis.PyQt.QtWidgets import QTextEdit

from lizmap.definitions.definitions import Html


class LogPanel:

    def __init__(self, widget: QTextEdit):
        self.widget = widget

    def separator(self):
        """ Add a horizontal separator. """
        # TODO, check for a proper HTML
        self.widget.append('=' * 20)

    def append(
            self,
            msg: str,
            style: Html = None,
            abort=None,
            time: bool = False,
            level: Qgis.MessageLevel = Qgis.Info,
    ):
        """ Append text to the log. """
        if abort:
            sys.stdout = sys.stderr

        if time:
            now = QDateTime.currentDateTime()
            now_str = now.toString(QLocale().timeFormat(QLocale.ShortFormat))
            self.widget.append(now_str)

        if level == Qgis.Warning:
            # byte_array = QByteArray()
            # QBuffer
            # buffer( & byteArray);
            # pixmap.save( & buffer, "PNG");
            # QString
            # msg += "<img src=\"data:image/png;base64," + byte_array.toBase64() + "\"/>";
            # msg = '<img src="{}">'.format(":images/themes/default/mIconWarning.svg")
            pass

        if style:
            output = ''
            if style in (Html.H1, Html.H2, Html.H3):
                output += '<br>'
            output += '<{0}>{1}</{0}>'.format(style.value, msg)
            msg = output

        self.widget.append(msg)

    def clear(self):
        """ Clear the content of the text area log. """
        self.widget.clear()


if __name__ == '__main__':
    """ For manual tests. """
    from qgis.PyQt.QtWidgets import QApplication, QDialog, QHBoxLayout
    app = QApplication(sys.argv)
    dialog = QDialog()
    layout = QHBoxLayout()
    dialog.setLayout(layout)
    edit = QTextEdit()
    layout.addWidget(edit)
    logger = LogPanel(edit)
    logger.append("Title", Html.H2, time=True)
    dialog.exec_()
    sys.exit(app.exec_())
