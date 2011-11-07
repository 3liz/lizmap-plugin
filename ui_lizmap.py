# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_lizmap.ui'
#
# Created: Mon Nov  7 12:10:50 2011
#      by: PyQt4 UI code generator 4.8.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_lizmap(object):
    def setupUi(self, lizmap):
        lizmap.setObjectName(_fromUtf8("lizmap"))
        lizmap.resize(589, 463)
        self.tabWidget = QtGui.QTabWidget(lizmap)
        self.tabWidget.setGeometry(QtCore.QRect(10, 0, 571, 421))
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tab_2 = QtGui.QWidget()
        self.tab_2.setObjectName(_fromUtf8("tab_2"))
        self.treeLayer = QtGui.QTreeWidget(self.tab_2)
        self.treeLayer.setGeometry(QtCore.QRect(10, 10, 350, 341))
        self.treeLayer.setColumnCount(1)
        self.treeLayer.setObjectName(_fromUtf8("treeLayer"))
        self.treeLayer.headerItem().setText(0, _fromUtf8("Name"))
        self.treeLayer.header().setDefaultSectionSize(50)
        self.treeLayer.header().setMinimumSectionSize(50)
        self.treeLayer.header().setStretchLastSection(True)
        self.verticalLayoutWidget = QtGui.QWidget(self.tab_2)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(370, 10, 191, 355))
        self.verticalLayoutWidget.setObjectName(_fromUtf8("verticalLayoutWidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label_7 = QtGui.QLabel(self.verticalLayoutWidget)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.verticalLayout.addWidget(self.label_7)
        self.inLayerTitle = QtGui.QLineEdit(self.verticalLayoutWidget)
        self.inLayerTitle.setObjectName(_fromUtf8("inLayerTitle"))
        self.verticalLayout.addWidget(self.inLayerTitle)
        self.label_8 = QtGui.QLabel(self.verticalLayoutWidget)
        self.label_8.setObjectName(_fromUtf8("label_8"))
        self.verticalLayout.addWidget(self.label_8)
        self.teLayerAbstract = QtGui.QTextEdit(self.verticalLayoutWidget)
        self.teLayerAbstract.setObjectName(_fromUtf8("teLayerAbstract"))
        self.verticalLayout.addWidget(self.teLayerAbstract)
        self.label_10 = QtGui.QLabel(self.verticalLayoutWidget)
        self.label_10.setObjectName(_fromUtf8("label_10"))
        self.verticalLayout.addWidget(self.label_10)
        self.inLayerLink = QtGui.QLineEdit(self.verticalLayoutWidget)
        self.inLayerLink.setObjectName(_fromUtf8("inLayerLink"))
        self.verticalLayout.addWidget(self.inLayerLink)
        self.cbLayerIsBaseLayer = QtGui.QCheckBox(self.verticalLayoutWidget)
        self.cbLayerIsBaseLayer.setObjectName(_fromUtf8("cbLayerIsBaseLayer"))
        self.verticalLayout.addWidget(self.cbLayerIsBaseLayer)
        self.cbGroupAsLayer = QtGui.QCheckBox(self.verticalLayoutWidget)
        self.cbGroupAsLayer.setObjectName(_fromUtf8("cbGroupAsLayer"))
        self.verticalLayout.addWidget(self.cbGroupAsLayer)
        self.cbToggled = QtGui.QCheckBox(self.verticalLayoutWidget)
        self.cbToggled.setObjectName(_fromUtf8("cbToggled"))
        self.verticalLayout.addWidget(self.cbToggled)
        self.cbSingleTile = QtGui.QCheckBox(self.verticalLayoutWidget)
        self.cbSingleTile.setObjectName(_fromUtf8("cbSingleTile"))
        self.verticalLayout.addWidget(self.cbSingleTile)
        self.cbCached = QtGui.QCheckBox(self.verticalLayoutWidget)
        self.cbCached.setObjectName(_fromUtf8("cbCached"))
        self.verticalLayout.addWidget(self.cbCached)
        self.btRefreshTree = QtGui.QPushButton(self.tab_2)
        self.btRefreshTree.setGeometry(QtCore.QRect(250, 353, 111, 31))
        self.btRefreshTree.setObjectName(_fromUtf8("btRefreshTree"))
        self.tabWidget.addTab(self.tab_2, _fromUtf8(""))
        self.tab_3 = QtGui.QWidget()
        self.tab_3.setObjectName(_fromUtf8("tab_3"))
        self.verticalLayoutWidget_2 = QtGui.QWidget(self.tab_3)
        self.verticalLayoutWidget_2.setGeometry(QtCore.QRect(20, 20, 531, 280))
        self.verticalLayoutWidget_2.setObjectName(_fromUtf8("verticalLayoutWidget_2"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.verticalLayoutWidget_2)
        self.verticalLayout_2.setMargin(0)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.label_16 = QtGui.QLabel(self.verticalLayoutWidget_2)
        font = QtGui.QFont()
        font.setWeight(75)
        font.setBold(True)
        self.label_16.setFont(font)
        self.label_16.setObjectName(_fromUtf8("label_16"))
        self.verticalLayout_2.addWidget(self.label_16)
        self.horizontalLayout_8 = QtGui.QHBoxLayout()
        self.horizontalLayout_8.setObjectName(_fromUtf8("horizontalLayout_8"))
        self.label_9 = QtGui.QLabel(self.verticalLayoutWidget_2)
        self.label_9.setObjectName(_fromUtf8("label_9"))
        self.horizontalLayout_8.addWidget(self.label_9)
        self.liImageFormat = QtGui.QComboBox(self.verticalLayoutWidget_2)
        self.liImageFormat.setObjectName(_fromUtf8("liImageFormat"))
        self.liImageFormat.addItem(_fromUtf8(""))
        self.liImageFormat.addItem(_fromUtf8(""))
        self.horizontalLayout_8.addWidget(self.liImageFormat)
        self.verticalLayout_2.addLayout(self.horizontalLayout_8)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        spacerItem1 = QtGui.QSpacerItem(20, 60, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem1)
        self.label_15 = QtGui.QLabel(self.verticalLayoutWidget_2)
        font = QtGui.QFont()
        font.setWeight(75)
        font.setBold(True)
        self.label_15.setFont(font)
        self.label_15.setObjectName(_fromUtf8("label_15"))
        self.verticalLayout_2.addWidget(self.label_15)
        self.horizontalLayout_12 = QtGui.QHBoxLayout()
        self.horizontalLayout_12.setObjectName(_fromUtf8("horizontalLayout_12"))
        self.label_13 = QtGui.QLabel(self.verticalLayoutWidget_2)
        self.label_13.setObjectName(_fromUtf8("label_13"))
        self.horizontalLayout_12.addWidget(self.label_13)
        self.inMinScale = QtGui.QLineEdit(self.verticalLayoutWidget_2)
        self.inMinScale.setInputMethodHints(QtCore.Qt.ImhDigitsOnly)
        self.inMinScale.setMaxLength(10)
        self.inMinScale.setObjectName(_fromUtf8("inMinScale"))
        self.horizontalLayout_12.addWidget(self.inMinScale)
        self.verticalLayout_2.addLayout(self.horizontalLayout_12)
        self.horizontalLayout_13 = QtGui.QHBoxLayout()
        self.horizontalLayout_13.setObjectName(_fromUtf8("horizontalLayout_13"))
        self.label_14 = QtGui.QLabel(self.verticalLayoutWidget_2)
        self.label_14.setObjectName(_fromUtf8("label_14"))
        self.horizontalLayout_13.addWidget(self.label_14)
        self.inMaxScale = QtGui.QLineEdit(self.verticalLayoutWidget_2)
        self.inMaxScale.setInputMethodHints(QtCore.Qt.ImhDigitsOnly)
        self.inMaxScale.setMaxLength(10)
        self.inMaxScale.setObjectName(_fromUtf8("inMaxScale"))
        self.horizontalLayout_13.addWidget(self.inMaxScale)
        self.verticalLayout_2.addLayout(self.horizontalLayout_13)
        self.horizontalLayout_14 = QtGui.QHBoxLayout()
        self.horizontalLayout_14.setObjectName(_fromUtf8("horizontalLayout_14"))
        self.label_17 = QtGui.QLabel(self.verticalLayoutWidget_2)
        self.label_17.setObjectName(_fromUtf8("label_17"))
        self.horizontalLayout_14.addWidget(self.label_17)
        self.inZoomLevelNumber = QtGui.QLineEdit(self.verticalLayoutWidget_2)
        self.inZoomLevelNumber.setInputMethodHints(QtCore.Qt.ImhDigitsOnly)
        self.inZoomLevelNumber.setMaxLength(2)
        self.inZoomLevelNumber.setObjectName(_fromUtf8("inZoomLevelNumber"))
        self.horizontalLayout_14.addWidget(self.inZoomLevelNumber)
        self.verticalLayout_2.addLayout(self.horizontalLayout_14)
        self.label_18 = QtGui.QLabel(self.verticalLayoutWidget_2)
        font = QtGui.QFont()
        font.setWeight(75)
        font.setBold(True)
        self.label_18.setFont(font)
        self.label_18.setObjectName(_fromUtf8("label_18"))
        self.verticalLayout_2.addWidget(self.label_18)
        self.horizontalLayout_15 = QtGui.QHBoxLayout()
        self.horizontalLayout_15.setObjectName(_fromUtf8("horizontalLayout_15"))
        self.label_19 = QtGui.QLabel(self.verticalLayoutWidget_2)
        self.label_19.setObjectName(_fromUtf8("label_19"))
        self.horizontalLayout_15.addWidget(self.label_19)
        self.inMapScales = QtGui.QLineEdit(self.verticalLayoutWidget_2)
        self.inMapScales.setInputMethodHints(QtCore.Qt.ImhDigitsOnly)
        self.inMapScales.setObjectName(_fromUtf8("inMapScales"))
        self.horizontalLayout_15.addWidget(self.inMapScales)
        self.verticalLayout_2.addLayout(self.horizontalLayout_15)
        self.tabWidget.addTab(self.tab_3, _fromUtf8(""))
        self.tab_ftp = QtGui.QWidget()
        self.tab_ftp.setObjectName(_fromUtf8("tab_ftp"))
        self.horizontalLayoutWidget_3 = QtGui.QWidget(self.tab_ftp)
        self.horizontalLayoutWidget_3.setGeometry(QtCore.QRect(10, 60, 261, 51))
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
        self.horizontalLayoutWidget_2.setGeometry(QtCore.QRect(470, 10, 91, 41))
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
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(10, 10, 431, 41))
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
        self.horizontalLayoutWidget_5.setGeometry(QtCore.QRect(10, 180, 551, 51))
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
        self.horizontalLayoutWidget_4.setGeometry(QtCore.QRect(290, 60, 271, 51))
        self.horizontalLayoutWidget_4.setObjectName(_fromUtf8("horizontalLayoutWidget_4"))
        self.horizontalLayout_4 = QtGui.QHBoxLayout(self.horizontalLayoutWidget_4)
        self.horizontalLayout_4.setMargin(0)
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.label_4 = QtGui.QLabel(self.horizontalLayoutWidget_4)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.horizontalLayout_4.addWidget(self.label_4)
        self.inPassword = QtGui.QLineEdit(self.horizontalLayoutWidget_4)
        self.inPassword.setInputMethodHints(QtCore.Qt.ImhHiddenText|QtCore.Qt.ImhNoAutoUppercase|QtCore.Qt.ImhNoPredictiveText)
        self.inPassword.setEchoMode(QtGui.QLineEdit.Password)
        self.inPassword.setObjectName(_fromUtf8("inPassword"))
        self.horizontalLayout_4.addWidget(self.inPassword)
        self.horizontalLayoutWidget_6 = QtGui.QWidget(self.tab_ftp)
        self.horizontalLayoutWidget_6.setGeometry(QtCore.QRect(10, 120, 551, 51))
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
        self.outLog = QtGui.QTextEdit(self.tab_main)
        self.outLog.setGeometry(QtCore.QRect(10, 10, 551, 331))
        self.outLog.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.outLog.setReadOnly(True)
        self.outLog.setObjectName(_fromUtf8("outLog"))
        self.outState = QtGui.QLabel(self.tab_main)
        self.outState.setGeometry(QtCore.QRect(450, 353, 81, 21))
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setWeight(75)
        font.setBold(True)
        self.outState.setFont(font)
        self.outState.setText(_fromUtf8(""))
        self.outState.setObjectName(_fromUtf8("outState"))
        self.btClearlog = QtGui.QPushButton(self.tab_main)
        self.btClearlog.setGeometry(QtCore.QRect(10, 350, 291, 27))
        self.btClearlog.setObjectName(_fromUtf8("btClearlog"))
        self.btCancelFtpSync = QtGui.QPushButton(self.tab_main)
        self.btCancelFtpSync.setEnabled(True)
        self.btCancelFtpSync.setGeometry(QtCore.QRect(320, 350, 97, 27))
        self.btCancelFtpSync.setObjectName(_fromUtf8("btCancelFtpSync"))
        self.tabWidget.addTab(self.tab_main, _fromUtf8(""))
        self.tab = QtGui.QWidget()
        self.tab.setObjectName(_fromUtf8("tab"))
        self.textEdit = QtGui.QTextEdit(self.tab)
        self.textEdit.setEnabled(True)
        self.textEdit.setGeometry(QtCore.QRect(10, 10, 551, 351))
        self.textEdit.setReadOnly(True)
        self.textEdit.setObjectName(_fromUtf8("textEdit"))
        self.tabWidget.addTab(self.tab, _fromUtf8(""))
        self.tab_4 = QtGui.QWidget()
        self.tab_4.setObjectName(_fromUtf8("tab_4"))
        self.txtAbout = QtGui.QTextEdit(self.tab_4)
        self.txtAbout.setEnabled(True)
        self.txtAbout.setGeometry(QtCore.QRect(10, 10, 551, 351))
        self.txtAbout.setReadOnly(True)
        self.txtAbout.setObjectName(_fromUtf8("txtAbout"))
        self.tabWidget.addTab(self.tab_4, _fromUtf8(""))
        self.btSave = QtGui.QPushButton(lizmap)
        self.btSave.setGeometry(QtCore.QRect(340, 426, 85, 31))
        self.btSave.setObjectName(_fromUtf8("btSave"))
        self.btSync = QtGui.QPushButton(lizmap)
        self.btSync.setEnabled(True)
        self.btSync.setGeometry(QtCore.QRect(431, 426, 154, 31))
        self.btSync.setObjectName(_fromUtf8("btSync"))

        self.retranslateUi(lizmap)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(lizmap)
        lizmap.setTabOrder(self.tabWidget, self.treeLayer)
        lizmap.setTabOrder(self.treeLayer, self.inLayerTitle)
        lizmap.setTabOrder(self.inLayerTitle, self.teLayerAbstract)
        lizmap.setTabOrder(self.teLayerAbstract, self.inLayerLink)
        lizmap.setTabOrder(self.inLayerLink, self.cbLayerIsBaseLayer)
        lizmap.setTabOrder(self.cbLayerIsBaseLayer, self.cbGroupAsLayer)
        lizmap.setTabOrder(self.cbGroupAsLayer, self.cbToggled)
        lizmap.setTabOrder(self.cbToggled, self.cbSingleTile)
        lizmap.setTabOrder(self.cbSingleTile, self.cbCached)
        lizmap.setTabOrder(self.cbCached, self.btRefreshTree)
        lizmap.setTabOrder(self.btRefreshTree, self.liImageFormat)
        lizmap.setTabOrder(self.liImageFormat, self.inMinScale)
        lizmap.setTabOrder(self.inMinScale, self.inMaxScale)
        lizmap.setTabOrder(self.inMaxScale, self.inZoomLevelNumber)
        lizmap.setTabOrder(self.inZoomLevelNumber, self.inMapScales)
        lizmap.setTabOrder(self.inMapScales, self.inHost)
        lizmap.setTabOrder(self.inHost, self.inPort)
        lizmap.setTabOrder(self.inPort, self.inUsername)
        lizmap.setTabOrder(self.inUsername, self.inPassword)
        lizmap.setTabOrder(self.inPassword, self.inRemotedir)
        lizmap.setTabOrder(self.inRemotedir, self.inLocaldir)
        lizmap.setTabOrder(self.inLocaldir, self.outLog)
        lizmap.setTabOrder(self.outLog, self.btClearlog)
        lizmap.setTabOrder(self.btClearlog, self.textEdit)
        lizmap.setTabOrder(self.textEdit, self.txtAbout)
        lizmap.setTabOrder(self.txtAbout, self.btSave)
        lizmap.setTabOrder(self.btSave, self.btSync)

    def retranslateUi(self, lizmap):
        lizmap.setWindowTitle(QtGui.QApplication.translate("lizmap", "LizMap", None, QtGui.QApplication.UnicodeUTF8))
        self.label_7.setText(QtGui.QApplication.translate("lizmap", "Title", None, QtGui.QApplication.UnicodeUTF8))
        self.label_8.setText(QtGui.QApplication.translate("lizmap", "Abstract", None, QtGui.QApplication.UnicodeUTF8))
        self.label_10.setText(QtGui.QApplication.translate("lizmap", "Link", None, QtGui.QApplication.UnicodeUTF8))
        self.cbLayerIsBaseLayer.setText(QtGui.QApplication.translate("lizmap", "Base layer ?", None, QtGui.QApplication.UnicodeUTF8))
        self.cbGroupAsLayer.setText(QtGui.QApplication.translate("lizmap", "Group as a layer ?", None, QtGui.QApplication.UnicodeUTF8))
        self.cbToggled.setText(QtGui.QApplication.translate("lizmap", "Toggled ?", None, QtGui.QApplication.UnicodeUTF8))
        self.cbSingleTile.setText(QtGui.QApplication.translate("lizmap", "Singletile ?", None, QtGui.QApplication.UnicodeUTF8))
        self.cbCached.setText(QtGui.QApplication.translate("lizmap", "Cached ?", None, QtGui.QApplication.UnicodeUTF8))
        self.btRefreshTree.setText(QtGui.QApplication.translate("lizmap", "Refresh tree", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QtGui.QApplication.translate("lizmap", "Layers", None, QtGui.QApplication.UnicodeUTF8))
        self.label_16.setText(QtGui.QApplication.translate("lizmap", "Optimization", None, QtGui.QApplication.UnicodeUTF8))
        self.label_9.setText(QtGui.QApplication.translate("lizmap", "Image format", None, QtGui.QApplication.UnicodeUTF8))
        self.liImageFormat.setItemText(0, QtGui.QApplication.translate("lizmap", "png", None, QtGui.QApplication.UnicodeUTF8))
        self.liImageFormat.setItemText(1, QtGui.QApplication.translate("lizmap", "jpg", None, QtGui.QApplication.UnicodeUTF8))
        self.label_15.setText(QtGui.QApplication.translate("lizmap", "Scales", None, QtGui.QApplication.UnicodeUTF8))
        self.label_13.setText(QtGui.QApplication.translate("lizmap", "Min. Scale :  1/", None, QtGui.QApplication.UnicodeUTF8))
        self.label_14.setText(QtGui.QApplication.translate("lizmap", "Max. Scale : 1/", None, QtGui.QApplication.UnicodeUTF8))
        self.label_17.setText(QtGui.QApplication.translate("lizmap", "Zoom levels number", None, QtGui.QApplication.UnicodeUTF8))
        self.label_18.setText(QtGui.QApplication.translate("lizmap", "  or", None, QtGui.QApplication.UnicodeUTF8))
        self.label_19.setText(QtGui.QApplication.translate("lizmap", "Scales (ex:100000,20000)", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QtGui.QApplication.translate("lizmap", "Map options", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("lizmap", "Username", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("lizmap", "Port", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("lizmap", "Host", None, QtGui.QApplication.UnicodeUTF8))
        self.label_5.setText(QtGui.QApplication.translate("lizmap", "Local Dir", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("lizmap", "Password", None, QtGui.QApplication.UnicodeUTF8))
        self.label_6.setText(QtGui.QApplication.translate("lizmap", "Remote Dir", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_ftp), QtGui.QApplication.translate("lizmap", "FTP options", None, QtGui.QApplication.UnicodeUTF8))
        self.btClearlog.setText(QtGui.QApplication.translate("lizmap", "Clear log", None, QtGui.QApplication.UnicodeUTF8))
        self.btCancelFtpSync.setText(QtGui.QApplication.translate("lizmap", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_main), QtGui.QApplication.translate("lizmap", "Log", None, QtGui.QApplication.UnicodeUTF8))
        self.textEdit.setHtml(QtGui.QApplication.translate("lizmap", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Ubuntu\'; font-size:11pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Prerequisites</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">*************</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600; font-style:italic;\">Qgis side</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Project must be saved</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Project projection must be set</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Projections must be set for each layer</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Data (vector and raster) must be stored in the same folder of the project file, or in a subfolder</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Project paths must be set to &quot;relative&quot; (see project properties)</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* WMS options must be set in the project properties</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* The FTP synchronisation only works on linux and windows operating systems. On Linux plateforms, the software lftp must have been installed. On Windows plaforms, WinSCP Portable is used and is already contained in Lizmap plugin directory.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600; font-style:italic;\">Server side</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* QgisMapserver must be installed.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* You need FTP write access to a directory aka remotedir in this help.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Lizmap must be installed and correctly configured.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Usage</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">************</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Please read the following desription of each interface tab first. The usage scenario is written further down.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Layers</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">*************</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">This tab shows the exact tree of groups and layers from your project. With this tree, you can several options for each group or layer just by selecting a group/layer in the tree. Then you can edit the input fields right to the tree :</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Title</span> : the title of the group/layer. You can use this field to rename the group or layer. For example, you could have a layer called &quot;main_rivers&quot;, and title it &quot;Main rivers&quot;. This title will be displayed by Lizmap web application, not the layer/group name.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Abstract</span> : a short description of the group/layer. This abstract will be shown on hover of the title in Lizmap web app.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Link</span> : an html link such as &quot;http://qgis.org&quot;. If a link is given for a group or a layer, an icon &quot;(i)&quot; will be shown next to the group/layer title in Lizmap. Clicking on the icon will open a new browser window pointing to this link.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Base layer</span>  : If this checkbox is checked, the group/layer will appear in the list of base layers. If not, the group/layer will appear in the list of overview layers.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Group as layer</span> : This checkbox is only usefull for groups. By checking it, you can transform a qgis group (with child groups and/or layers) into a single layer in Lizmap web application. The children won\'t appear in Lizmap layer lists. The legend for this group will display every child legend.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Toggled</span> : If checked, the group/layer will be also checked and visible in Lizmap. If not, the user will have to check it manually.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Singletile</span> : If checked, Lizmap web application will display a single image corresponding to the map viewport. If not, Lizmap will ask for several small images (tiles) to fill the viewport. You can choose singletile to avoid truncated labels.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Cached</span> : If the server administrators has set up a tile caching system, you can check a group/layer to tell Lizmap to use the cache server instead of Qgis Server. The tile cache server must have been configured with the project extent, projection and the adequate layers.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Map options</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">*************</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">In this tab, you can edit some basic options for the map displayed by Lizmap web application :</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Image format</span> : Choose betwen &quot;png&quot; or &quot;jpg&quot;. Png is often a good choice. It respects transparency. Jpg will produce smaller images though.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Min. Scale</span><span style=\" font-weight:600;\"> </span>: The minimum scale of Lizmap map. E.g &quot;10000&quot;</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Max. Scale</span> : The maximum scale of Lizmap map. E.g &quot;1000000&quot;</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Zoom leves number</span> : The number of zoom levels of Lizmap map between max scale and min scale. E.g. 10.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Scales</span> : You can overwrite the 3 previous options (min and max scale, zoom level number) by entering a list of scales you want to display in Lizmap map. The scales must be separated by commas &quot;,&quot;. E.g. &quot;1000000, 500000, 200000&quot;.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">FTP options</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">*************</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">In this tab, you can write and edit FTP options to tell the plugin where and how to store your local project data on the server :</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">host</span> : FTP host, corresponding to the server where Qgis Server is installed (ip address or domain)</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">username</span> = Ftp username</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">password</span> = Ftp password</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">port</span> = Ftp port (21 if not given)</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">remotedir</span> = Path to the directory where all your qgis project data (project file, rasters and vectors) must be sent. </p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">- For Windows users, you must give a full path, for exemple : &quot;/home/username/myremotedir/&quot; (please ask the server admin for the complete path to you FTP root folder).</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">- For linux users, just use a relative path, such as &quot;/myremotedir/&quot;</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Log</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">*************</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">This tab shows the log written when clicking on &quot;Save&quot; or &quot;Save and Sync&quot; buttons:</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* The small input shows file operations processed during a FTP sync.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* The big text area shows the actions made by the plugin : input data checking, ftp actions report, warnings and errors.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* When performing a FTP synchronisation, an orange message &quot;running&quot; is written next to the &quot;Clear log&quot; button, and a small progress bar moves from 0 to 1 each time an FTP operation has been made. </p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* You can cancel a FTP Synchronization by clicking the &quot;Cancel&quot; button in the Log tab.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* You can clear the log by clicking on the &quot;Clear log&quot; button.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Help</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">*************</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">The tab you are reading now.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Usage</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">*************</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600;\">Read this help</span> with care.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Check that you have properly set your <span style=\" font-weight:600;\">project options</span>.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Edit the options in <span style=\" font-weight:600;\">each plugin tab</span>.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Click the &quot;<span style=\" font-weight:600;\">Save</span>&quot; button will save the configuration in a file stored next to your qgis project file. Then you will have to manually send the modified files (project, config file, raster and vector data, etc.) from your computer to the remote FTP directory.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* Click the &quot;<span style=\" font-weight:600;\">Save and synchronize</span>&quot; button will first save the configuration. It will then synchronize your <span style=\" font-weight:600;\">local directory</span><span style=\" font-style:italic;\"> </span>(where the project file and all data are stored on your computer) to the <span style=\" font-weight:600;\">&quot;remotedir&quot; server directory </span>: </p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  - every local updated or non existing file will be sent, </p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">  - every remote file which does not exist locally will be <span style=\" font-weight:600;\">removed</span>. </p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Note that only the modified files will be sent to prevent unwanted network usage.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">WARNING</span> :<span style=\" font-weight:600;\"> all the content of the server directory not related to your local project will be lost !</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600; font-style:italic;\">*** Alway have a fresh backup of your local project and data files ! ***</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Lizmap Hints</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">*************</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Lizmap Qgis plugin aims to be used to configure a web application dynamically generated by Lizmap (php/html/css/js) with the help of Qgis Server. With this plugin, you can configure one web map per Qgis project. Details on each tab is given above.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Things to consider :</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Configuration backup</span> :</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">The layers, map and ftp options are saved each time &quot;Save&quot; or &quot;Save and synchronize&quot; are launched :</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">- <span style=\" font-style:italic;\">layers and map options</span> are stored in a configuration file in the same folder as Qgis project file. E.g. projectname.qgs.cfg if your project file is called projectname.qgs. When you open a project in Qgis and then launch lizmap plugin, the input fields will be set accordingly if possible (e.g. if you have not change the name of the layers)</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">- <span style=\" font-style:italic;\">FTP options</span> are stored in lizmap.cfg file in lizmap plugin folder. It means you must check the FTP options each time you run the plugin in case you work on different project with different FTP server options.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Project options</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Some of the project options are not displayed in lizmap plugin but are indeed used by Lizmap web application : WMS options, project name and description, projection, extent, etc.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Group and layers visibility</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">- <span style=\" font-style:italic;\">min and maxscales </span>: A layer will be active and visible on map in Lizmap web application only if the current zoom level matches the min and max scales if this visibility is set in the layer properties dialog.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">- a group wich has the <span style=\" font-style:italic;\">&quot;Group as layer&quot;</span> option checked will be visible as soon as one of its child layers is visible.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">* <span style=\" font-weight:600; font-style:italic;\">Overview</span> : </p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">If there is a group name &quot;<span style=\" font-style:italic;\">Overview</span>&quot; (with the capital O at the beginning) in your qgis project, there will be a small Overview map displayed in Lizmap web application. These layers won\'t be displayed in the main map. Please check the layers of this group are visible at all scales. </p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QtGui.QApplication.translate("lizmap", "Help", None, QtGui.QApplication.UnicodeUTF8))
        self.txtAbout.setHtml(QtGui.QApplication.translate("lizmap", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Ubuntu\'; font-size:11pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">***************</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600;\">Lizmap 1.0</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Publication plugin for Lizmap web application, by 3LIZ</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">    begin          : 2011-11-01</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">    copyright : (C) 2011 by 3liz</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">    authors     : René-Luc D\'Hont and Michaël Douchin</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">    email          : info@3liz.com</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">    website     : <a href=\"http://www.3liz.com\"><span style=\" text-decoration: underline; color:#0000ff;\">http://www.3liz.com</span></a></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Lizmap Qgis plugin aims to be used to configure a web application dynamically generated by Lizmap (php/html/css/js) with the help of <a href=\"www.qgis.org/wiki/QGIS_Server_Tutorial\"><span style=\" text-decoration: underline; color:#0000ff;\">Qgis Server</span></a> ( http://www.qgis.org/wiki/QGIS_Server_Tutorial ) With this plugin, you can configure one web map per Qgis project. The Lizmap web application must be installed on the server.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">We like to thank the members of <a href=\"http://www.alise-geomatique.fr\"><span style=\" text-decoration: underline; color:#0000ff;\">Alisé Géomatique</span></a> ( http://www.alise-geomatique.fr ) a french company, for the help the provided by reporting bugs and asking for new features during the development of Lizmap Qgis plugin and web application.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">******  <span style=\" font-weight:600;\">LICENSE</span>  *****</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Version: MPL 1.1/GPL 2.0/LGPL 2.1</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">The contents of this file are subject to the Mozilla Public License Version 1.1 (the &quot;License&quot;); you may not use this file except in compliance with the License. You may obtain a copy of the License at <a href=\"http://www.mozilla.org/MPL/\"><span style=\" text-decoration: underline; color:#0000ff;\">http://www.mozilla.org/MPL/</span></a></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Software distributed under the License is distributed on an &quot;AS IS&quot; basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License for the specific language governing rights and limitations under the License.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">The Original Code is 3liz code,</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">The Initial Developer of the Original Code are René-Luc D\'Hont rldhont@3liz.com and Michael Douchin mdouchin@3liz.com </p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Portions created by the Initial Developer are Copyright (C) 2011 the Initial Developer. All Rights Reserved.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Alternatively, the contents of this file may be used under the terms of either of the GNU General Public License Version 2 or later (the &quot;GPL&quot;), or the GNU Lesser General Public License Version 2.1 or later (the &quot;LGPL&quot;), in which case the provisions of the GPL or the LGPL are applicable instead of those above. If you wish to allow use of your version of this file only under the terms of either the GPL or the LGPL, and not to allow others to use your version of this file under the terms of the MPL, indicate your decision by deleting the provisions above and replace them with the notice and other provisions required by the GPL or the LGPL. If you do not delete the provisions above, a recipient may use your version of this file under the terms of any one of the MPL, the GPL or the LGPL.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4), QtGui.QApplication.translate("lizmap", "About", None, QtGui.QApplication.UnicodeUTF8))
        self.btSave.setText(QtGui.QApplication.translate("lizmap", "Save", None, QtGui.QApplication.UnicodeUTF8))
        self.btSync.setText(QtGui.QApplication.translate("lizmap", "Save and synchronize", None, QtGui.QApplication.UnicodeUTF8))


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    lizmap = QtGui.QDialog()
    ui = Ui_lizmap()
    ui.setupUi(lizmap)
    lizmap.show()
    sys.exit(app.exec_())

