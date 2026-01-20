import torch
from spectrai import App
from PyQt5 import QtWidgets
import sys

app = QtWidgets.QApplication(sys.argv)
MainWindow = App()
MainWindow.show()
sys.exit(app.exec_())