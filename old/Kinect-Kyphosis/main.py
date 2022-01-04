# Pykinect Library
from ctypes import WINFUNCTYPE
from pykinect2 import PyKinectV2
from pykinect2.PyKinectV2 import *
from pykinect2 import PyKinectRuntime

# Regular Libraries
import os
import time
import cv2 

# Custom Resource Files 
from resources import windowManagement as WM
from resources import mousePts as mousePts
from resources import Logging as Log



# Declare a Global Logging object
Logger =  Log.LOGGING(os.path.join("logs", str("log-" + time.strftime("%Y%m%d-%H%M%S") + ".txt")))

# point.z = depthVal
# point.x = (x - CameraParams.cx) * point.z / CameraParams.fx; 
# point.y = (y - CameraParams.cy) * point.z / CameraParams.fy 

class CAMPARAM: 
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
   
    # For Debug Purposes
    def showIntrinsics(self): 
        Logger.output(2, "Focal_X, Focal_Y, Principle_X, Principle_Y")
        Logger.output(2, (str(self.focal_x) + " " +  str(self.focal_y) + " " + str(self.principal_x) + " " + str(self.principal_y)))



   
# This class does all the magic, this allows the tester to grab the 3 points of reference they need: C7, T12/L1, and S1
class INFRAIMP: 

    def __init__(self): 
        # Instatntitate the Example Program, so I can accesss necessary portions
        #self._irClass = IRI.InfraRedRuntime()
        # Now get the kinect class based from the IRI InfraRedRuntime() class. 
        self._Kinectdev = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
        # Camera Settings, to do distance calcs
        self._CAM_SETS = CAMPARAM()
        # Calibration Frames -> Don't use for now, will see if accuracy is great after testing -> 10/27
        self._CALIBRATION_MAX = 10 
        self._IsCalibrated = False

        # Amount of scans
        self._REQSCANS = 3 
        # Amount of scans done during the program
        self.SCANCNT = 0
        self.KyphosisArr = [] 
        # Array to hold depth values, of the 3 landmarks
        self.spinalLandmarks = [] 
        # Identifier points 
        self.id = 1 
        # 3 points are necessary to obtain thoracic index: C7, T12/L1 and S1
        self._REQPOINTS = 3
        
        # OpenCV Size Parameters
        self.height, self.width = self._Kinectdev.depth_frame_desc.Height, self._Kinectdev.depth_frame_desc.Width
        # Max Frames to average -> should be 5, as commonly seen w other research
        self._MAXFRAMES = 5 
        # OpenCV Window Manager
        self.openCV = WM.cvController(self._Kinectdev.depth_frame_desc.Height, self._Kinectdev.depth_frame_desc.Width, self.id, Logger)
        # To save a frame for openCV, without modifying original
        self.frameSave = None
        self.frameSaveData = None
        # To trigger opencv exit
        self._is_Done = False
        # Universal Pause so I dont have to use semaphores
        self.pause = False

        # Background Removal
        self._MIN_DEPTH ,self._MAX_DEPTH = 609.6, 1371.6 # Between 2 ft and 4.5 feet away from camera
        self.saved = False
    # Calibrate the Camera, may have to run over a period of time -> see if it is an issue later on -> 10/27
    def runCalibration(self): 
        
        #focalX, focalY, princX, princY = 0,0,0,0
        for i in range(self._CALIBRATION_MAX): 
            if self._Kinectdev.has_new_depth_frame(): 
                intrinsics = self._Kinectdev._mapper.GetDepthCameraIntrinsics()
                self._CAM_SETS.setIntrinsics(intrinSics_Matrix=intrinsics)
                #focalX += intrinsics.FocalLengthX 
                #focalY += intrinsics.FocalLengthY 
                #princX += intrinsics.PrincipalPointX
                #princY += intrinsics.PrincipalPointY 

        
        #camParams = [focalX/self._CALIBRATION_MAX, focalY/self._CALIBRATION_MAX, princX/self._CALIBRATION_MAX, princY/self._CALIBRATION_MAX]
        #self._CAM_SETS.focal_x, self._CAM_SETS.focal_y = camParams[0], camParams[1]
        #self._CAM_SETS.principal_x, self._CAM_SETS.principal_y = camParams[2], camParams[3]
        
        Logger.output(2, self._CAM_SETS.showIntrinsics())
        
        self._IsCalibrated = True 

    # Remove the Background when saving the program
    def removeBackgroundForSaving(self, frame):
        for y in range(self.height):
            for x in range(self.width):
                depth = self.calcDepth(self.frameSaveData, x, y)
                if depth > self._MAX_DEPTH or depth < self._MIN_DEPTH:
                    frame[y,x] = [0,0,0]
        
                

    def openCVEvents(self, FRAMECOUNT, ALLOWCALCULATIONSFLAG, DATAWASPROCESSED): 
       
      
        # First lets handle any mouse events
        #self.openCV.Edit()
        #if self.openCV.cropping == True: 
        #    print("cropping")
        #    self.openCV.crop()
        #else: 
        mouseX, mouseY = None, None
        self.openCV.handleMousePress()
        
        try:
            if len(self.openCV.locations) > 0:
             mouseX, mouseY = self.openCV.locations.pop().getXY()
        except: 
            Logger.output(2, "Error retrieving x,y coordinate of mouse, exit error...")
            mouseX, mouseY = None, None
            assert("Unable to retrieve mouse coordinates, exit now")
         
        if (mouseX != None and mouseY != None) and len(self.spinalLandmarks) <= self._REQPOINTS: 
            if len(self.spinalLandmarks) > 0: 
                mouseX, _ = self.spinalLandmarks[0].getXY()    
            self.spinalLandmarks.append(mousePts.MOUSE_PTS(self.id, mouseX, mouseY))
            self.id += 1
            Logger.output(3,("A Point Was Placed at X: " + str(mouseX) + " Y: "+ str(mouseY)))
        elif len(self.spinalLandmarks) > self._REQPOINTS: 
            Logger.output(1, "Too many Points, please press space to reset and continue if needed...")
        
        
        # Now Lets Handle Keypresses 
        keypress = cv2.waitKey(1) & 0xFF
        if keypress == 27: # If key esc pressed reset program
            self.spinalLandmarks = [] 
            self.id = 1
            self.openCV.resetLocations() 
            # Reset Flags 
            FRAMECOUNT, ALLOWCALCULATIONSFLAG, DATAWASPROCESSED = 0, False, False
        elif keypress == ord('b'):
            # We want to begin data collections 
            Logger.output(3, "Beginning Data Collection...")
            ALLOWCALCULATIONSFLAG = True 
            Logger.output(3, "Points Selected: ")
            for i in self.spinalLandmarks: 
                Logger.output(3, i.getXY())
        elif keypress == ord('c'):
            if len(self.spinalLandmarks) > 0 and ALLOWCALCULATIONSFLAG: 
                Logger.output(3, "Beginning Calculations...")
                self.doCalculations()
                DATAWASPROCESSED = True 
        elif keypress == ord('s'): 
            if self.saved == False:
                self.saved = True
                Logger.output(3, "Saving Image...")
                self.removeBackgroundForSaving(self.frameSave)
                cv2.namedWindow("Saved Image")
                cv2.imshow("Saved Image", self.frameSave)
                self.openCV.saveImage("Image-" + str(time.strftime("%Y%m%d-%H%M%S")) + ".png")
            else: 
                self.saved = False
                cv2.destroyWindow("Saved Image")

        #elif keypress == ord('x'): 
        #    self.openCV.setCrop()
        elif keypress == ord('q'):
            self._is_Done = True
            self.openCV.closeWindows()
        elif keypress == ord('p'): 
            if self.pause: 
                self.pause = False 
            else: 
                self.pause = True
        
        
        return FRAMECOUNT, ALLOWCALCULATIONSFLAG, DATAWASPROCESSED # 11.18: Need to fix the allowcalcuations flag
            


    # For all values in a given array, calculate the avg depth/distance    
    def avgDistance(self, arrOfDistances) -> int: 
        
        sum = 0 

        for values in arrOfDistances: 
            sum += values
        
        return (sum/len(arrOfDistances))


    # Converts a given array index, that contains xyz vals into actual mm measurements -> HELPER Function
    def _convtXYToDistance(self, ptIndex): 
        
        depthVal = self.spinalLandmarks[ptIndex].getAvgDistance()
        pointX, pointY = self.spinalLandmarks[ptIndex].getXY()
        distanceX = ((pointX - self._CAM_SETS.principal_x) * depthVal)/self._CAM_SETS.focal_x
        distanceY = ((pointY - self._CAM_SETS.principal_y) * depthVal)/self._CAM_SETS.focal_y 
        
        return float(distanceX),float(distanceY), float(depthVal) # Will return as mm distances
    
    # Convert every x,y to distance in mm
    def convt_XY_Pts_To_Distance(self): 
        for elements in self.spinalLandmarks: 
            if elements.getAvgDistance() == None: 
                raise("Error, average distances must be calculated first")
        
        # Set all the real distance values of each x,y coordinate
        for i in range(len(self.spinalLandmarks)): 
            distanceX, distanceY, distanceZ = self._convtXYToDistance(i)
            self.spinalLandmarks[i].set_Real_Distances(distanceX, distanceY)


    # Obtain the distance between two points of the spine
    def distanceBetweenPoints(self, index1, index2):
        point1x,point1y = self.spinalLandmarks[index1].getRealDistances()
        point2x,point2y = self.spinalLandmarks[index2].getRealDistances()

        point2y - point1y; 
        # Debug Print
        #print(point2y, point1y)
        #Since we're looking for height, we return the y-distances, should be positive values only
        distanceY =  point2y-point1y
        if distanceY < 0: 
            return distanceY * -1
        else: 
            return distanceY

        
    

    # Find the z value of the largest depth from C7 until t12, so we need to travel along the y-axis only
    # Since we're looking at the back as a "flat" image, we can simply
    # move down the y-axis to find the pixel with the furthest depth
    # Will return the c7x and then the y coordinate furthest away
    def getDeepest(self): 
        c7x, c7y = self.spinalLandmarks[0].getXY()
        t12x,t12y = self.spinalLandmarks[1].getXY()

        c7z = self.spinalLandmarks[0].getAvgDistance()
        largestDiff, largestDiffY = 0,0

        # Get most recent frame data
        # Create a frame reader object
        frameData=self._Kinectdev._depth_frame_data
        for i in range(c7y+1, t12y-1): 
            depth = self.calcDepth(frameData, c7x, i)
            Logger.output(2, str("X,Y Coordinate: ("+ str(c7x) + "," + str(i) + ") " + "Depth: " + str(depth)))
            depthDiff = c7z-depth
            if depthDiff > largestDiff: 
                largestDiff = depthDiff
                largestDiffY = i
        Logger.output(2, str("Largest Depth Point Difference: " + str(largestDiffY)))
        if largestDiff == 0: 
            raise("Error, index could not be calculated")
        return  c7x,largestDiffY,largestDiff

    # Calculate the kyphosis index, normal range from 25-45
    def kyphosisIndex(self): 
        # Get Distance between C7 and T12/L1
        lenC7toT12_L1 = self.distanceBetweenPoints(0,1)
        # Get x,y coordinate of deepest point between C7 and T12/L1
        # Get the largest depth/height 
        x,y,z = self.getDeepest()

        return (z/lenC7toT12_L1) * 100


        
   

    # Perform Post Processing, of data to get wanted info
    def doCalculations(self): 
        # First Perform the Depth Averaging
        try:
            counter = 1 
            for elements in self.spinalLandmarks: 
                if len(elements.getDepthValsArr()) == 0: 
                    assert("Depth Values are empty!!!")
                avgDistance = self.avgDistance(elements.getDepthValsArr())
                elements.setAvgDistance(avgDistance)
                # Debug Print Statement below, implement logging later -> Dopne 11/1/2021 3:06 am 
                Logger.output(2, str("Point " + str(elements.get_Pt_ID()) + " with x,y coordinate " + str(elements.getXY()) +  " has average distance of: " + str(elements.getAvgDistance())))
                counter+=1
            
            # Convt X,Y to mm measurements
            self.convt_XY_Pts_To_Distance()
        except Exception as er: 
            Logger.output(2, er)
            raise("A serious error occured, please view the Log Files for more info.")
            

        # Get distance between C7 and T12/L1 
        # Remember arrays start from 0, so we are going from point 0-2
        #self.distanceBetweenPoints(0,2) # will return the distance between two given points 

        # Kyphosis Index 
        Logger.output(3, "\nKyphosis Index Is: " + str(self.kyphosisIndex()))
    

        # Debug Print, implement logging later
        Logger.output(3, ("The Length of the Spine is: " + str(self.distanceBetweenPoints(0,2))))
        Logger.output(2,"\n\n")
        # Increment Scan Count 
        self.KyphosisArr.append(self.kyphosisIndex())
        self.SCANCNT += 1 

    # Return the depth of a given x,y
    def calcDepth(self, frameReaderObj, x, y): 
        # Should be width of 512
        return frameReaderObj[(y * self._Kinectdev.depth_frame_desc.Width) + x]



    # Runs the program 
    # Pre-req: Grab Calibration Data -> Complete
    # (1) Gather the data points to measure -> Complete
    # (2) Obtain data -> Complete
    # (3) Average all depth vals -> Complete
    #
    # (4) Convt X,Y to mm measurments -> Functions done -> Add to code
    # (5) Calculate distance from C7 and T12/L1 (optional C7 and S1) -> Functions done -> Add to code
    # (6) Obtain height by using depth difference from C7 and T12 -> Functions Done -> Add to code
    # (7) Calculate angle/index of kyphosis -> Need to create function
    # 
    def runProgram(self): 
        # Mouse coordinates holder
        mouseX, mouseY = 0,0
        # Frames Read 
        frameCount = 0
        # Frame Image 
        frame = None 
        frameData = None

        # Prepared for Window?
        prepared = False

        # Begin Recording Data 
        beginDataCollections = False

        # Was the data already processed? 
        DATAWASPROCESSED = False

       
        # Create Game Loop
        while not self._is_Done and self.SCANCNT < self._REQSCANS:
            
            # Shift away from pygame later
            # The value of parameters should be the same as the value fed in, unless reset activated
            # This will create the array of points to be tracked
            frameCount, beginDataCollections, DATAWASPROCESSED = self.openCVEvents(frameCount, beginDataCollections, DATAWASPROCESSED)

            # Get the last frame 
            # so first draw the ir frame and then display the circles
            if (self._Kinectdev.has_new_depth_frame()) and (frameCount < self._MAXFRAMES) and (self.pause == False):
                # Grab calibration data first if not already calibrated
                if not self._IsCalibrated:
                    self.runCalibration()
                # 3 Steps to obtain depth information
                # (1) Obtain Frame Source
                # (2) Feed Frame Source Data into a Frame Reader Object
                # (3) Get Depth Data from Frame Reader Object
                
                # (1) Obtain Frame Source
                self.frameSave = self._Kinectdev.get_last_depth_frame()
                # (2) Now create a framereader object to hold the depth vals of all pixels in the depth frame data 
                self.frameSaveData = self._Kinectdev._depth_frame_data
        
            
                # Prepare to show on cv2
                #prepared, frameSave = self.prepareForDisplay(frameSave)
                self.frameSave = self.openCV.cnvtKinectImage(self.frameSave)
                prepared = True 
                
                
                # (3) Now read the depth value of a given x,y coordinate of the frame
                # The x,y coordinate should come from the points on the spine that were marked and saved into the SpinalPts array
                # Only Provide Data When 3 points of reference (C7, t12/L1, S1) have been obtained 
                if (len(self.spinalLandmarks) == self._REQPOINTS and frameCount < self._MAXFRAMES) and beginDataCollections: 
                    for i in range(len(self.spinalLandmarks)):
                        # First Get the Value of position x,y that user marked stored in spinalLandmark Array
                        mouseX, mouseY = self.spinalLandmarks[i].getXY()
                        # Read the depthValues from the x,y points in the structure
                        distance_Depth_Val = self.calcDepth(self.frameSaveData, mouseX, mouseY) # Save this to depth array of each point, this is the standard equation to get depth value in 3d array
                        # Save the depth value to the depth value array of location i
                        self.spinalLandmarks[i].setDepth_Val(distance_Depth_Val)

                # Points selected should be shown immediately
                for i in range(len(self.spinalLandmarks)): 
                    color = [(255,0,0), (0,255,0), (0,0,255)] # Just to give different colors based on the order which the points was placed (RGB)
                    x_temp, y_temp = self.spinalLandmarks[i].getXY()
                    self.openCV.drawCircleToCV(x_temp, y_temp, color=color[i%len(color)])
                    
                
            
            # Pause Capture When Five Frames have been saved, but only after 3 points identified
            if len(self.spinalLandmarks) == self._REQPOINTS and beginDataCollections:
                frameCount += 1 
            if (frameCount < self._MAXFRAMES) and (prepared) and (self.pause == False):
                self.openCV.displayImage()
        
        # Now Perform Calculations
        if (not DATAWASPROCESSED and len(self.spinalLandmarks) == self._REQPOINTS):
            self.doCalculations()
        
        # Average all kyphosis index amounts 
        if self.KyphosisArr:
            sum = 0
            for i in self.KyphosisArr: 
                sum += i
            index = sum/len(self.KyphosisArr)
            Logger.output(3,("\nAverage Kyphosis Index: " + str(index)))

            self._Kinectdev.close()


            

def main(): 
    # Create the Kinect Object    
    program = INFRAIMP()
    program.runProgram()
   

if __name__ == "__main__": 
    # Should create a new instance of the logging library for each class with title of log"Date_Time_here".txt
    #Logger = Log.LOGGING(os.path.join("logs", str("log-" + time.strftime("%Y%m%d-%H%M%S") + ".txt")))
    main()
     # Close the logfile 
    Logger.closeFile()