__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import sys

from qgis.core import Qgis
from qgis.PyQt.QtCore import QDateTime, QLocale
from qgis.PyQt.QtWidgets import QTextEdit

from lizmap.definitions.definitions import Html
from lizmap.qgis_plugin_tools.tools.resources import resources_path


class LogPanel:

    def __init__(self, widget: QTextEdit):
        self.widget = widget
        css_path = resources_path('css', 'log.css')
        with open(css_path, encoding='utf8') as f:
            css = f.read()
        self.widget.document().setDefaultStyleSheet(css)
        self.html = ''

    def append_html(self, new: str):
        self.html += new
        # Do not use self.widget.html()
        # Qt is adding a lot of things in the HTML
        self.widget.setHtml(self.html)

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
            msg = now_str + ' : ' + msg

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
            if level == Qgis.Warning:
                output += '<{0} style="color: orange">{1}</{0}>'.format(style.value, msg)
            elif level == Qgis.Critical:
                output += '<{0} style="color: red">{1}</{0}>'.format(style.value, msg)
            else:
                output += '<{0}>{1}</{0}>'.format(style.value, msg)
            msg = output

        self.append_html(msg)

    def start_table(self):
        self.append_html("<table class=\"tabular-view\" width=\"100%\">")

    def end_table(self):
        self.append_html("</table>")

    def add_row(self, index):
        row_class = ''
        if index % 2:
            row_class = "class=\"odd-row\""
        self.append_html("<tr {}>".format(row_class))

    def end_row(self):
        self.append_html("</tr>")

    def clear(self):
        """ Clear the content of the text area log. """
        self.widget.clear()
        self.html = ''


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
