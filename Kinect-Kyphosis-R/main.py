# Pykinect Libraries
from typing import Tuple
from Resources.pykinect2 import PyKinectV2
from Resources.pykinect2.PyKinectV2 import * 
from Resources.pykinect2 import PyKinectRuntime


# Libraries
import os, traceback
import time
import cv2 
import numpy as np 
from numpy import average 

# My Resource Files 
from Resources.Logging import LOGGING 
from Resources.kyphosisEditor import KyphosisImg 
from Resources.mousePts import MOUSE_PTS

_ColorPallete = [(255,0,0), (0,255,0), (0,0,255)]

# First Lets Take Care of Camera Params 
class CamParam:
    def __init__(self): 
        self.focal_X, self.focal_Y = None, None 
        self.principal_X, self.principal_Y = None, None 
    
    def __areIntrinsicsValid(self, intrinsics_Matrix): 
        for value in intrinsics_Matrix: 
            if value == 0 or (value is None): 
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
        self.frameToDisplay, self.frameSave, self.frame, self.frameData = None, None, None, None 
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
            self.frameSave = self.frameToDisplay 
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
            self._PauseFrame = self.frameSave
        

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
        self.__openCVKeyPressEvents()


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
            cv2.imwrite(fileName, f"{self.frameToDisplay}.png")
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
        
        depthVal = self.spinalLandmarks[ptIndex].getAvgDistance()
        pointX, pointY = self.spinalLandmarks[ptIndex].getXY()
        distanceX = ((pointX - self._CAM_SETS.principal_x) * depthVal)/self._CAM_SETS.focal_x
        distanceY = ((pointY - self._CAM_SETS.principal_y) * depthVal)/self._CAM_SETS.focal_y 
        
        return float(distanceX),float(distanceY), float(depthVal) # Will return as mm distances
    
    # Convert every x,y to distance in mm
    def convt_XY_Pts_To_Distance(self): 
        for elements in self.spinalLandmarks: 
            if elements.getAvgDistance() == None: 
                self._ProgramLog.output(3, "Error Average Distances Must Be Calculated First!")
                exit(-1)
        
        # Set all the real distance values of each x,y coordinate
        for i in range(len(self.spinalLandmarks)): 
            distanceX, distanceY, distanceZ = self._convtXYToDistance(i)
            self.spinalLandmarks[i].set_Real_Distances(distanceX, distanceY)


    # Obtain the distance between two points of the spine
    def distanceBetweenPoints(self, index1, index2) -> float:
        point1x,point1y = self.spinalLandmarks[index1].getRealDistances()
        point2x,point2y = self.spinalLandmarks[index2].getRealDistances()

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
        c7x, c7y = self.spinalLandmarks[0].getXY()
        t12x,t12y = self.spinalLandmarks[1].getXY()

        c7z = self.spinalLandmarks[0].getAvgDistance()
        largestDiff, largestDiffY = 0,0

        # Get most recent frame data
        # Create a frame reader object
        #frameData=self._KinectDevice._depth_frame_data
        for i in range(c7y+1, t12y-1): 
            depth = self.calcDepth(self.frameData, c7x, i)
            self._PatientLog.output(2, f"X,Y Coordinate: {c7x, i} Depth: {depth}")
            depthDiff = c7z-depth
            if depthDiff > largestDiff: 
                largestDiff = depthDiff
                largestDiffY = i
       
        self._PatientLog.output(2, f"Largest Depth Point Difference {largestDiffY}")
        
        if largestDiff == 0: 
            self._ProgramLog.output(3,"Error, Kyphosis Index Could Not Be Calculated!")
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
        if not self._AllowCalculations or not self._AllowAnalysis:
            return 

        # Disallow any repressing of calculate button at this time 
        self._AllowCalculations, self._AllowAnalysis = False, False
        # Convert To Real Space
        self.convt_XY_Pts_To_Distance()
        # Calculate Kyphosis Index 
        self.kyphosisIndexValue = self.getKyphosisIndex()
        # Append the Value to the kyphosis index array, to average later 
        self.kyphosisIndexArr.append(self.kyphosisIndexValue)
        # Increase the Program Run Times 
        self._ProgramRunTimes += 1 

        # Unpause the Program
        self._Pause = False


    def messageDisplay(self, img, text) -> np.ndarray: 
         return self._OpenCVDepthHandler.displayAMessageToCV(img, text, (0,0), (500, 50), (25,25))
         

    def handleImgDisplay(self): 
        
        if self.frameToDisplay is None: 
            return 
        
        if not self._Pause:
            for index, spinePts in enumerate(self.spinalLandmarksArr): 
                self.frameToDisplay = self._OpenCVDepthHandler.drawPoints(spinePts.getXY(), color=_ColorPallete[index%len(_ColorPallete)])
            self.frameToDisplay = self._OpenCVDepthHandler.drawCoordinates("Coordinates: ")
            self._OpenCVDepthHandler.displayFrame(self.frameToDisplay)
            return 
        
        elif self._AllowAnalysis and not self._AllowCalculations: 
            self._PauseFrame = self.messageDisplay(self._PauseFrame, "Press \"b\" to analyze Thoracic Kyphosis")
        
        elif self._AllowAnalysis and self._AllowCalculations:
            self._PauseFrame = self.messageDisplay(self._PauseFrame, "\"spacebar\" to continue, or Press \"esc\" to RESET all points AND continue")
        
        self._OpenCVDepthHandler.displayFrame(self._PauseFrame)


    def runtime(self):
        
        while not self._Is_Done:

            # Handle User Input 
            self.handleOpenCVEvents()

            # Capture Depth Frames if program is not paused
            if not self._Pause:   
                self.getNewFrames()

            # Now Gather Intrinsics if they weren't already 
            if not self._IntrinsicsGathered: 
                self.gatherIntrinsics()
            elif self._AllowAnalysis and self._AllowCalculations: 
                self.captureDepthData()
                self.doCalculations()

            # Now Display The Image 
            self.handleImgDisplay()


            
                


if __name__ == "__main__":
    kyphosisApp = Kyphosis()
    kyphosisApp.runtime()