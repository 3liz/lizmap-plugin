# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_send2server.ui'
#
# Created: Thu Jun 16 17:30:52 2011
#      by: PyQt4 UI code generator 4.8.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_send2server(object):
    def setupUi(self, send2server):
        send2server.setObjectName(_fromUtf8("send2server"))
        send2server.resize(481, 422)
        self.tabWidget = QtGui.QTabWidget(send2server)
        self.tabWidget.setGeometry(QtCore.QRect(10, 10, 461, 401))
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tab_ftp = QtGui.QWidget()
        self.tab_ftp.setObjectName(_fromUtf8("tab_ftp"))
        self.horizontalLayoutWidget_3 = QtGui.QWidget(self.tab_ftp)
        self.horizontalLayoutWidget_3.setGeometry(QtCore.QRect(10, 130, 431, 51))
        self.horizontalLayoutWidget_3.setObjectName(_fromUtf8("horizontalLayoutWidget_3"))
        self.horizontalLayout_3 = QtGui.QHBoxLayout(self.horizontalLayoutWidget_3)
        self.horizontalLayout_3.setMargin(0)
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.label_3 = QtGui.QLabel(self.horizontalLayoutWidget_3)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout_3.addWidget(self.label_3)
        self.inUsername = QtGui.QLineEdit(self.horizontalLayoutWidget_3)
        self.inUsername.setObjectName(_fromUtf8("inUsername"))
        self.horizontalLayout_3.addWidget(self.inUsername)
        self.horizontalLayoutWidget_2 = QtGui.QWidget(self.tab_ftp)
        self.horizontalLayoutWidget_2.setGeometry(QtCore.QRect(10, 70, 431, 51))
        self.horizontalLayoutWidget_2.setObjectName(_fromUtf8("horizontalLayoutWidget_2"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.horizontalLayoutWidget_2)
        self.horizontalLayout_2.setMargin(0)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label_2 = QtGui.QLabel(self.horizontalLayoutWidget_2)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout_2.addWidget(self.label_2)
        self.inPort = QtGui.QLineEdit(self.horizontalLayoutWidget_2)
        self.inPort.setObjectName(_fromUtf8("inPort"))
        self.horizontalLayout_2.addWidget(self.inPort)
        self.horizontalLayoutWidget = QtGui.QWidget(self.tab_ftp)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(10, 10, 431, 51))
        self.horizontalLayoutWidget.setObjectName(_fromUtf8("horizontalLayoutWidget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtGui.QLabel(self.horizontalLayoutWidget)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.inHost = QtGui.QLineEdit(self.horizontalLayoutWidget)
        self.inHost.setObjectName(_fromUtf8("inHost"))
        self.horizontalLayout.addWidget(self.inHost)
        self.horizontalLayoutWidget_5 = QtGui.QWidget(self.tab_ftp)
        self.horizontalLayoutWidget_5.setGeometry(QtCore.QRect(10, 310, 431, 51))
        self.horizontalLayoutWidget_5.setObjectName(_fromUtf8("horizontalLayoutWidget_5"))
        self.horizontalLayout_5 = QtGui.QHBoxLayout(self.horizontalLayoutWidget_5)
        self.horizontalLayout_5.setMargin(0)
        self.horizontalLayout_5.setObjectName(_fromUtf8("horizontalLayout_5"))
        self.label_5 = QtGui.QLabel(self.horizontalLayoutWidget_5)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.horizontalLayout_5.addWidget(self.label_5)
        self.inLocaldir = QtGui.QLineEdit(self.horizontalLayoutWidget_5)
        self.inLocaldir.setEnabled(False)
        self.inLocaldir.setObjectName(_fromUtf8("inLocaldir"))
        self.horizontalLayout_5.addWidget(self.inLocaldir)
        self.horizontalLayoutWidget_4 = QtGui.QWidget(self.tab_ftp)
        self.horizontalLayoutWidget_4.setGeometry(QtCore.QRect(10, 190, 431, 51))
        self.horizontalLayoutWidget_4.setObjectName(_fromUtf8("horizontalLayoutWidget_4"))
        self.horizontalLayout_4 = QtGui.QHBoxLayout(self.horizontalLayoutWidget_4)
        self.horizontalLayout_4.setMargin(0)
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.label_4 = QtGui.QLabel(self.horizontalLayoutWidget_4)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.horizontalLayout_4.addWidget(self.label_4)
        self.inPassword = QtGui.QLineEdit(self.horizontalLayoutWidget_4)
        self.inPassword.setObjectName(_fromUtf8("inPassword"))
        self.horizontalLayout_4.addWidget(self.inPassword)
        self.horizontalLayoutWidget_6 = QtGui.QWidget(self.tab_ftp)
        self.horizontalLayoutWidget_6.setGeometry(QtCore.QRect(10, 250, 431, 51))
        self.horizontalLayoutWidget_6.setObjectName(_fromUtf8("horizontalLayoutWidget_6"))
        self.horizontalLayout_6 = QtGui.QHBoxLayout(self.horizontalLayoutWidget_6)
        self.horizontalLayout_6.setMargin(0)
        self.horizontalLayout_6.setObjectName(_fromUtf8("horizontalLayout_6"))
        self.label_6 = QtGui.QLabel(self.horizontalLayoutWidget_6)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.horizontalLayout_6.addWidget(self.label_6)
        self.inRemotedir = QtGui.QLineEdit(self.horizontalLayoutWidget_6)
        self.inRemotedir.setObjectName(_fromUtf8("inRemotedir"))
        self.horizontalLayout_6.addWidget(self.inRemotedir)
        self.tabWidget.addTab(self.tab_ftp, _fromUtf8(""))
        self.tab_main = QtGui.QWidget()
        self.tab_main.setObjectName(_fromUtf8("tab_main"))
        self.horizontalLayoutWidget_7 = QtGui.QWidget(self.tab_main)
        self.horizontalLayoutWidget_7.setGeometry(QtCore.QRect(10, 10, 441, 52))
        self.horizontalLayoutWidget_7.setObjectName(_fromUtf8("horizontalLayoutWidget_7"))
        self.horizontalLayout_7 = QtGui.QHBoxLayout(self.horizontalLayoutWidget_7)
        self.horizontalLayout_7.setMargin(0)
        self.horizontalLayout_7.setObjectName(_fromUtf8("horizontalLayout_7"))
        self.btSync = QtGui.QPushButton(self.horizontalLayoutWidget_7)
        self.btSync.setObjectName(_fromUtf8("btSync"))
        self.horizontalLayout_7.addWidget(self.btSync)
        self.btClearlog = QtGui.QPushButton(self.horizontalLayoutWidget_7)
        self.btClearlog.setObjectName(_fromUtf8("btClearlog"))
        self.horizontalLayout_7.addWidget(self.btClearlog)
        self.outLog = QtGui.QTextEdit(self.tab_main)
        self.outLog.setGeometry(QtCore.QRect(10, 60, 441, 301))
        self.outLog.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.outLog.setObjectName(_fromUtf8("outLog"))
        self.tabWidget.addTab(self.tab_main, _fromUtf8(""))
        self.tab = QtGui.QWidget()
        self.tab.setObjectName(_fromUtf8("tab"))
        self.textEdit = QtGui.QTextEdit(self.tab)
        self.textEdit.setGeometry(QtCore.QRect(10, 10, 441, 351))
        self.textEdit.setObjectName(_fromUtf8("textEdit"))
        self.tabWidget.addTab(self.tab, _fromUtf8(""))

        self.retranslateUi(send2server)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(send2server)

    def retranslateUi(self, send2server):
        send2server.setWindowTitle(QtGui.QApplication.translate("send2server", "send2server", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("send2server", "Username", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("send2server", "Port", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("send2server", "Host", None, QtGui.QApplication.UnicodeUTF8))
        self.label_5.setText(QtGui.QApplication.translate("send2server", "Local Dir", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("send2server", "Password", None, QtGui.QApplication.UnicodeUTF8))
        self.label_6.setText(QtGui.QApplication.translate("send2server", "Remote Dir", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_ftp), QtGui.QApplication.translate("send2server", "FTP configuration", None, QtGui.QApplication.UnicodeUTF8))
        self.btSync.setText(QtGui.QApplication.translate("send2server", "Synchronize", None, QtGui.QApplication.UnicodeUTF8))
        self.btClearlog.setText(QtGui.QApplication.translate("send2server", "Clear log", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_main), QtGui.QApplication.translate("send2server", "Run", None, QtGui.QApplication.UnicodeUTF8))
        self.textEdit.setHtml(QtGui.QApplication.translate("send2server", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Ubuntu\'; font-size:11pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Prerequisites</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-style:italic;\">Client-side</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Project srs must be set</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Srs must be set for each layer</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Data (vector and raster) must be stored in the same folder of the project file, or in a subfolder</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Project paths must be set to &quot;relative&quot; (see project settings)</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-style:italic;\">Server side</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* QgisMapserver must be installed</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Someone must have root permissions to add your qgis project the first time.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* You need FTP write access to a directory</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Ftp configuration</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">You must give</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* host : ftp host, corresponding to the server where QgisMapserver is installed</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* username = Ftp username</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* password = Ftp password</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* port = Ftp port (21 if not given)</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* remotedir = Path to the directory where all your qgis project (project file and data) must be sent.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Usage</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Check that all the Ftp configuration are set. Go to &quot;Ftp Configuration&quot; tab to do so.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Click &quot;Send&quot;. It will perform a local --&gt; server synchronisation.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">It will synchronize your <span style=\" font-style:italic;\">local directory </span>(where the project file and all data are stored on your computer) to the <span style=\" font-style:italic;\">&quot;remotedir&quot; server directory </span>: </p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  - every local updated or non existing file will be sent, </p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  - every remote file which does not exist locally will be removed. </p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Note that only the modified files will be sent to prevent unwanted network usage. </p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">WARNING</span> : all the content of the server directory not related to you local project will be lost !</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QtGui.QApplication.translate("send2server", "Help", None, QtGui.QApplication.UnicodeUTF8))


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    send2server = QtGui.QDialog()
    ui = Ui_send2server()
    ui.setupUi(send2server)
    send2server.show()
    sys.exit(app.exec_())

