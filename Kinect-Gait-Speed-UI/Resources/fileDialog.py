import sys, os 
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QFile
from PyQt5.QtWidgets import QDialog, QApplication, QFileDialog
from PyQt5.uic import loadUi

class fileWindow(QDialog): 
    def __init__(self): 
        super(fileWindow, self).__init__()
        self._UIPath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "UI")
        self._UIPath = os.path.join(self._UIPath, "imageSelectionUI.ui")

        # Now Load The UI 
        loadUi(self._UIPath, self)
        self.pushButton.clicked.connect(self.viewFiles)
        self.pushButton_2.clicked.connect(self.generateImage)

        # Flag to inform if the window was closed via the X button 
        self._ButtonPressed = False 
        # Variable to save file name 
        self._FileName = None 

    # Call the file explorer 
    def viewFiles(self): 
        self._FileName = QFileDialog.getOpenFileName(self, "Choose Image", os.getcwd(), "Images (*.png)")
        self._FileName = self._FileName[0]
        if self._FileName == '':
            self._FileName = None
        self._ButtonPressed = True 
        self.close()

    # Just to inform the calling program that a button was pressed    
    def generateImage(self): 
        self._ButtonPressed = True 
        self.close()

    def getFileName(self):
        return self._FileName
    
    def wasButtonPressed(self): 
        return self._ButtonPressed
    '''
    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self._ButtonPressed = False
        print("Closed")
        return super().closeEvent(a0)
    '''
'''
app = QApplication(sys.argv)
mainWindow = fileWindow()
widget = QtWidgets.QStackedWidget()
widget.addWidget(mainWindow)
widget.setFixedHeight(400)
widget.setFixedWidth(400)
widget.show()
sys.exit(app.exec_())
'''