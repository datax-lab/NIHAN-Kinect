# Pykinect Libraries
from typing import Tuple
from Resources.pykinect2 import PyKinectV2
from Resources.pykinect2.PyKinectV2 import * 
from Resources.pykinect2 import PyKinectRuntime


# Libraries
import os, traceback
import time
import cv2 
from numpy import average 

# My Resource Files 
from Resources.Logging import LOGGING 
from Resources.kyphosisEditor import KyphosisImg 
from Resources.mousePts import MOUSE_PTS

# First Lets Take Care of Camera Params 
class CamParam:
    def __init__(self): 
        self.focal_X, self.focal_Y = None, None 
        self.principal_X, self.principal_Y = None, None 


    def setIntrinsics(self, intrinsics_Matrix): 
        self.focal_X = intrinsics_Matrix.FocalLengthX
        self.focal_Y = intrinsics_Matrix.FocalLengthY
        self.principal_X = intrinsics_Matrix.PrincipalPointX
        self.principal_Y = intrinsics_Matrix.PrincipalPointY

    def getIntrinsics(self) -> tuple: 
        return float(self.focal_X), float(self.focal_Y), float(self.principal_X), float(self.principal_Y)




class Kyphosis: 
    def __init__(self): 
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
        self.displayFrame, self.frameSave, self.frame, self.frameData = None, None, None, None 
        self._PauseFrame = None 
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

        # Setup Logging
        self._ProgramPath, self._CurrentTime, self._ProgramLogPath, self._PatientLogPath = None, None, None, None  
        self.setupLogs()
        # Actual Logging Variables 
        self._ProgramLog = LOGGING(os.path.join(self._ProgramLogPath, f"ProgramLog-{self._CurrentTime}.txt"))
        self._PatientLog = LOGGING(os.path.join(self._PatientLogPath, f"PtLog-{self._CurrentTime}.txt"))

   
    # Core Control Functions

    # Program Logging Setup 
    def setupLogs(self):
        
        self._ProgramPath = os.path.dirname(os.path.abspath(__file__))
        if __name__ != "__main__": # Then we are a resource file for another program 
            self._ProgramPath = os.path.dirname(self._ProgramPath)

        self._CurrentTime = time.strftime("%Y%m%d-%H%M%S")
        self._ProgramLogPath = os.path.join(self._ProgramPath, "ProgramLogs")
        self._PatientLogPath = os.path.join(self._ProgramPath, "PatientLogs")
        
        if not os.path.exists(self._ProgramLogPath): 
            os.mkdir(self._ProgramLogPath)
        if not os.path.exists(self._PatientLogPath): 
            os.mkdir(self._PatientLogPath)

    def gatherIntrinsics(self): 
        intrinsics = self._KinectDevice._mapper.GetDepthCameraIntrinsics()
        self._CAM_SETS.setIntrinsics(intrinsics)
        self._ProgramLog.output(2, f"Intrisics: {self._CAM_SETS.getIntrinsics()}")


    # General Function to Get New Depth Frames if there are any 
    def getNewFrames(self):
        if self._KinectDevice.has_new_depth_frame(): 
            self.displayFrame, self.frame = self._OpenCVDepthHandler.convtImg(self._KinectDevice.get_last_depth_frame())
            self.frameData = self._KinectDevice._depth_frame_data
            self.frameSave = self.displayFrame 
    
    # Handle cv window mouse events 
    def __openCVMouseEvents(self): 
        
        # No Mouse Events should be allowed if the screen is blank
        if self.displayFrame is None:
            return 

        mouseX, mouseY = None, None 

        self._OpenCVDepthHandler.handleMouseEvents()

        try: 
            if self._OpenCVDepthHandler.getLen() > 0:
                mouseX, mouseY = self._OpenCVDepthHandler.popData()
        except Exception: 
            self._ProgramLog.output(3, f"\nError Retrieving x,y, coordinates of mouse, exiting...\n")
            self._ProgramLog.output(2, traceback.format_exc())
            exit(-1)
        
        if (mouseX is not None and mouseY is not None) and len(self.spinalLandmarksArr) <= self._ReqPts: 
            # Since the spine should be relatively straight, it should be along the same X coord, so set the next 2 points to the x coord of the first point
            if len(self.spinalLandmarksArr) > 0: 
                mouseX, _ = self.spinalLandmarksArr[0].getXY()
            
            self.spinalLandmarksArr.append(MOUSE_PTS(self.id, (mouseX, mouseY)))
            self.id += 1 
            self._PatientLog.output(3, f"A Point Was Placed at X: {mouseX} Y: {mouseY}")
        
        elif len(self.spinalLandmarksArr) > self._ReqPts:
            self._ProgramLog.output(3, "Too Many Points, please press \"esc\" to remove all points and continue!")
            # Since the cvWindow event handling class automatically appends any points pressed to the array, we now have an invalid value that needs
            # to be thrown away
            _, _ = self._OpenCVDepthHandler.popData()
        
        # Once there are 3 points (C7, T12/L1, S1) allow the user to press the processing keybind to analyse kyphosis 
        if len(self.spinalLandmarksArr) == self._ReqPts: 
            self._AllowAnalysis = True 
            self._Pause = True 
        

    # Now Lets Handle the CV window Keypress Events 
    def __openCVKeyPressEvents(self): 
        
        keypress = cv2.waitKey(1) & 0xFF
        if keypress == 27: # press 'esc' to reset the program at any time
            self.reset(clearSpinalArr=True)
        elif keypress == ' ': 
            self.reset(clearSpinalArr=False)
        elif keypress == ord('b') and self._AllowAnalysis: 
            # Allow For Calculations 
            self._ProgramLog.output(3, "Beginning Analysis...")
            self._RunCalculations = True 
        elif keypress == ord('s'): 
            self._imgSave()
        elif keypress == ord('q'):
            self._Is_Done = True 
            cv2.destroyAllWindows()
            if len(self.kyphosisIndexArr) > 0: 
                self._PatientLog.output(3, f"\n\nKyphosis Indexes Calculated: {self.kyphosisIndexArr}")
                self._PatientLog.output(3, f"\nAverage Kyphosis Index: {average(self.kyphosisIndexArr)}")
        elif keypress == ord('p'):
            if not self._Pause:
                self._Pause = True
            else:
                self._Pause = False 

    # Handle the cv window events 
    def handleOpenCVEvents(self): 
        self.__openCVMouseEvents()
        self.__openCVKeyPressEvents 


    def _imgSave(self): 
        # Check if the image folder path exists
        if not os.path.exists(os.path.join(self._ProgramPath, "KyphosisImages")): 
            os.mkdir(os.path.join(self._ProgramPath, "KyphosisImages"))
            self._ProgramLog.output(2, "KyphosisImages Folder Generated\n")

        if self.saveAnImage is False:
            # Create the File Name
            fileName = f"img-{self._CurrentTime}"
            fileName = os.path.join(os.path.join(self._ProgramPath, "KyphosisImages"), fileName)
            # Save the image
            cv2.imwrite(fileName, f"{self.displayFrame}.png")
            self.saveAnImage = True 
            # Now Display It 
            cv2.namedWindow(self.saveAnImgWindowName)
            cv2.imshow(self.saveAnImgWindowName, fileName)
        
        elif self.saveAnImage is True: 
            cv2.destroyWindow(self.saveAnImgWindowName)
            self.saveAnImage = False 

    
    # Reset Function

    def reset(self, clearSpinalArr=False): 
        if clearSpinalArr: 
            self.spinalLandmarksArr = [] 

        self.id = 1 
        self._OpenCVDepthHandler.resetWindow() 
        self._RunCalculations, self._AllowCalculations, self._CalculationCompleted = False, False, False
        self._Pause = False


    # Calculation Functions 
    



    def runtime(self):
        
        while not self._Is_Done:

            # Handle User Input 
            self.handleOpenCVEvents()

            # Capture Depth Frames 
            self.getNewFrames()

            # Now Gather Intrinsics if they weren't already 
            if not self._IntrinsicsGathered: 
                self.gatherIntrinsics()
            

            if self.displayFrame is not None: 
                self._OpenCVDepthHandler.displayFrame(self.displayFrame)


if __name__ == "__main__":
    kyphosisApp = Kyphosis()
    kyphosisApp.runtime()