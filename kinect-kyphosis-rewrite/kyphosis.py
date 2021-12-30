# Pykinect Imports 
from numpy.lib.function_base import average
from Resources.mousePts import Mouse_Pts
from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime 


# General Imports 
import os 
import time 
import traceback

# Specialized Libraries 
import numpy 
import cv2 

# Resource Files 
from Resources import kyphosisImg as IMG 
from Resources import Logging as LOG 

colorPallete = [(255,0,0), (0,255,0), (0,0,255)] 

# Class to Hold the Kinect Parameters needed for Future Calculations 
class CamParam: 
    def __init__(self): 
        self.focal_x = float() 
        self.focal_y = float()
        self.principal_x = float()
        self.principal_y = float()
        self.sets = 0
        

    

    def setIntrinsics(self, intrinSics_Matrix): 
        self.focal_x = intrinSics_Matrix.FocalLengthX
        self.focal_y = intrinSics_Matrix.FocalLengthY
        self.principal_x = intrinSics_Matrix.PrincipalPointX
        self.principal_y = intrinSics_Matrix.PrincipalPointY
   

    def getIntrinsics(self) -> tuple: 
        return self.focal_x, self.focal_y, self.principal_x, self.principal_y



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
        self._OpenCVDepthHandler = IMG.KyphosisImgEditor(self._Height, self._Width, "Kinect V2 Kyphosis Analyzer")
        
        # Actual Program Vars: 
        # Array To Hold the Depth Measurment, and the XY position of the clicked points
        # Array To Hold All the Calculated Kyphosis Indexes 
        self.spinalLandmarksArr, self._KpyhosisIndexArr = [], [] 
        self.id = 1  
        
        # Pogram Constants, other than what's required for kinect setup 
        self._ReqPts, self._ReqFrames = 3, 5 

        # Frames Used in Program 
        self.displayFrame, self.frameSave, self.frame, self.frameData = None, None, None, None 
        self.saveAnImage, self.saveAnImgWindowName = False, "Kinect V2 Saved Image" 

        # Program Flags 
        self._Is_Done, self._Pause = False, False 
        self._AllowCalculations, self._DoCalculations = False, False  
        self._CalculationCompleted = False
        self._ProgramRunTimes = 0 


        # Data Recording 
        self.kyphosisIndexArr, self.kyphosisIndexValue = [], None 



        # Setup Logging
        self._ProgramPath, self._CurrentTime, self._ProgramLogPath, self._PatientLogPath = None, None, None, None  
        self.setupLogs()
        # Actual Logging Variables 
        self._ProgramLog = LOG.LOGGING(os.path.join(self._ProgramLogPath, f"ProgramLog-{self._CurrentTime}.txt"))
        self._PatientLog = LOG.LOGGING(os.path.join(self._PatientLogPath, f"PtLog-{self._CurrentTime}.txt"))
        

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

    # Core Functions
    # Save the camera's intrinsics, so that we can use it to calculate where an xy point is in space 
    def gatherIntrinsics(self): 
        
        intrinsics = self._KinectDevice._mapper.GetDepthCameraIntrinsics()
        self._CAM_SETS.setIntrinsics(intrinsics)

    # Handle New Found Depth Frames 
    def handleNewFrame(self): 
        if self._KinectDevice.has_new_depth_frame(): 
            self.displayFrame, self.frame = self._OpenCVDepthHandler.convtImg(self._KinectDevice.get_last_depth_frame())
            self.frameData = self._KinectDevice._depth_frame_data 
        else: 
            self.frame, self.frameData = None, None # The Display Frame is unaffected here, as there should always 
                                                    # be something displayed to the screen


    def openCVEvents(self): 
        mouseX, mouseY = None, None 
        self._OpenCVDepthHandler.handleMousePress()

        try: 
            if len(self._OpenCVDepthHandler.ptsArr) > 0: 
                mouseX, mouseY = self._OpenCVDepthHandler.ptsArr.pop().getXY()
        except Exception as err: 
            self._ProgramLog.output(3, f"\nError Retrieving x,y, coordinates of mouse, exiting...\n")
            self._ProgramLog.output(2, traceback.format_exc())
            exit(-1)

        # Append the XY Points to the Spinal Landmarks Array       
        if (mouseX is not None and mouseY is not None) and len(self.spinalLandmarksArr) <= self._ReqPts: 
            # We can assume that the x point should remain consistent as the spinal landmarks should be along the same x axis 
            if len(self.spinalLandmarksArr) > 0: 
                mouseX, _ = self.spinalLandmarksArr[0].getXY()
            self.spinalLandmarksArr.append(Mouse_Pts(mouseX, mouseY, self.id))
            self.id += 1 
            self._PatientLog.output(3, f"A Point Was Placed at X: {mouseX} Y: {mouseY}")
        elif len(self.spinalLandmarksArr) >= self._ReqPts: # Ensure that the user is not selecting more that 3 points
            self._ProgramLog.output(3, "Too Many Points, please press \"SPACEBAR\" to remove all points and continue!")


        # Allow Calculations Once There Are Three Points Marked (Which should be the C7, T12/L1, and S1)
        if len(self.spinalLandmarksArr) == self._ReqPts: 
            self._AllowCalculations = True 
        elif self._AllowCalculations is True and len(self.spinalLandmarksArr) < self._ReqFrames: 
            self._AllowCalculations = False 


        # Now Let's Handle the Normal Keypresses 
        keypress = cv2.waitKey(1) & 0xFF
        if keypress == 27: 
            self.spinalLandmarksArr = [] 
            self.id = 1 
            self._OpenCVDepthHandler.resetWindow() 
            self._DoCalculations, self._AllowCalculations = False 
        elif keypress == ord('b') and self._AllowCalculations: 
            # Allow For Calculations 
            self._ProgramLog.output(3, "Beginning Analysis...")
            self._DoCalculations = True 
        elif keypress == ord('s'): 
            self._imgSave()
        elif keypress == ord('q'):
            self._Is_Done = True 
            cv2.destroyAllWindows()
            if self.kyphosisIndexArr > 0: 
                self._PatientLog.output(3, f"\n\nKyphosis Indexes Calculated: {self.kyphosisIndexArr}")
                self._PatientLog.output(3, f"\nAverage Kyphosis Index: {average(self.kyphosisIndexArr)}")
        elif keypress == ord('p'):
            if not self._Pause:
                self._Pause = True
            else:
                self._Pause = False 

        
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



    # Moving onto the program calculations 


    # Capture the Depth Data from 5 Frames or whatever the constant is set to, and then set the average 
    def captureDepthData(self):
        if not self._DoCalculations: 
            print("Please Press \"b\" to begin analysis")
            return 
        elif not self._AllowCalculations: 
            print(f"Please select {self._ReqPts} to enable analysis option, then press \"b\"")
            return 
        # Local Variable for a Counter
        frameCount = 0 
        
        while frameCount < self._ReqFrames: 
            self.handleNewFrame()
            if self.frame is not None: 
                for spinePts in self.spinalLandmarksArr: 
                    mouseX,mouseY = spinePts.getXY()
                    spinePts.set_Distance(self._OpenCVDepthHandler.getDepth(self.frameData, mouseX, mouseY))
                frameCount += 1 
        
        # Now Set the Average for each 
        for spinePts in self.spinalLandmarksArr: 
            spinePts.calculateAvgDistance()
        
        self._Pause = True 



    def _convtXYToSpcPointsHelper(self, index): 
        avgDepthVal = self.spinalLandmarksArr[index].getAvgDistance()
        pointX, pointY = self.spinalLandmarksArr[index].getXY()
        distanceX = float(((pointX - self._CAM_SETS.principal_x) * avgDepthVal)/self._CAM_SETS.focal_x)
        distanceY = float(((pointY - self._CAM_SETS.principal_y) * avgDepthVal)/self._CAM_SETS.focal_y)

        return distanceX, distanceY, avgDepthVal

    
    # We need to convert the x and y points to mm locations in space, so we can find the distance between any of the points
    def convt_XY_To_SpcPts(self): 
        # First Lets Check Every Point to ensure that all values are valid 
        for index, spinePts in enumerate(self.spinalLandmarksArr): 
            if spinePts.getAvgDistance() is None: 
                self._ProgramLog.output(3, f"Error DEPTH of spinal point index {index} with X-Value, Y-Value: {spinePts.getXY()} is invalid,\nplease reset the program and try again!")
                raise("Error, invalid Average Distance")
            else: 
                distanceX, distanceY, _ = self._convtXYToSpcPointsHelper(index)
                spinePts.set_RealSpc_Vals(distanceX, distanceY)

    
    # Find the Distance Between the Selected Points
    def distanceBetweenPoints(self, index1, index2): 
        # Get the Point location in space
        _, point1y = self.spinalLandmarksArr[index1].getSpcPoints()
        _, point2y = self.spinalLandmarksArr[index2].getSpcPoints()

        distanceY = point2y - point1y 
        if distanceY > 0:
            return distanceY
        else:
             return 0 

    # This should always attempt to find the greatest distance difference between c7 and t12/L1 
    def getDeepest(self, index1, index2): 
        c7x, c7y = self.spinalLandmarksArr[index1].getXY()
        t12x, t12y = self.spinalLandmarksArr[index2].getXY()

        c7z = self.spinalLandmarksArr[index1].getAvgDistance()
        largestDiff, largestDiffYCoord = 0, 0 

        # Since The Person Should Not Be Moving As Much, we can grab the current framedata to provide us with distances 
        for i in range(c7y+1, t12y+1): 
            depth = self._OpenCVDepthHandler.getDepth(self.frameData, c7x, i) 
            self._PatientLog.output(2, f"X,Y Coordinate: ({c7x}, {c7y}) Depth: {depth}")
            depthDiff = c7z-depth
            if depth > largestDiff: 
                largestDiff = depthDiff
                largestDiffYCoord = i
        self._PatientLog.output(2, f"Largest Depth Point Difference: {largestDiff} found at Y Location: {largestDiffYCoord}")    
        if largestDiff == 0: 
            self._ProgramLog.output(3,"Error, could not obtain depth points correctly, exiting...")
        
        return c7x, largestDiff, largestDiffYCoord
    

    
    # Now that all the helper functions are complete, now I can attempt to find the kyphosis index 
    def kyphosisIndex(self): 
        # Get Distance between points C7 and T12/L1
        lenC7toT12 = self.distanceBetweenPoints(0,1)
        # Now Get greatest distance difference between said points 
        x,y,z = self.getDeepest()
        
        # Kyphosis index equation
        if lenC7toT12 == 0: 
            self._ProgramLog.output(3, "\nFatal Error, unable to retrieve Distance Between Spinal Points C7 and T12 (index 0 and 1)")
            raise("Zero Division Error in Function: Kyphosis Index!")
        else: 
            return ((z/lenC7toT12) * 100)



    def doCalculations(self): 
        if not self._AllowCalculations or not self._DoCalculations: 
            return 
        
        # Change Flags Accordingly 
        self._AllowCalculations, self._DoCalculations, self._Pause = False, False, True  
        # First convert all the points to xy_spc points 
        self.convt_XY_To_SpcPts() 
        # Now Calculate Kyphosis Index, and save it 
        self.kyphosisIndexValue = self.kyphosisIndex()
        self.kyphosisIndexArr.append(self.kyphosisIndexValue)

        # Set the Calculations Completed Flag to True
        self._CalculationCompleted = True 



    def runTime(self): 
        return 



if __name__ == "__main__": 
    _Program = Kyphosis()
    _Program.runTime()