from builtins import object
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_lizmap_popup.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_lizmap_popup(object):
    def setupUi(self, lizmap_popup):
        lizmap_popup.setObjectName(_fromUtf8("lizmap_popup"))
        lizmap_popup.setWindowModality(QtCore.Qt.WindowModal)
        lizmap_popup.resize(743, 489)
        self.gridLayout_3 = QtGui.QGridLayout(lizmap_popup)
        self.gridLayout_3.setMargin(6)
        self.gridLayout_3.setObjectName(_fromUtf8("gridLayout_3"))
        self.splitter = QtGui.QSplitter(lizmap_popup)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName(_fromUtf8("splitter"))
        self.groupBox = QtGui.QGroupBox(self.splitter)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.gridLayout_2 = QtGui.QGridLayout(self.groupBox)
        self.gridLayout_2.setMargin(0)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.txtPopup = gui.QgsCodeEditorHTML(self.groupBox)
        self.txtPopup.setObjectName(_fromUtf8("txtPopup"))
        self.gridLayout_2.addWidget(self.txtPopup, 0, 0, 1, 1)
        self.groupBox_2 = QtGui.QGroupBox(self.splitter)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox_2)
        self.gridLayout.setMargin(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.htmlPopup = QtGui.QTextEdit(self.groupBox_2)
        self.htmlPopup.setEnabled(False)
        self.htmlPopup.setObjectName(_fromUtf8("htmlPopup"))
        self.gridLayout.addWidget(self.htmlPopup, 0, 0, 1, 1)
        self.gridLayout_3.addWidget(self.splitter, 0, 0, 1, 1)
        self.bbConfigurePopup = QtGui.QDialogButtonBox(lizmap_popup)
        self.bbConfigurePopup.setOrientation(QtCore.Qt.Horizontal)
        self.bbConfigurePopup.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.bbConfigurePopup.setObjectName(_fromUtf8("bbConfigurePopup"))
        self.gridLayout_3.addWidget(self.bbConfigurePopup, 1, 0, 1, 1)

        self.retranslateUi(lizmap_popup)
        QtCore.QMetaObject.connectSlotsByName(lizmap_popup)
        lizmap_popup.setTabOrder(self.txtPopup, self.htmlPopup)
        lizmap_popup.setTabOrder(self.htmlPopup, self.bbConfigurePopup)

    def retranslateUi(self, lizmap_popup):
        lizmap_popup.setWindowTitle(_translate("lizmap_popup", "Lizmap - Popup", None))
        self.groupBox.setTitle(_translate("lizmap_popup", "Template for the popup", None))
        self.groupBox_2.setTitle(_translate("lizmap_popup", "Preview", None))

from qgis import gui
