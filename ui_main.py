# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_main.ui'
#
# Created: Wed Aug 21 13:46:44 2013
#      by: PyQt4 UI code generator 4.9.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(800, 480)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.lvDestinations = QtGui.QListView(self.centralwidget)
        self.lvDestinations.setGeometry(QtCore.QRect(10, 110, 256, 341))
        font = QtGui.QFont()
        font.setPointSize(32)
        self.lvDestinations.setFont(font)
        self.lvDestinations.setObjectName(_fromUtf8("lvDestinations"))
        self.lblAgent = QtGui.QLabel(self.centralwidget)
        self.lblAgent.setGeometry(QtCore.QRect(280, 120, 511, 61))
        font = QtGui.QFont()
        font.setPointSize(36)
        self.lblAgent.setFont(font)
        self.lblAgent.setObjectName(_fromUtf8("lblAgent"))
        self.lblDistance = QtGui.QLabel(self.centralwidget)
        self.lblDistance.setGeometry(QtCore.QRect(280, 330, 481, 31))
        font = QtGui.QFont()
        font.setPointSize(22)
        self.lblDistance.setFont(font)
        self.lblDistance.setObjectName(_fromUtf8("lblDistance"))
        self.lblBusID = QtGui.QLabel(self.centralwidget)
        self.lblBusID.setGeometry(QtCore.QRect(340, 420, 201, 31))
        font = QtGui.QFont()
        font.setPointSize(22)
        self.lblBusID.setFont(font)
        self.lblBusID.setObjectName(_fromUtf8("lblBusID"))
        self.lblDestination = QtGui.QLabel(self.centralwidget)
        self.lblDestination.setGeometry(QtCore.QRect(280, 180, 491, 61))
        font = QtGui.QFont()
        font.setPointSize(36)
        self.lblDestination.setFont(font)
        self.lblDestination.setObjectName(_fromUtf8("lblDestination"))
        self.lblPrice = QtGui.QLabel(self.centralwidget)
        self.lblPrice.setGeometry(QtCore.QRect(280, 240, 491, 81))
        font = QtGui.QFont()
        font.setPointSize(48)
        self.lblPrice.setFont(font)
        self.lblPrice.setObjectName(_fromUtf8("lblPrice"))
        self.pbPrint = QtGui.QPushButton(self.centralwidget)
        self.pbPrint.setGeometry(QtCore.QRect(600, 370, 191, 81))
        font = QtGui.QFont()
        font.setPointSize(24)
        self.pbPrint.setFont(font)
        self.pbPrint.setObjectName(_fromUtf8("pbPrint"))
        self.pbSwitchDirection = QtGui.QPushButton(self.centralwidget)
        self.pbSwitchDirection.setGeometry(QtCore.QRect(280, 400, 51, 51))
        self.pbSwitchDirection.setObjectName(_fromUtf8("pbSwitchDirection"))
        self.gvTrack = QtGui.QGraphicsView(self.centralwidget)
        self.gvTrack.setGeometry(QtCore.QRect(10, 10, 781, 91))
        self.gvTrack.setObjectName(_fromUtf8("gvTrack"))
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "MainWindow", None, QtGui.QApplication.UnicodeUTF8))
        self.lblAgent.setText(QtGui.QApplication.translate("MainWindow", "Agen", None, QtGui.QApplication.UnicodeUTF8))
        self.lblDistance.setText(QtGui.QApplication.translate("MainWindow", "Jarak", None, QtGui.QApplication.UnicodeUTF8))
        self.lblBusID.setText(QtGui.QApplication.translate("MainWindow", "AA 7880 BZ", None, QtGui.QApplication.UnicodeUTF8))
        self.lblDestination.setText(QtGui.QApplication.translate("MainWindow", "Tujuan", None, QtGui.QApplication.UnicodeUTF8))
        self.lblPrice.setText(QtGui.QApplication.translate("MainWindow", "Harga", None, QtGui.QApplication.UnicodeUTF8))
        self.pbPrint.setText(QtGui.QApplication.translate("MainWindow", "Cetak\n"
"Tiket", None, QtGui.QApplication.UnicodeUTF8))
        self.pbSwitchDirection.setText(QtGui.QApplication.translate("MainWindow", "<->", None, QtGui.QApplication.UnicodeUTF8))

