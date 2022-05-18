from Resources.UIResources.UI import loginScreen, twoFactorUI
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import QDialog, QApplication
from PyQt5.QtCore import pyqtSignal

import sys

from Resources.webRequests import WebReq
from kinectAnalyzer import mainWindow



# Debug for now 
_DebugMode = False 
if len(sys.argv) > 1: 
    print(sys.argv)
    if sys.argv[1] == "--DEBUG": 
        _DebugMode = True 
        print("Debug Mode Active")


class userLogin(QDialog):
    def __init__(self):
        # Standard UI Setup
        super(userLogin, self).__init__()
        self._Window = loginScreen.Ui_Dialog()
        self._Window.setupUi(self)

        # Temporarily Hold the User Name and Password
        self._Email, self._Passwd = None, None
        # Web Requests 
        self._WebInteraction = WebReq()

        # Two Factor Window
        self._twoFactorWindow = twoFactorIn()

        # Timer to clear input
        self._LoginTimer, self._ReqTimer = QtCore.QTimer(self),QtCore.QTimer(self)
        self.__LoginTimeOut, self.__ReqRefreshInterval = 30, 180000 # This is in seconds
        self._LoginTimeOutInterval = self.__LoginTimeOut * 1000

        # Instantiate the mainUI 
        self._mainUI = mainWindow()
        
        # Functions to start upon instantiation
        self.connectButtons()
        self.connectSignals()
        
    
    def connectSignals(self):
        self._WebInteraction.webReqMessage.connect(self.outputMessage)
        self._twoFactorWindow.twoFactorCode.connect(self.verifyCode)
     
     
    def connectButtons(self):
        self._Window.pushButton.clicked.connect(self.runLogin)
        self._Window.lineEdit.textChanged.connect(self.connectClearLoginTimer)


    def connectRefreshTimer(self):
        self._ReqTimer.timeout.connect(self._WebInteraction.linkStart)
        self._ReqTimer.start(self.__ReqRefreshInterval)
        
    def connectClearLoginTimer(self):
        if not self._LoginTimer.isActive():
            if _DebugMode:
                print("Lined Changed")
            self._LoginTimer.timeout.connect(self.clearInputOnTimeOut)
            self._LoginTimer.start(self._LoginTimeOutInterval)


    def clearInputOnTimeOut(self):
        self._Window.lineEdit.clear()
        self._Window.lineEdit_2.clear()
        self._LoginTimer.stop()


    def runLogin(self):
        if _DebugMode:
            print("Login Button Pressed!")
        self._Email, self._Passwd = self._Window.lineEdit.text(), self._Window.lineEdit_2.text()
        # Call WebRequests File Here, and check if login success
        # if it was succes then start the refresh timer
        # else output login error and restart the loginTimer to clear input
        self._WebInteraction.setUserPass(self._Email, self._Passwd)
        if _DebugMode: 
            print(f"User: {self._Email}, Passd: {self._Passwd}")
            self.callMainUI()
        elif self._WebInteraction.linkStart() > -1: 
           self._twoFactorWindow.setEmail(self._Email)
           self._twoFactorWindow.show()
        else:
            # The call to the linkstart will emit a message to the screen if there was an error w
            # logging in 
            # If there was no error, then this should never be executed, since the call to
            # open the main window will happen
            self.connectClearLoginTimer()
            
    def verifyCode(self, code): 
        if code != "-1" and self._WebInteraction.linkStart(token=code) > -1: 
            self.connectRefreshTimer()
            self.callMainUI()
        else: 
            self.connectClearLoginTimer()
            
    
    def outputMessage(self, message: tuple): 
        if message[0] == -1: 
            self._Window.label.setStyleSheet("background-color: red; color: white; font-weight: bold")
        
        self._Window.label.setText(message[1])
      
        
    def callMainUI(self): 
        self._mainUI.setWebDBConnection(self._WebInteraction)
        self.hide()
        self._mainUI.show()
        

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
      
        self._WebInteraction.logout()
     
        print("logged out")
        
        return super().closeEvent(a0)



class twoFactorIn(QDialog): 
    twoFactorCode = pyqtSignal(str)
    
    def __init__(self):
        super(twoFactorIn, self).__init__() 
        self._Window = twoFactorUI.Ui_Dialog()
        self._Window.setupUi(self)
        # Add For Look
        self._email = None 
        
        self.connectButtons()
      
    def connectButtons(self): 
        self._Window.pushButton.clicked.connect(self.sendCode)
    
    def setEmail(self, email): 
        self._Window.label.setText(f"Enter The Code Sent To: {email}")
        
    def sendCode(self): 
        tempCode = self._Window.lineEdit.text()
        self._Window.lineEdit.setText('')
        self.twoFactorCode.emit(tempCode)
        self.close()
        
    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.twoFactorCode.emit("-1")
        return super().closeEvent(a0)            
        



if __name__ == "__main__":

    # Set all pyqt5 windows to retain their scaling
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    App=QApplication(sys.argv)
    main=userLogin()
    main.show()
    App.exec_()
    
    main._WebInteraction.logout()

