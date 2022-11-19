   
import os, cv2, time, sys

# PyQt5 
from PyQt5 import QtGui
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog


# UI Imports
from Resources.UIResources.UI import controlCenterGait, gaitSpdGeneral, gaitSpdAverageUI, trackbar, errorLog 
# Gait Runtime Program
from Runtime.programRuntimes.gaitRuntime import GaitAnalyzer


# Directory Path 
_ProgramPath = os.path.dirname(os.getcwd())

class controlPanelGait(QDialog):
    
    trigger_Program_restart = pyqtSignal(bool)
    trigger_patient_switch = pyqtSignal(bool)
    def __init__(self):
        super(controlPanelGait, self).__init__()
        self._Window = controlCenterGait.Ui_Dialog()
        self._Window.setupUi(self)
        #self._Window = loadUi(os.path.join(_UIPath, "controlCenter.ui"), self)

        # Person Identifier 
        self._Name, self._PtId = None, None 
        # Database/Web Req reference so we can logout when program is done
        self._DatabaseRef = None

        # GaitSpd UI Instance
        self.uiShowGaitSpd, self.avgGaitSpdUI = None, None
        # Gait Program Instance
        self.gaitProgram, self._GaitProgramThread = GaitAnalyzer(), None 
        # GAIT Reporting Windows 
        self.uiShowGaitSpd = gaitSpdUI()
        self.avgGaitSpdUI = avgSpdUI()
       
        # Tracbar adjustments window 
        self.trackbarWindow = trackBarUI() 
        
        # Flags
        self._ValidActionCommand = False

        # Button Connections 
        self.connectButtons()
        self._Window.pushButton_2.setDisabled(True) # Disable the Start Button Until Start Distance Captured
        # Thread Setups
        self.setupThreads()

        self.handleEmits()
        


    ##################################################
    #              GUI Setup Functions               #      
    ##################################################  
    def connectButtons(self):
        self._Window.pushButton.clicked.connect(self.signalGetStartDistance)
        self._Window.pushButton_2.clicked.connect(self.signalStartProgram)
        self._Window.pushButton_3.clicked.connect(self.signalFinishProgram)
        self._Window.pushButton_4.clicked.connect(self.signalCaptureImg)

        # Connect Trackbar 
        self._Window.toolButton.clicked.connect(self.showTrackbar)
        # Disable The Start and Get Start Distance Button On Startup, but allow get start button if an init image was given (handled in the signals)
        self._Window.pushButton.setDisabled(True)
        self._Window.pushButton_2.setDisabled(True)

    def handleEmits(self): 
        self.gaitProgram.signalShowControlWindow.connect(self.show)
        self.gaitProgram.signalAllowStartDistanceCapture.connect(self.signalallowStartdistanceBut)
        self.gaitProgram.messages.connect(self.updateLabel)
        self.gaitProgram.exitSignal.connect(self.signalExit)
        self.gaitProgram.programCanContinue.connect(self.continueGait)
        self.gaitProgram.reportProgDone.connect(self.programFinished)
        # General Gait Speed Display UI Signals
        self.uiShowGaitSpd.signalSavenQuitPressed.connect(self.signalFinishProgram) # Change this to properly exit and quit program
        self.uiShowGaitSpd.signalContinuePressed.connect(self.continuingProg)
        # Handle Ending Program Once the Avg Box Pops Up 
        self.avgGaitSpdUI.endProgram.connect(self.signalExit)
        
        # Handle Trackbar Events 
        self.trackbarWindow.sliderValueUpdate.connect(self.gaitProgram.updateCVFiltering)
        # Handle Logout without quitting
        self.avgGaitSpdUI.logout_sig.connect(self.signalLogoutOnly)
        # Handle Switching Patient Without Logout and exit
        self.avgGaitSpdUI.switch_patient.connect(self.signalPatientSwitch)
        
        

        # Handle Showing Graph At End if requested
        self.avgGaitSpdUI.signalShowAllGraphPressed.connect(self.showAllGraphs)
        self.avgGaitSpdUI.signalShowAvgGraphPressed.connect(self.showAvgGraph)

    def setupThreads(self):
        self._GaitProgramThread = QThread()
        self.gaitProgram.moveToThread(self._GaitProgramThread)
        self._GaitProgramThread.start()
        
        

    # Run the Program and Save Patient Information
    def setInfoNRun(self,id, name, database = None): 
        # Run the Program ONce the Fields are Set
        self.gaitProgram.setPatientInfo((id, name))
        self._DatabaseRef = database
        self.gaitProgram.setDatabaseInstance(self._DatabaseRef)
        self.gaitProgram.runtime()
        


    ##################################################
    #            Program Status Updates              #      
    ##################################################  
    # When the user presses continue on the gait spd general ui -> meant to be used for multiple runs on the same patient
    def continuingProg(self, boolVal): 
        if boolVal: 
            self._Window.pushButton.setDisabled(False)
            self.gaitProgram.reset(False)
            
 
    def continueGait(self, boolVal): 
        if boolVal: 
            # We Want to Report The Gait Speed Here In a new window 
            self.showGaitSpd()
    
    def showGaitSpd(self): 
        self.uiShowGaitSpd.setSpd(self.gaitProgram.getCurrGaitSpd())
        self.uiShowGaitSpd.gaitProRef = self.gaitProgram
        self.uiShowGaitSpd.show()
        
        

    def updateLabel(self, text):
        self._Window.label.setText(text)


    ##################################################
    #       Program Signal Handling Functions        # 
    ##################################################
    def showTrackbar(self): 
        self.trackbarWindow.show()
        
    def signalallowStartdistanceBut(self, boolVal):
        if boolVal: self._Window.pushButton.setDisabled(False)
        else: self._Window.pushButton.setDisabled(True)
            

    def signalGetStartDistance(self): 
        if self.gaitProgram._InitFrame is not None: 
            self.gaitProgram._AllowStartDistanceInit = True 
            #self._Window.pushButton.setDisabled(True)
            self._Window.pushButton_2.setDisabled(False)

 
    def signalStartProgram(self): 
        
        if self.gaitProgram._startDistanceCaptured:
                # Enable the Button
                self._Window.pushButton_2.setDisabled(False)
                self._Window.pushButton.setDisabled(True)
                if self.gaitProgram._PAUSE is False:
                    # Output Current Iteration to the Data File, just for organization purposes
                    '''
                    self.gaitProgram._DataSave.output(3,"\n\n---------------------------------------------------------------------------------")
                    self.gaitProgram._DataSave.output(2, f"Program Iteration: {len(self.gaitProgram.gait_Speed_Arr) + 1}")
                    self.gaitProgram._DataSave.output(3,"---------------------------------------------------------------------------------\n")
                    '''
                    # Actual Program Calls
                    self.gaitProgram.aRunTimeComplete = False  
                    self._Window.label.setText("Started, Viewfinder Will Freeze When Done")
                    self.gaitProgram._Timer.starTtimer()
                    self.gaitProgram._AllowDataCollection = True
                    self._Window.pushButton_2.setDisabled(True)
        



    def signalCaptureImg(self): 
        if self.gaitProgram._InitFrame is None: 
            self.gaitProgram.handleInitImg()
        elif not self.gaitProgram._PictureTaken: 
            self.checkForPicDirectory()
            picName =  os.path.join(_ProgramPath,"Pictures") 
            picName = os.path.join(picName, str(time.strftime("%Y%m%d-%H%M%S")) + ".png")
            self.gaitProgram._OpenCVDepthHandler.saveImage(picName, self.gaitProgram.displayFrame)
            self.gaitProgram._PictureTaken = True
            cv2.namedWindow(self.gaitProgram._PictureWindowName)
            cv2.imshow(self.gaitProgram._PictureWindowName, self.gaitProgram.displayFrame)
        else:
            cv2.destroyWindow(self.gaitProgram._PictureWindowName)
            self.gaitProgram._PictureTaken = False 


    def showAvgGraph(self, booleanVal): 
        self.gaitProgram.displayAvgGraph()
    
    def showAllGraphs(self, booleanVal): 
        if booleanVal: 
            self.gaitProgram.displayGraph(id=-1)
    
    
    def signalFinishProgram(self): 
        self.gaitProgram._IsDone = True 

    def signalLogoutOnly(self, booleanVAl=True):
        if booleanVAl:
            self._ValidActionCommand = True
            self.close()
            if(len(sys.argv) > 1 and sys.argv[1] == "--DEBUG"):
                print("Logout button presed", flush=True)
            # Set the param to True, because we want to erase all the data of the previous patient and reset the whole tool
            self.gaitProgram.reset(True)
            self._DatabaseRef.logout()
            self.trigger_Program_restart.emit(True)
    
    def signalPatientSwitch(self, booleanVal=True): 
        if booleanVal: 
            self._ValidActionCommand = True
            self.close()
            # Set the param to True, because we want to erase all the data of the previous patient and reset the whole tool
            self.gaitProgram.reset(True)
            if(len(sys.argv) > 1 and sys.argv[1] == "--DEBUG"):
                print("Patient Switching Pressed", flush=True)
            self.trigger_patient_switch.emit(True)

    def signalExit(self, booleanVal=True): 
        if booleanVal:
            self._GaitProgramThread.quit()
            self.gaitProgram._OpenCVDepthHandler.closeAllWindows()
            self._GaitProgramThread.wait(20)
            self._DatabaseRef.logout()
            exit(0)
    

    def programFinished(self, avgGait): 
        self.gaitProgram._OpenCVDepthHandler.closeAllWindows()
        # Do this to reset the trackbar slider once we are done with an iteration
        self.trackbarWindow.resetSlider()
        self.avgGaitSpdUI.setAvgSpd(avgGait)
        self.avgGaitSpdUI.show()
        
       
        
            
       
       

    
    ##################################################
    #                Helper Functions                #      
    ##################################################  
    def checkForPicDirectory(self): 
        picturePath = os.path.join(_ProgramPath, "Pictures")
        if not os.path.exists(picturePath):
            os.mkdir(picturePath) 

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        self._ValidActionCommand = False
        return super().showEvent(a0)
    
    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if not self._ValidActionCommand:
            self._DatabaseRef.logout()
            exit(0)
        
        
        
   
       

        

        
# Class to Handle Displaying General Gait Speed After Each Program Run 
class gaitSpdUI(QDialog):
    signalSavenQuitPressed = pyqtSignal(bool)
    signalContinuePressed = pyqtSignal(bool)
   
    def __init__(self):
        # Setup the window 
        super(gaitSpdUI, self).__init__()
        self._Window = gaitSpdGeneral.Ui_Dialog()
        self._Window.setupUi(self)

        # Get a Reference to the gaitprogram        
        self.gaitProRef = GaitAnalyzer()
        self.saveNquitPressed = False 
        self.buttonSetup()


    def buttonSetup(self): 
        self._Window.pushButton_2.clicked.connect(self.showGraph)
        self._Window.pushButton_4.clicked.connect(self.continuePressed)
        self._Window.pushButton_3.clicked.connect(self.saveNQuit)

    def saveNQuit(self): 
        self.saveNquitPressed = True 
        self.signalSavenQuitPressed.emit(True)
        self.hide()
    
    def showGraph(self): 
       self.gaitProRef.displayGraph()
    
    def setSpd(self, gaitSpd): 
        self._Window.label_2.setText(str(gaitSpd))

    def continuePressed(self):
        self.close()
        self.signalContinuePressed.emit(True)
    
    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.saveNquitPressed:
            self.signalSavenQuitPressed.emit(True)
        else: 
            self.signalContinuePressed.emit(True)
        self.close()



# End of Program Display, shows the calculated average of the gait speed
class avgSpdUI(QDialog):
    endProgram = pyqtSignal(bool)
    logout_sig = pyqtSignal(bool)
    switch_patient = pyqtSignal(bool)
    
    # Signals to be recieved on program's final window
    signalShowAvgGraphPressed = pyqtSignal(bool)
    signalShowAllGraphPressed = pyqtSignal(bool)
    def __init__(self): 
        super(avgSpdUI, self).__init__()
        self._Window = gaitSpdAverageUI.Ui_Dialog()
        self._Window.setupUi(self)

        self._Window.pushButton_2.clicked.connect(self.closeAvgBox)
        self._Window.pushButton_3.clicked.connect(self.showAvgGraph)
        self._Window.pushButton_4.clicked.connect(self.showAllGraphs)
        self._Window.commandLinkButton.clicked.connect(self.sendLogout)
        self._Window.commandLinkButton_2.clicked.connect(self.sendPatientSwitch)
    
    def showAllGraphs(self): 
        self.signalShowAllGraphPressed.emit(True)
    
    def showAvgGraph(self): 
        self.signalShowAvgGraphPressed.emit(True)

    def sendLogout(self): 
        self.hide()
        self.logout_sig.emit(True)
    
    def sendPatientSwitch(self): 
        self.hide()
        if(len(sys.argv) > 1 and sys.argv[1] == "--DEBUG"): 
            print("Switch Patient Button Pressed", flush=True)
        self.switch_patient.emit(True)
    
    def closeAvgBox(self): 
        self.close()
        self.endProgram.emit(True)

    # We also need this function to disable the graph buttons if there was no data
    def setAvgSpd(self, avgSpd):    
        # Need to set whether the buttons are active based on whether the avg speed is greater than 0 or not
        if(avgSpd <= 0):
            self._Window.label_2.setText(f"No Data")
            self._Window.pushButton_3.setDisabled(True)
            self._Window.pushButton_4.setDisabled(True)
        else: 
            # We have to re-enable buttons here, due to the ability of the program to run 
            # multiple times on different patients
            self._Window.label_2.setText(f"{avgSpd} m/s")
            self._Window.pushButton_3.setDisabled(False)
            self._Window.pushButton_4.setDisabled(False)
        
        #if(avgSpd > 0):
        #    self._Window.label_2.setText(f"{avgSpd} m/s")
        #else: 
        #    self._Window.label_2.setText("No Data")



class trackBarUI(QDialog): 
    
    sliderValueUpdate = pyqtSignal(int)
    
    
    def __init__(self): 
        super(trackBarUI, self).__init__()
        self._Window = trackbar.Ui_Dialog()
        self._Window.setupUi(self)
        self._ErrorOut = errorWindow()
        self.originalVal = 23
        self.prevSliderVal = 23 
        self.connectItems()
        
    
    def connectItems(self): 
        self._Window.horizontalSlider.valueChanged.connect(self.updateSensitivity)
        self._Window.pushButton.clicked.connect(self.resetSlider)

    
    def resetSlider(self): 
        self._Window.horizontalSlider.setSliderPosition(self.originalVal)
        self.sliderValueUpdate.emit(self.originalVal)
        
    
    def checkValidValueandFind(self, sliderValue : int) -> int:
        """ Verifies the Slider Values and Ensures they are a valid kernel size and returns the new position of the trackbar"""
        if(sliderValue == self.prevSliderVal and sliderValue % 2 == 1) : return sliderValue 
        elif(sliderValue % 2  == 1): 
            offset, kernelValue = abs(self.prevSliderVal - sliderValue), sliderValue, 
            # We need to calculate the offset since increased sensitivity indicates decrease kernel size
            if(sliderValue < self.prevSliderVal):  kernelValue = sliderValue + offset 
            else: kernelValue = sliderValue - offset 
            self.prevSliderVal = kernelValue
            # Since the trackbar has values from 15-45 increasing the number (moving the trackbar toward the right) would actually mean decreasing sensitivity
            # So We want to make this backend react so that it makes sense to the UI trackbar
            # So calculate the kernel value based on how close this given slider position is to the max, but put it in terms of distance from the 
            # min i.e ui trackbar is at value 43 so we would do max-43 then do that plus the min value and that will be the correct kernel sizing
            kernelValue = (self._Window.horizontalSlider.maximum() - kernelValue) + self._Window.horizontalSlider.minimum()
            return kernelValue
        
        kernelValue = sliderValue
        while(kernelValue % 2 != 1 and kernelValue <= self._Window.horizontalSlider.maximum() and kernelValue >= self._Window.horizontalSlider.minimum()): 
            if(sliderValue > self.prevSliderVal): kernelValue -= 1 
            else: kernelValue += 1 
            
        self.prevSliderVal = kernelValue
        kernelValue = (self._Window.horizontalSlider.maximum() - kernelValue) + self._Window.horizontalSlider.minimum()
        return kernelValue
            
        
                
    def updateSensitivity(self):
        sliderValue = self._Window.horizontalSlider.value()
        # self._Window.lineEdit.setText(str(sliderValue))
        # Since gausian blur only accepts kernels > 0 and height, width % 2  == 1
        # This is sending the kernel size to the gait code 
        kernelValue = self.checkValidValueandFind(sliderValue)
        self.sliderValueUpdate.emit(kernelValue)
            
            
    

class errorWindow(QDialog): 
    
    def __init__(self): 
        super(errorWindow, self).__init__()
        self._Window = errorLog.Ui_Dialog()
        self._Window.setupUi(self)

    def setMessage(self, msg):
        self._Window.label_2.setText(msg)
    
        