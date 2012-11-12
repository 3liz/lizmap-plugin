# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_lizmap_popup.ui'
#
# Created: Mon Nov  5 17:24:21 2012
#      by: PyQt4 UI code generator 4.9.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_lizmap_popup(object):
    def setupUi(self, lizmap_popup):
        lizmap_popup.setObjectName(_fromUtf8("lizmap_popup"))
        lizmap_popup.setWindowModality(QtCore.Qt.WindowModal)
        lizmap_popup.resize(448, 391)
        self.verticalLayout = QtGui.QVBoxLayout(lizmap_popup)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(lizmap_popup)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.txtPopup = QtGui.QTextEdit(lizmap_popup)
        self.txtPopup.setObjectName(_fromUtf8("txtPopup"))
        self.verticalLayout.addWidget(self.txtPopup)
        self.label_2 = QtGui.QLabel(lizmap_popup)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.verticalLayout.addWidget(self.label_2)
        self.htmlPopup = QtGui.QTextEdit(lizmap_popup)
        self.htmlPopup.setEnabled(False)
        self.htmlPopup.setObjectName(_fromUtf8("htmlPopup"))
        self.verticalLayout.addWidget(self.htmlPopup)
        self.bbConfigurePopup = QtGui.QDialogButtonBox(lizmap_popup)
        self.bbConfigurePopup.setOrientation(QtCore.Qt.Horizontal)
        self.bbConfigurePopup.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.bbConfigurePopup.setObjectName(_fromUtf8("bbConfigurePopup"))
        self.verticalLayout.addWidget(self.bbConfigurePopup)

        self.retranslateUi(lizmap_popup)
        QtCore.QMetaObject.connectSlotsByName(lizmap_popup)
        lizmap_popup.setTabOrder(self.txtPopup, self.htmlPopup)
        lizmap_popup.setTabOrder(self.htmlPopup, self.bbConfigurePopup)

    def retranslateUi(self, lizmap_popup):
        lizmap_popup.setWindowTitle(QtGui.QApplication.translate("lizmap_popup", "Lizmap - Popup", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("lizmap_popup", "ui.popup.source.label", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("lizmap_popup", "ui.popup.html.label", None, QtGui.QApplication.UnicodeUTF8))

