# Pykinect Libraries
from typing import Tuple
from Resources.pykinect2 import PyKinectV2
from Resources.pykinect2.PyKinectV2 import * 
from Resources.pykinect2 import PyKinectRuntime

# PyQt5 
from PyQt5.QtCore import QThread, pyqtSignal


# Libraries
import os, traceback
import time
import cv2 
import numpy as np 
from numpy import average 

# My Resource Files 
from Resources.Logging import LOGGING 
from Resources.CVResources.kyphosisEditor import KyphosisImg 
from Resources.mousePts import MOUSE_PTS

from Resources.webRequests import WebReq
#from Resources.data import DataHandler

_ColorPallete = [(255,0,0), (0,255,0), (0,0,255)]

# First Lets Take Care of Camera Params 
# These are parameters that are needed to get real world points in mm 
class CamParam:
    def __init__(self): 
        self.focal_X, self.focal_Y = None, None 
        self.principal_X, self.principal_Y = None, None 
    
    # Just check one to see if it is valid
    def __areIntrinsicsValid(self, intrinsics_Matrix): 
        if intrinsics_Matrix.FocalLengthX == 0:
            return False
        
        return True

    # Will check if the intrinsics are valid, since the its possible the kinect may not connect properly 
    def setIntrinsics(self, intrinsics_Matrix) -> bool: 
        if not self.__areIntrinsicsValid(intrinsics_Matrix):
            return False 

        self.focal_X = intrinsics_Matrix.FocalLengthX
        self.focal_Y = intrinsics_Matrix.FocalLengthY
        self.principal_X = intrinsics_Matrix.PrincipalPointX
        self.principal_Y = intrinsics_Matrix.PrincipalPointY
        
        return True 

    def getIntrinsics(self) -> tuple: 
        return float(self.focal_X), float(self.focal_Y), float(self.principal_X), float(self.principal_Y)
    
 
# The main class of the kyphosis program 
class Kyphosis(QThread): 
    signalControlWindowtoShow = pyqtSignal(bool)
    signalReqPtsSatisfied = pyqtSignal(bool)
    signalMessageOutput = pyqtSignal(str)

    signalKyphosisIndex = pyqtSignal(float)
    signalProgramEnding = pyqtSignal(float) # Should transmit the average kyphosis index
    
    def __init__(self):
        # Threading Setup 
        QThread.__init__(self) 
        # Kinect Setup Steps: 
        # Create the kinectDevice Object, that holds all the depth frame function
        self._KinectDevice = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
        # Get the Kinect's Camera Parameters, will be needed to calculate the distance between C7 and T12/L1 
        self._CAM_SETS = CamParam()
        # Set the Height and Width of the Frame 
        self._Height, self._Width = self._KinectDevice.depth_frame_desc.Height, self._KinectDevice.depth_frame_desc.Width
        # Class to help convert images to readable and editable formats 
        self._OpenCVDepthHandler = KyphosisImg(self._Height, self._Width, "Kinect V2 Kyphosis Analyzer")
        
        
        # Actual Program Vars: 
        # Array To Hold the Depth Measurment, and the XY position of the clicked points
        # Array To Hold All the Calculated Kyphosis Indexes 
        self.spinalLandmarksArr, self._KyphosisIndexArr = [], [] 
        self.id = 1  
        
        # Pogram Constants, other than what's required for kinect setup 
        self._ReqPts, self._ReqFrames = 3, 5 

        # Frames Used in Program 
        self.frameToDisplay, self.frameSave, self.frame, self.frameData = None, None, None, None 
        self.saveAnImage, self.saveAnImgWindowName = False, "Kinect V2 Saved Image" 

        # Program Flags 
        self._IntrinsicsGathered = False 
        self._Is_Done, self._Pause = False, False 

        self._AllowCalculations, self._RunCalculations, self._AllowAnalysis = False, False, False
        self._CalculationCompleted = False

        self._ProgramRunTimes, self._ProgramMinIterations = 0, 3 
        
        # Data Recording 
        self.kyphosisIndexArr, self.kyphosisIndexValue = [], None 
        self._AvgKyphosisIndex = 0
        #self.spinePtCntr = 0 # if becomes > 3 then notify that there should only be 3 points on the spine
        # Setup Logging
        self._ProgramPath, self._CurrentTime, self._ProgramLogPath, self._PatientLogPath = None, None, None, None  
         # Actual Logging Variables 
        self._ProgramLog, self._PatientLog = None, None
      
        # Patient Info 
        self._PatientID, self._PatientName = None, None
        self._Database = WebReq() #DataHandler()

        self.setupLogs()

    def setDatabaseInstance(self, dataBasePtr):
        self._Database = dataBasePtr
   
    # Core Control Functions
    def setPatientInfo(self, ptInfo): 
        self._PatientID, self._PatientName = ptInfo

    # Program Logging Setup 
    def setupLogs(self):
        self._ProgramPath = os.getcwd()
        #self._ProgramPath = os.path.dirname(os.path.abspath(__file__))
        '''
        if __name__ != "__main__": # Then we are a resource file for another program 
            self._ProgramPath = os.path.dirname(self._ProgramPath)
        '''
        self._CurrentTime = time.strftime("%Y%m%d-%H%M%S")
        self._ProgramLogPath = os.path.join(self._ProgramPath, "ProgramLogs")
        self._PatientLogPath = os.path.join(self._ProgramPath, "PatientLogs")
        
        if not os.path.exists(self._ProgramLogPath): 
            os.mkdir(self._ProgramLogPath)
        if not os.path.exists(self._PatientLogPath): 
            os.mkdir(self._PatientLogPath)
        
        self._ProgramLog = LOGGING(os.path.join(self._ProgramLogPath, f"ProgramLog-{self._CurrentTime}.txt"))
        self._PatientLog = LOGGING(os.path.join(self._PatientLogPath, f"PtLog-{self._CurrentTime}.txt"))

    def gatherIntrinsics(self): 
        intrinsics = self._KinectDevice._mapper.GetDepthCameraIntrinsics()
        
        if not self._CAM_SETS.setIntrinsics(intrinsics):
            self._ProgramLog.output(2,"Intrinsics Not Valid")
        else:
            self._ProgramLog.output(2, f"Intrisics: {self._CAM_SETS.getIntrinsics()}")
            self._IntrinsicsGathered = True 


    # General Function to Get New Depth Frames if there are any 
    def getNewFrames(self):
        if self._KinectDevice.has_new_depth_frame(): 
            self.frameToDisplay, self.frame = self._OpenCVDepthHandler.convtImg(self._KinectDevice.get_last_depth_frame())
            self.frameData = self._KinectDevice._depth_frame_data
            self._OpenCVDepthHandler.setDisplayFrame(self.frameToDisplay)
            self.frameSave = np.copy(self.frameToDisplay)
        else: 
            self.frame, self.frameData = None, None 
    
    # Handle cv window mouse events 
    def __openCVMouseEvents(self): 
        
        # No Mouse Events should be allowed if the screen is blank
        if self.frameToDisplay is None:
            return 

        mouseX, mouseY = None, None 

        self._OpenCVDepthHandler.handleMouseEvents()
        
 
        try: 
            if self._OpenCVDepthHandler.getLen() > 0:
                mouseX, mouseY = self._OpenCVDepthHandler.popData()
        except Exception: 
            self._ProgramLog.output(2, f"\nError Retrieving x,y, coordinates of mouse, exiting...\n")
            self._ProgramLog.output(2, traceback.format_exc())
            exit(-1)
        #self.spinePtCntr += 1

        if (mouseX is not None and mouseY is not None) and len(self.spinalLandmarksArr) < self._ReqPts: 
            # Since the spine should be relatively straight, it should be along the same X coord, so set the next 2 points to the x coord of the first point
            if len(self.spinalLandmarksArr) > 0: 
                mouseX, _ = self.spinalLandmarksArr[0].getXY()
            
            self.spinalLandmarksArr.append(MOUSE_PTS(self.id, (mouseX, mouseY)))
            self.id += 1 
            self._PatientLog.output(2, f"A Point Was Placed at X: {mouseX} Y: {mouseY}")
        
        # Once there are 3 points (C7, T12/L1, S1) allow the user to press the processing keybind to analyse kyphosis 
        if len(self.spinalLandmarksArr) == self._ReqPts: 
            self._AllowAnalysis = True 
            #self._Pause = True 
            self.signalReqPtsSatisfied.emit(self._AllowAnalysis)
            self.signalMessageOutput.emit("Press \"Analyze\" to Get Kyphosis Index")
        

    # Now Lets Handle the CV window Keypress Events 
    def __openCVKeyPressEvents(self): 
        
        keypress = cv2.waitKey(1) & 0xFF

        if keypress == 27: # press 'esc' to reset the program at any time
            self.reset(clearSpinalArr=True)
        elif keypress == ord(' '): 
            self.reset(clearSpinalArr=False)
        elif keypress == ord('b') and self._AllowAnalysis: 
            # Allow For Calculations 
            self._ProgramLog.output(2, "Beginning Analysis...")
            self._RunCalculations = True 
        elif keypress == ord('s'): 
            self._imgSave()
        elif keypress == ord('q'):
            #self.programClose()
            self._Is_Done = True
        elif keypress == ord('p'):
            if not self._Pause:
                self._Pause = True
            else:
                self._Pause = False 

    # End of Program Cleanup 
    # This is also the section where I will upload the data to the Database 
    def programClose(self): 
        
        self._Is_Done = True 

        

        if len(self.kyphosisIndexArr) > 0: 
            self._PatientLog.output(2, f"\n\nKyphosis Indexes Calculated: {self.kyphosisIndexArr}")
            self._PatientLog.output(2, f"\nAverage Kyphosis Index: {average(self.kyphosisIndexArr)}")
            
        
        self._ProgramLog.output(2, "\nProgram Run Complete, Exit Success")

        self._PatientLog.closeFile()
        self._ProgramLog.closeFile()

        if len(self.kyphosisIndexArr) > 0: 
            # Upload to DB/Web Server
            self._Database.uploadKyphosisResult((self._PatientID, self._PatientName), average(self.kyphosisIndexArr))
            # Upload Data to DB 
            #self._Database.uploadResults((self._PatientID, self._PatientName), None, None, None, None, average(self.kyphosisIndexArr))
            self.signalProgramEnding.emit(average(self.kyphosisIndexArr))
        else: 
            self.signalProgramEnding.emit(-1)
            

    # Handle the cv window events 
    def handleOpenCVEvents(self): 
        self.__openCVMouseEvents()
        # Just to Stop OpenCV from Freezing
        key = cv2.waitKey(1) & 0xFF 
        if key == ord('q') and False: 
            exit(0)
        #self.__openCVKeyPressEvents()


    def _imgSave(self): 
        # Check if the image folder path exists
        if not os.path.exists(os.path.join(self._ProgramPath, "KyphosisImages")): 
            os.mkdir(os.path.join(self._ProgramPath, "KyphosisImages"))
            self._ProgramLog.output(2, "KyphosisImages Folder Generated\n")

        self.frameSave = self.displayPoints(self.frameSave) 
    

        if self.saveAnImage is False:
            # Create the File Name
            fileName = f"img-{self._CurrentTime}.png"
            fileName = os.path.join(os.path.join(self._ProgramPath, "KyphosisImages"), fileName)
            # Save the image
            self._OpenCVDepthHandler.saveImg(fileName, self.frameSave)
            self.saveAnImage = True 
            # Now Display It 
            cv2.namedWindow(self.saveAnImgWindowName)
            cv2.imshow(self.saveAnImgWindowName, cv2.imread(fileName))
        
        elif self.saveAnImage is True: 
            cv2.destroyWindow(self.saveAnImgWindowName)
            self.saveAnImage = False 

    
    # Reset Function
    def reset(self, clearSpinalArr=False): 
        if clearSpinalArr: 
            self.spinalLandmarksArr = [] 
            self.signalMessageOutput.emit("Please Select C7, T12, L1 In ViewFinder")
        else: 
            self.signalMessageOutput.emit("Press \"Analyze\" to get Thoracic Kyphosis")

        self.id = 1 
        self._OpenCVDepthHandler.resetList() 
        self._RunCalculations, self._AllowCalculations, self._CalculationCompleted, self._AllowAnalysis = False, False, False, False
        self._Pause = False
        self.signalReqPtsSatisfied.emit(self._AllowAnalysis)



    # Calculation Functions 
    def captureDepthData(self): 
        
        framesCaptured = 0 
        while framesCaptured < self._ReqFrames: 
            self.getNewFrames()
            
            if self.frame is not None: 
                # If the Frame is not None, then I want to grab the depth points of the xyTuple of each element in the spinal array 
                # Then append the depth in mm to the correct element of the spinalArray -> each element in the spinalArray is an instance 
                # of the Mouse_Pts class 
                for spinalPoints in self.spinalLandmarksArr: 
                    x_Temp, y_Temp = spinalPoints.getXY()
                    spinalPoints.setDepth_Val(self._OpenCVDepthHandler.getDepth(self.frameData, x_Temp, y_Temp))
                
                # Increment the Frame Counter 
                framesCaptured += 1

        # Since I have obtained the distances/depth I want to get the average across these five frames, which should have a length of 5 
        for spinalPts in self.spinalLandmarksArr: 
            spinalPts.setAvgDistance()


    def _convtXYToDistance(self, ptIndex) -> tuple: 
        
        depthVal = self.spinalLandmarksArr[ptIndex].getAvgDistance()
        pointX, pointY = self.spinalLandmarksArr[ptIndex].getXY()
        distanceX = ((pointX - self._CAM_SETS.principal_X) * depthVal)/self._CAM_SETS.focal_X
        distanceY = ((pointY - self._CAM_SETS.principal_Y) * depthVal)/self._CAM_SETS.focal_Y 
        
        return float(distanceX),float(distanceY), float(depthVal) # Will return as mm distances
    
    # Convert every x,y to distance in mm
    def convt_XY_Pts_To_Distance(self): 
        for elements in self.spinalLandmarksArr: 
            if elements.getAvgDistance() == None: 
                self._ProgramLog.output(2, "Error Average Distances Must Be Calculated First!")
                exit(-1)
        
        # Set all the real distance values of each x,y coordinate
        for i in range(len(self.spinalLandmarksArr)): 
            distanceX, distanceY, distanceZ = self._convtXYToDistance(i)
            self.spinalLandmarksArr[i].set_Real_Distances(distanceX, distanceY)


    # Obtain the distance between two points of the spine
    def distanceBetweenPoints(self, index1, index2) -> float:
        point1x,point1y = self.spinalLandmarksArr[index1].getRealDistances()
        point2x,point2y = self.spinalLandmarksArr[index2].getRealDistances()

        #Since we're looking for height, we return the y-distances, should be positive values only
        distanceY =  point2y-point1y
        if distanceY < 0: 
            return float(distanceY * -1)
        else: 
            return float(distanceY)

        
    

    # Find the z value of the largest depth from C7 until t12, so we need to travel along the y-axis only
    # Since we're looking at the back as a "flat" image, we can simply
    # move down the y-axis to find the pixel with the furthest depth
    # Will return the c7x and then the y coordinate furthest away
    def getDeepest(self) -> tuple: 
        c7x, c7y = self.spinalLandmarksArr[0].getXY()
        t12x,t12y = self.spinalLandmarksArr[1].getXY()

        c7z = self.spinalLandmarksArr[0].getAvgDistance()
        largestDiff, largestDiffY = 0,0

        # Get most recent frame data
        # Create a frame reader object
        #frameData=self._KinectDevice._depth_frame_data
        for i in range(c7y+1, t12y-1): 
            depth = self._OpenCVDepthHandler.getDepth(self.frameData, c7x, i)
            self._PatientLog.output(2, f"X,Y Coordinate: {c7x, i} Depth: {depth}")
            depthDiff = c7z-depth
            if depthDiff > largestDiff: 
                largestDiff = depthDiff
                largestDiffY = i
       
        self._PatientLog.output(2, f"Largest Depth Point Difference {largestDiffY}")
        
        if largestDiff == 0: 
            self._ProgramLog.output(2,"Error, Kyphosis Index Could Not Be Calculated!")
            exit(-1)

        return  c7x,largestDiffY,largestDiff

    # Calculate the kyphosis index, normal range from 25-45
    def getKyphosisIndex(self) -> float: 
        # Get Distance between C7 and T12/L1
        lenC7toT12_L1 = self.distanceBetweenPoints(0,1)
        # Get x,y coordinate of deepest point between C7 and T12/L1
        # Get the largest depth/height 
        x,y,z = self.getDeepest()

        return float((z/lenC7toT12_L1) * 100)

    

    def doCalculations(self): 
        if not self._AllowAnalysis or not self._RunCalculations:
            return 

        # Disallow any repressing of calculate button at this time 
        self._AllowAnalysis, self._RunCalculations = False, False
        # Convert To Real Space
        self.convt_XY_Pts_To_Distance()
        # Calculate Kyphosis Index 
        self.kyphosisIndexValue = self.getKyphosisIndex()
        # Append the Value to the kyphosis index array, to average later 
        self.kyphosisIndexArr.append(self.kyphosisIndexValue)
        # Also emit the kyphosis index
        self.signalKyphosisIndex.emit(self.kyphosisIndexValue)
        # Increase the Program Run Times 
        self._ProgramRunTimes += 1 

        # Unpause the Program
        self._Pause, self._CalculationCompleted = False, True
        self._PatientLog.output(2, f"\nProgram Run: {self._ProgramRunTimes}\nKyphosis Index Was: {self.kyphosisIndexValue}\n")


    def messageDisplay(self, img, text) -> np.ndarray: 
         return self._OpenCVDepthHandler.displayAMessageToCV(img, text, (0,0), (self._Width, 50), (0,25))
         
    def displayPoints(self, img): 
        for index, spinePts in enumerate(self.spinalLandmarksArr): 
                img = self._OpenCVDepthHandler.drawPoints(img, spinePts.getXY(), color=_ColorPallete[index%len(_ColorPallete)])
        
        return img


    def handleImgDisplay(self): 
        
        if self.frameToDisplay is None: 
            return 
        
        #imgTemp = self.displayPoints(self.frameToDisplay)
        self.frameToDisplay = self.displayPoints(self.frameToDisplay)

        
        if not self._Pause:
            self.frameToDisplay = self._OpenCVDepthHandler.drawCoordinates(self.frameToDisplay,"Coordinates: ")
        
        elif self._AllowAnalysis and not self._CalculationCompleted and self._Pause: 
            #self.frameToDisplay = self.messageDisplay(self.frameToDisplay, "Press \"b\" to analyze Thoracic Kyphosis")
            self.signalMessageOutput.emit("Press \"Analyze\" to get Thoracic Kyphosis")
        #elif self._AllowAnalysis and self._CalculationCompleted and self._Pause:
         #   self.frameToDisplay = self.messageDisplay(self.frameToDisplay, "Press \"spacebar\" to continue, or \"esc\" to CLEAR and continue")
        if self.frameToDisplay is None: 
            print("Empty")
            exit(-1)
       
        self._OpenCVDepthHandler.displayFrame(self.frameToDisplay)

   
    def runtime(self):
        messsageSent = False 

        
        while not self._Is_Done:

            # Handle User Input 
            self.handleOpenCVEvents()

            # Capture Depth Frames if program is not paused  
            if not self._Pause:
                self.getNewFrames()

            # Now Gather Intrinsics if they weren't already 
            if not self._IntrinsicsGathered: 
                self.gatherIntrinsics()
            elif self._AllowAnalysis and self._RunCalculations: 
                self.captureDepthData()
                self.doCalculations()
                self._ProgramLog.output(2, "Calculation Finished!")

            # Now Display The Image 
            self.handleImgDisplay()

            if messsageSent is False: 
                messsageSent = True
                self.signalControlWindowtoShow.emit(True)

        self.programClose()
        

            

    


            
                


if __name__ == "__main__":
    kyphosisApp = Kyphosis()
    kyphosisApp.runtime()