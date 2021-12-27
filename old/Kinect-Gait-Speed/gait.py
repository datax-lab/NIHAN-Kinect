# Pykinect Library imports
from posixpath import abspath
from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime

# General Libraries
import os
import time
import cv2
import numpy as np
import traceback



# Custom Libraries
from Resources import windowManagers as WM
from Resources import imageEditor as IMPROC
from Resources import timer as Timer
from Resources import Logging as lg
from Resources import plot 

# Logging 




# Actual Class
class GAIT():
    def __init__(self):
        # Standard Pykinect V2 init
        self._KinectDev = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
        self._Height, self._Width = self._KinectDev.depth_frame_desc.Height, self._KinectDev.depth_frame_desc.Width

        # UI Integrations
        # Grab Initial Image from a UI
        self._FileExplorerSelection = WM.FileExplorer(self._Height, self._Width)
        self._FileExplorerSelection.handleButtonPresses()
        self._InitImageFileName = self._FileExplorerSelection.returnInitImage()

        # Confirmation Box UI
        self._ConfirmationBoxForSaving = WM.ConfirmationDialogBox("Save as initilization image?", self._Height,
                                                                  self._Width)
        # Image Processing Vars
        # Now Create Frames For Analysis and Displaying
        #   displayframe -> the frame that will be displayed to the viewfinder
        #   frame -> the internal frame to do calculations with
        #   framedataReader -> The object that will hold the depth frame data (i.e. 3d array of depth data)
        self.displayFrame = np.zeros((self._Height, self._Width), np.uint8)
        self._PauseFrame, self.frame, self.frameDataReader = None, None, None
        self._InitFrame = None # To Hold the Initial Frame, will be used to find what's a foreground object and what's not
        self._MaxFrameCalibrationCnt = 5
        #print("Debug Print:",self._InitImageFileName)
        # Instantiate Image Processing Custom Library
        self._OpenCVDepthHandler = IMPROC.CVEDITOR_DEPTH(self._Height, self._Width, "Kinect V2 Gait Analyzer",
                                                         self._InitFrame)
        
        # Data Plotting
        self.plot, self.plotFlag = plot.PLOTTER() , False 
        

        # Program Flags
        self._PAUSE, self._IsDone, self._BegZoneReached, self._EndReached = False, False, False, False
        self._InitFrameConvted = False # This is to ensure that we conver the image first
        self._AllowDataCollection, self._CalculationsAllowed = False, False
        self._PictureTaken, self._PictureWindowName = False, "Saved Image"
        self._startDistanceCaptured = False 

        # Error Handling
        self._LastPosition = []

        
        
        # Program Logging and Data Collection 
        # Create Necessary Directories if Needed
        self._ProgramPath = os.path.dirname(os.path.abspath(__file__))
        if __name__ != "__main__": 
            self._ProgramPath = os.path.dirname(self._ProgramPath)

        if not os.path.isdir(os.path.join(self._ProgramPath, "syslogs")):
                os.mkdir(os.path.join(self._ProgramPath, "syslogs"))
        sysLogsDir = os.path.join(self._ProgramPath, "sysLogs")
        self._programLog = lg.LOGGING(os.path.join(sysLogsDir, str("runtimeLog-" + time.strftime("%Y%m%d-%H%M%S") + ".txt")))
        
        if not os.path.isdir(os.path.join(self._ProgramPath, "logs")):
                os.mkdir(os.path.join(self._ProgramPath, "logs"))
        # Save the Stats 
        ptLogDirectory = os.path.join(self._ProgramPath, "logs")
        self._ptLog = lg.LOGGING(os.path.join(ptLogDirectory, str("Ptlog-" + time.strftime("%Y%m%d-%H%M%S") + ".txt")))

        
        
        # Message Formats
        self._BgStart, self._BgEnd, self._TextStart = (0, 0), (self._Width, 50), (40, 25)

        # Gait Speed Setup Vars
        self._Timer = Timer.Timer("Kinect V2 Acceleration Zone Speed Timer")
        self._TimerMeasure = Timer.Timer("Measurement Zone Timer")
        self._BeginMeasurementZone, self._EndMeasurementZone = 1000, 4000 # Begin Measurement Zone at 1m and end at 4m
        self._StartDistance, self._CalibrateStartDist, self._AllowStartDistanceInit = 0, False, False
        self._CalculationsFlag = False 
        self.currentDistance = 0
        # Gait Speed Vars
        self._TimeTakenToWalk = None
        self._UnitConversionFactor = 1000
        self._Gait_Speed = None # rep as m/s

        




    # Important Event Controller Functions
    def openCVEvents(self, limitKeybind = False):

        keypress=cv2.waitKey(1) & 0xFF

        # If We Need to Limit Out Keybinds to either quit or calibrate
        if limitKeybind is True:
            if keypress == ord("q"):
                exit(0)
            elif keypress == ord("c"):
                self.handleInitImg()


        else:

            # These are the normal keybinds
            if keypress == ord("q"):
                self._OpenCVDepthHandler.closeAllWindows()
                self._IsDone = True
            elif keypress == ord("p"):
                if self._PictureTaken is False:
                    picName =  str(time.strftime("%Y%m%d-%H%M%S")) + ".png"
                    self._OpenCVDepthHandler.saveImage(picName, self.displayFrame)
                    self._PictureTaken = True
                    cv2.namedWindow(self._PictureWindowName)
                    cv2.imshow(self._PictureWindowName, self.displayFrame)
                else:
                    cv2.destroyWindow(self._PictureWindowName)
                    self._PictureTaken = False
            elif keypress == ord("s"):
                if self._startDistanceCaptured: 
                    print("Timer and Gait Tracking Started, program will auto-pause when patient has reached endpoint...\n")
                    self._Timer.starTtimer(True)
                    self._AllowDataCollection = True 
            elif keypress == ord("i"):
                # Get the starting distance of the person here
                self._AllowStartDistanceInit = True
            elif keypress == ord("c"): 
                if self._startDistanceCaptured: 
                    if self._Timer.isTimerStopped is False or self._TimerMeasure.isTimerStopped() is False: 
                        self._Timer.endTimer()   
                        self._TimerMeasure.endTimer()
                    self._CalculationsAllowed = True  
            elif keypress == ord("v"): 
                if self.plot.getSize() > 0: 
                    self.plotFlag = True 
                    fileName = "GAIT Speed Graph-" + time.strftime("%Y%m%d-%H%M%S") + ".png"
                    self.plot.plotPts(fileName, "Time (sec)", "Speed (m/s)")
                


    def handleNewDepthFrames(self) -> np.ndarray:
        if self._KinectDev.has_new_depth_frame():
            self.frame, self.frameDataReader = self._KinectDev.get_last_depth_frame(), self._KinectDev._depth_frame_data
            self.displayFrame, self.frame = self._OpenCVDepthHandler.convtImg(self.frame)
        else: 
            self.frame = None 

        return self.frame # We do a return here, cause we will alsol use this function to find the person's starting
                       # from the camera, along with capturing an init frame
        
    




    # Functions to be called in functions
    def _find_min(self, x_Start, width, y_Start, height):
        distanceArr = []
        # Go Through Distances Around the Object Midpoint searching for ones larger than or equal to the endzone distance
        if width is None or height is None: 
            x_Start, width, y_Start, height = self._LastPosition[0], self._LastPosition[1], self._LastPosition[2], self._LastPosition[3]
            self._programLog.output(2, "Fall Back Point was Used at x_Start: " + str(x_Start) + "y_Start: " + str(y_Start))
        
        # Since the kinect may lose the person at random points, this is a fallback point
        self._LastPosition=[x_Start, width, y_Start, height]

        for x in range(x_Start, x_Start+width):
            for y in range(y_Start, y_Start+height):
                distance = self._OpenCVDepthHandler.getDepth(self.frameDataReader, x, y)
                # Save the Distances that are not 0 and
                # when subtracted by the start distance are still larger than or equal to
                # the endMeasurement zone
                if distance != 0 and  distance >= self._EndMeasurementZone:
                    distanceArr.append((distance - self._StartDistance))
        # Sort the array so that the smallest distance is at the front
        distanceArr = sorted(distanceArr)
        # Return this smallest distance to see if we really are at the endpoint
        try: 
            return distanceArr[0]
        except Exception as err: 
            self._programLog.output(2, str(traceback.format_exc()))
            print("Critical Error, please view syslogs for more info")
            print("There was a critical error, try adjusting the camera to point up more.")
            exit(-1)

    # Converts the image selected from the file explorer to a grayscale img
    # Then sets the self._InitFrame to it 
    def _convt_init_img(self, anInitFrame = None):

        if self._InitImageFileName is not None:
            self._InitFrame = cv2.imread(self._InitImageFileName)
            self._InitFrame = cv2.cvtColor(self._InitFrame, cv2.COLOR_RGB2GRAY)
        # Now convert the actual initial image
        else:
            _, self._InitFrame = self._OpenCVDepthHandler.convtImg(self._InitFrame)
            self._InitFrame = cv2.imread(self._InitImageFileName)
            self._InitFrameConvted = True
    
    


    # Standard Events Handling Functions
    def createAnInitFrame(self):

        while self._InitFrame is None:
            self._InitFrame = self.handleNewDepthFrames()

        # Clean Up, since the function itself assigns the frames to the following variables, but we dont want that
        self.frame, self.displayFrame, self.frameDataReader = None, None, None


    def handleInitImg(self): 
        print("Calibrating Now, please ensure the area is cleared!")
        self.createAnInitFrame()
        OrigimgName = "Kinect_Img-" + time.strftime("%Y%m%d-%H%M%S") + ".png"
        cv2.namedWindow(OrigimgName)
        cv2.imshow(OrigimgName, self._InitFrame)
        self._ConfirmationBoxForSaving.handleButtonPress()
        if self._ConfirmationBoxForSaving.getResponse() is True:
            # Clear Error Flags
            self._InitFrameConvted = True
            self._DisplayAMessage = False
            self._PAUSE = False
            # Generate the init image folder if it does not already exist
            if not os.path.isdir(os.path.join(self._ProgramPath, "init_images")):
                os.mkdir(os.path.join(self._ProgramPath, "init_images")) 
            imgName = os.path.join(self._ProgramPath,"init_images")
            imgName= os.path.join(imgName, OrigimgName) 
            # Write and display the image 
            cv2.imwrite(imgName, self._InitFrame)
            cv2.destroyWindow(OrigimgName)
            print("Calibration Complete!\n")
        else:
            self._InitFrame = None
            cv2.destroyWindow(OrigimgName)


    def handleNoInitFrame(self):
        if self.displayFrame is None: 
            return 
        #message, beginRect, endRect, startText = None, None, None, None
        # If we have no init image display a message asking to capture one
        if self._InitFrame is None and self._InitFrameConvted is False:
            # Print The Error, and display message to capture an init frame 
            message = "No Initilization Frame, press \"c\" to capture one"
            self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, message, self._BgStart, self._BgEnd,
                                                         self._TextStart)
        


    def handleStartDistance(self, currFrameCnt) -> int:
        
        if self._CalibrateStartDist is False and self._PAUSE is True:
            return currFrameCnt
        # Declare some local variables
        x_Cent, y_Cent = None, None
        # Actual Logic to Get Start Distance
        if currFrameCnt < self._MaxFrameCalibrationCnt:
            if self.handleNewDepthFrames() is not None:
                x_Cent, y_Cent, _, _ = self._OpenCVDepthHandler.getObjectMidPoint(self._InitFrame, self.frame,
                                                                                  self.displayFrame)
                if (x_Cent is not None and y_Cent is not None) and self._AllowStartDistanceInit:
                    self._StartDistance += self._OpenCVDepthHandler.getDepth(self.frameDataReader, x_Cent, y_Cent)
                    currFrameCnt += 1
                else: 
                    message = "No Person Detected!"
                    self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, message, self._BgStart,
                                                                    self._BgEnd, self._TextStart)
                    self._AllowStartDistanceInit = False
            
            if not self._AllowStartDistanceInit:
                message = "Press \'i\' to get Start Distance"
                self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, message, self._BgStart,
                                                            self._BgEnd, self._TextStart)
                                                        
            
        elif currFrameCnt >= self._MaxFrameCalibrationCnt:
            # Finish Up
            self._AllowStartDistanceInit = False
            self._CalibrateStartDist = False
            self._StartDistance = self._StartDistance / self._MaxFrameCalibrationCnt
            self._startDistanceCaptured = True 

        return currFrameCnt


    # Handles getting the distance and determining start and end zones
    # Handles pausing the program when the end is reached
    def handleGeneralDistance(self):
        if self._PAUSE is True:
            return
        
        x_Cent, y_Cent = None, None
        
        if self.frame is not None:
            x_Cent, y_Cent, width, height = self._OpenCVDepthHandler.getObjectMidPoint(self._InitFrame, self.frame,
                                                                                       self.displayFrame)

            # Only Start Analyzing images when user presses the start key
            if self._AllowDataCollection:
                if (x_Cent is not None and y_Cent is not None):
                    self.currentDistance = (self._OpenCVDepthHandler.getDepth(self.frameDataReader, x_Cent, y_Cent) - self._StartDistance)
                if self.currentDistance >= self._BeginMeasurementZone and self.currentDistance <= self._EndMeasurementZone:
                    if self._find_min(x_Cent, width, y_Cent, height) >= self._BeginMeasurementZone:
                        self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, "Measurement Zone Entered!",
                                                                 self._BgStart, self._BgEnd, self._TextStart)
                        # Debug Print 
                        if self._BegZoneReached is False: 
                            print("----------------------------------------")
                            print("Patient Entered Measruement Zone")
                            print("----------------------------------------\n")
                            self._BegZoneReached = True
                # Here's a Tricky part, we need to make sure that this is rlly the endpoint, or at least very close to it, before we
                # Pause the program
                elif self.currentDistance >= self._EndMeasurementZone:
                    # Lets check to see if this rlly is the true end point
                    distance = self._find_min(x_Cent,width, y_Cent, height)
                    #print(distance)
                    if distance >= self._EndMeasurementZone:
                        self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, "Patient Has Reached Enpoint! Press \"c\" to get gait speed",
                                                                     self._BgStart, self._BgEnd, self._TextStart)
                        self._PAUSE, self._EndReached = True, True
                        self._AllowDataCollection = False 
                        self._PauseFrame = self.displayFrame
            else: 
                self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, "Press \"s\" to Start Gait Tracking", 
                                                            self._BgStart, self._BgEnd, self._TextStart)


    # Now we want to do gait speed calculations 
    def doGaitSpeedCalc(self): 
        if self._CalculationsAllowed is False: 
            return 
        
        # Change applicable flags 
        if self._Timer.isTimerStopped() is False: 
            self._Timer.endTimer()
        if self._TimerMeasure.isTimerStopped() is False: 
            self._TimerMeasure.endTimer()
        
        self._EndReached, self._CalculationsAllowed = True, False 
        self._AllowDataCollection = False
        self._TimeTakenToWalk = self._TimerMeasure.getTimeDiff()

        # Now Perform Calculations 
        if self._TimeTakenToWalk > 0: 
            try: 
                self._Gait_Speed = float((self._EndMeasurementZone/self._UnitConversionFactor) / self._TimeTakenToWalk)
            except ZeroDivisionError: 
                assert("No Data to Calculate Gait Speed Provided!!")


    # Closing Program Function 
    def finishProgram(self): 
        self._ptLog.output(3,"\n\n------------------------------------")
        self._ptLog.output(3, "          Statistics:              ") 
        self._ptLog.output(3,"------------------------------------")
        # Display Stats 
        if self._EndReached is True and self._CalculationsAllowed == False: 
            
            if self.plotFlag is False and self.plot.isListEmpty(): 
                self._programLog.output(2,"------------------------------------")
                self._programLog.output(2, "          Statistics:              ") 
                self._programLog.output(2,"------------------------------------")
                self._programLog.output(3, "\n")
                self._programLog.output(3, "X-Plot Points (Times)" + str(self.plot.x_Points))
                self._programLog.output(3, "Y-Plot Points (Speed)" + str(self.plot.y_Points))
                self.plot.plotPts("test.png", "Time (sec)", "Speed (m/s)")
                self._ptLog.output(1, "\n\n")

            self._CalculationsAllowed = True 
            self.doGaitSpeedCalc()
        if self._EndReached is True: 
            self._ptLog.output(3,"Starting Distance: " + str(self._StartDistance))
            self._ptLog.output(3,"Program Time Elapsed: " + str(self._Timer.getTimeDiff()))
            self._ptLog.output(3,"Elapsed Time: " + str(self._TimeTakenToWalk))
            self._ptLog.output(3,"Calculated Gait Speed: " + str(self._Gait_Speed) + " m/s")
        
        self._programLog.closeFile()
        self._ptLog.closeFile()

    # Runtime 
    def runtime(self):

        calibrationFrameCntr = 0
        # Local Variables to Display a Message to the cv Window
        # Before we do anything for the program we want to see if an initial image was loaded, and converted
        # if it was not already converted, convert the image, otherwise if there is no initial image, then
        # continue to the main program
        if self._InitImageFileName is not None:
            self._convt_init_img()


        # Actual Program Loop
        while not self._IsDone:
            # Get and handle new depth frames
            if self._PAUSE is False: 
                self.handleNewDepthFrames()
            # Let's First Check and see if we have an initial image, we can't allow any cv window events
            # until an initial image is
            # either captured or loaded, otherwise the program doesn't work properly

            if self._BegZoneReached and self._TimerMeasure.isTimerStarted() is False: 
                self._TimerMeasure.starTtimer(True)

            if self._InitFrame is None and self._InitFrameConvted is False:
               self.handleNoInitFrame()
               self.openCVEvents(limitKeybind=True)
            else:
                # Check for any openCV Events, such as keypresses
                self.openCVEvents(limitKeybind=False)
                # Now that we got out depth frame, we want to see if we captured an initial distance and if not we need
                # to see if we the user has allowed the capturing of an initial distance
                if self._PAUSE is False:

                    if self._StartDistance == 0 or self._CalibrateStartDist is True:
                        self._CalibrateStartDist = True
                        calibrationFrameCntr = self.handleStartDistance(calibrationFrameCntr)
                        #message = "Press \'i\' to get Start Distance"
                        #self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, message, self._BgStart,
                        #                                             self._BgEnd, self._TextStart)
                    else:
                        self.handleGeneralDistance()
                
                # Check if the program was paused and the end was reached
                # If so, end the timer and then do the gait speed calculations 
                if self._PAUSE and self._EndReached: 
                    if self._Timer.isTimerStarted(): 
                        self._TimerMeasure.endTimer()
                        self._Timer.endTimer()
                        self.doGaitSpeedCalc()


            # Display The Frame
            if self.frame is not None:
                self._OpenCVDepthHandler.displayFrame(self.displayFrame)
        
        
        
        # Display Stats 
        self.finishProgram()












if __name__ == "__main__":
    gait2 = GAIT()
    gait2.runtime()




