#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui

from dialogs.mainwindow import MainWindow

def main():
    # Точка входа
    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()