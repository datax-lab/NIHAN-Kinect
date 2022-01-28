
import sys, os, time, cv2

# PyQt5 
from PyQt5 import Qt, QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog, QApplication, QMainWindow
from UI import ptInfoUI, programSelection

from Runtime.kyphosisUI import kyphosisControl
from Runtime.gaitSpeedUI import controlPanelGait


from Resources.data import DataHandler


# AKA the patient information window 
class mainWindow(QDialog): 
    
    def __init__(self): 
        super(mainWindow, self).__init__()
        self._Window = ptInfoUI.Ui_Dialog()
        self._Window.setupUi(self)
        # Connect the Buttons 
        self.connectButtons()
        # Instantiate the Other Windows
        self._GaitControlPanel, self._KyphosisPanel = controlPanelGait(), kyphosisControl()
        self._ProgramSelector = programSelectorUI()

        # Wait for Signal to See which Program To Run 
        self._ProgramSelector.programSelectionChoice.connect(self.programChoice)

        # Database Links 
        self._Database = DataHandler()
        self._PatientName, self._PatientID = None, None        

    def connectButtons(self):
        self._Window.pushButton.clicked.connect(self.registAccount)
        self._Window.pushButton_2.clicked.connect(self.verifyPt)

    def registAccount(self): 
        # Grab The information from the input
        self._PatientName, self._PatientID = self._Window.lineEdit.text(), self._Window.lineEdit_2.text()
        
        # check to see if input is not empty
        if self._PatientID == "" or self._PatientName == "":
            self._Window.label_3.setStyleSheet("background-color: red; color: white")
            self._Window.label_3.setText("Error, Do Not Leave Any Fields Empty!!!")
            self._PatientName, self._PatientID = None, None
        else:  
            if self._Database.createPatient((str(self._PatientID), str(self._PatientName))) < 0: 
                self._Window.label_3.setStyleSheet("background-color: red; color: white")
                self._Window.label_3.setText("Error, Patient Already Exists in the Database! Press Verify and Continue instead!")
                self._PatientName, self._PatientID = None, None
                
            
            self.continueToProgramSelector()
    
    def verifyPt(self): 
        # This is where I would first verify if the pt is in the database, output error message if not
        # use setText to output the Error if a patient was not found in the database and tell to register
        self._PatientName, self._PatientID = self._Window.lineEdit.text(), self._Window.lineEdit_2.text()
        # This is where i will check if the fields are not empty, if they are launch pop up, or change the text to output the error 
        if  self._PatientID == "" or self._PatientName == "":
            self._Window.label_3.setStyleSheet("background-color: red; color: white")
            self._Window.label_3.setText("Error, Do Not Leave Any Fields Empty!!!")
            self._PatientName, self._PatientID = None, None
        else: 
            matchCnt, _ = self._Database.findPatient((str(self._PatientID), str(self._PatientName)))
            if matchCnt == 0:
                self._Window.label_3.setStyleSheet("background-color: red; color: white")
                self._Window.label_3.setText("Error, Patient Not Found In Database, please select register to add them!")
                self._PatientID, self._PatientName = None, None
        # Launch Pop up saying patient is invalid, and ask to create a new one, if patient was not found
        # Now I would continue to the program selector
        self.continueToProgramSelector()

    def continueToProgramSelector(self): 
        if self._PatientID is not None and self._PatientName is not None: 
            self.hide()
            self._ProgramSelector.show()


    def programChoice(self, intSelection): 
        if self._Window.lineEdit is not None: 
            self._Name, self._PtId = self._Window.lineEdit.text(), self._Window.lineEdit_2.text()
            if intSelection == 0: # If the Gait Program Was Chosen 
                self.runGaitProgram()
            elif intSelection == 1: 
                self.runKyphosisProgram()
                
    

    def runGaitProgram(self): 
        self.hide()
        self._GaitControlPanel.setInfoNRun(self._PatientID, self._PatientName, self._Database)
        self._GaitControlPanel.show()


    def runKyphosisProgram(self): 
        self._KyphosisPanel.setPtInfoNStart(self._PatientID, self._PatientName, self._Database)
        self._KyphosisPanel.show()
        



class programSelectorUI(QDialog): 
    
    programSelectionChoice = pyqtSignal(int)
    
    def __init__(self): 
        super(programSelectorUI, self).__init__()
        self._Window = programSelection.Ui_Dialog()
        self._Window.setupUi(self)

        self.connectButtons()

    def connectButtons(self): 
        self._Window.pushButton.clicked.connect(self.gaitProgram)
        self._Window.pushButton_2.clicked.connect(self.kyphosisProgram)
     
        

    def gaitProgram(self): 
        self.hide()
        self.programSelectionChoice.emit(0)
        self.close()
    
    def kyphosisProgram(self): 
        self.hide()
        self.programSelectionChoice.emit(1)
        self.close()
        

 
    



        


if __name__ == "__main__":
    # Set all pyqt5 windows to retain their scaling
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    main = mainWindow()
    main.show()
    app.exec_()






