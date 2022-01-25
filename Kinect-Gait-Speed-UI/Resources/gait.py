# Pykinect Library imports

from multiprocessing.dummy import Array
from Resources.pykinect2 import PyKinectV2
from Resources.pykinect2 import PyKinectRuntime

# General Libraries
import os, traceback, time
import cv2
import numpy as np

# UI Imports 
from Resources import windowManager as ui2
# pyQt Imports
from PyQt5.QtCore import QThread, pyqtSignal

# Custom Libraries
from Resources import imageEditor as IMPROC
from Resources import timer as Timer
from Resources import Logging as lg
from Resources import plot 

from Resources.data import DataHandler

      
     
# Actual Class
class GAIT(QThread):
    # Pyqt Signals 
    messages = pyqtSignal(str)
    programCanContinue = pyqtSignal(bool)

    def __init__(self):
        # Standard Pykinect V2 init
        QThread.__init__(self)
        ######################################################
        #               Kinect Setup                         #
        ######################################################
        self._KinectDev = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
        self._Height, self._Width = self._KinectDev.depth_frame_desc.Height, self._KinectDev.depth_frame_desc.Width
        ######################################################
        #               End Kinect Setup                     #
        ######################################################
 

        ######################################################
        #               Program Constants                    #
        ######################################################
        self._MaxFrameCalibrationCnt = 5
        self.programRuntimes = -1 # So that the current index of the gait speed is the same as the program run times
        self.labelRuntimes = self.programRuntimes + 2
        self._StartKey = self.labelRuntimes
        # Gait Constants
        self._BeginMeasurementZone_mm, self._EndMeasurementZone_mm = 1000, 4000 # Begin Measurement Zone at 1m and end at 4m
        self._UnitConversionFactor = 1000

        # Instant Velocity Constants
        self._DistanceOffset = 304.8 # For now its every 1 foot report 

        # Program Logging and Data Collection 
        self._ProgramPath = os.path.dirname(os.path.abspath(__file__))
        self._programLog, self._ptLog = None, None 

        # Instantiate Image Processing Custom Library
        self._OpenCVDepthHandler = IMPROC.CVEDITOR_DEPTH(self._Height, self._Width, "Kinect V2 Gait Analyzer")

        # UI Integrations
        self._FileExplorerSelection = None 
        # Grab Initial Image from a UI
        self._InitImageFileName = None
        self._InitFrame = None # To Hold the Initial Frame, will be used to find what's a foreground object and what's not

        # Message Formats
        self._BgStart, self._BgEnd, self._TextStart = (0, 0), (self._Width, 50), (40, 25)
        ######################################################
        #               End Program Constants                #
        ######################################################

        
        
        # Image Processing Vars
        # Now Create Frames For Analysis and Displaying
        #   displayframe -> the frame that will be displayed to the viewfinder
        #   frame -> the internal frame to do calculations with
        #   framedataReader -> The object that will hold the depth frame data (i.e. 3d array of depth data)
        self.displayFrame = np.zeros((self._Height, self._Width), np.uint8)
        self.frame, self.frameDataReader = None, None
         
        # Data Plotting
        self.plot, self.plotFlag = None, bool 
        

        # Program Flags
        self.aRunTimeComplete = bool 
        self._PAUSE, self._IsDone, self._BegZoneReached, self._EndReached = bool, bool, bool, bool
        self._InitFrameConvted = bool # This is to ensure that we conver the image first
        self._AllowDataCollection, self._CalculationsAllowed = bool, bool
        self._PictureTaken, self._PictureWindowName = bool, "Saved Image"
        self._startDistanceCaptured = bool 
        # Calibration Var
        self.calibrationFrameCntr = int
        self.calculationsDone = bool
        
        # Error Handling
        self._LastPosition = []

        # Gait Speed Data Saving
        self.gait_Speed_Arr = []
        # Gait Speed Setup Vars
        self._Timer, self._TimerMeasure = None, None
        self._StartDistance, self._CalibrateStartDist, self._AllowStartDistanceInit = float, bool, bool
        self.currentDistance, self.curr_Distance_measure_zone = float, float
        # Gait Speed Vars
        self._TimeTakenToWalk = None
        self._Gait_Speed = float # rep as m/s
        self._Gait_Speed_Avg = 0 



        ######################################################
        #               Instant Velocity                     #
        ######################################################
        # Dictionary to save data
        self.iV_Dict = {} #  Dictionary = {
                                  # '1': [{'distance_Measure': 15, 'currIV': 12, 'CurrTime': 15}, {'distance_Measure': 31, 'currIV': 12, 'CurrTime': 70}]
                                  #  } 
        
        # Distance Management 
        self.distanceOffset_Min, self.distanceOffset_Max = float, float
        self.tempIV_Distance_Arr, self.tempIV_Distance_Arr_time, self.searchingForOffset = None, None, bool 

        # Standard Vars 
        self.vf_AccelZone, self.vi_MeasureZone = None, None     
        self.prevDistance = 0 
        self.lastIvCalculated = False 

        ######################################################
        #             End Instant Velocity                   #
        ######################################################

        # Debug Timer 
        self._debugCntr = 0

        # Patient Info 
        self._PatientID, self._PatientName = None, None 
        self._Database = DataHandler()

        # Arrays to Help With Averaging 
        self._IV_Overall, self._IV_time_Overall = [], []

        # Arrays to help with output 
        self._IV_Dict_Averages = {}
        # Program Setup Functions
        self.setupDirectories()
        self.resetProgram()


    def setDatabaseInstance(self, database): 
        self._Database = database

    def setPatientInfo(self, ptInfo): 
        self._PatientID, self._PatientName = ptInfo


    def setupDirectories(self): 
        #Now Adding for EXE 
        if __name__ != "__main__": 
            self._ProgramPath = os.path.dirname(self._ProgramPath)
            #NOw Adding for EXE -> 1/6/2022
            self._ProgramPath = os.getcwd()

        if not os.path.isdir(os.path.join(self._ProgramPath, "ProgramLogs")):
                os.mkdir(os.path.join(self._ProgramPath, "ProgramLogs"))
        sysLogsDir = os.path.join(self._ProgramPath, "ProgramLogs")
        self._programLog = lg.LOGGING(os.path.join(sysLogsDir, str("runtimeLogGAIT-" + time.strftime("%Y%m%d-%H%M%S") + ".txt")))
        
        if not os.path.isdir(os.path.join(self._ProgramPath, "PatientLogs")):
                os.mkdir(os.path.join(self._ProgramPath, "PatientLogs"))
        # Save the Stats 
        ptLogDirectory = os.path.join(self._ProgramPath, "PatientLogs")
        self._ptLog = lg.LOGGING(os.path.join(ptLogDirectory, str("PtlogGAIT-" + time.strftime("%Y%m%d-%H%M%S") + ".txt")))



    exitSignal = pyqtSignal(bool) 
    def programStartup(self): 
        self._FileExplorerSelection = ui2.FileDialog()
        self._FileExplorerSelection.handleButtonPresses()
        self._InitImageFileName = self._FileExplorerSelection.getFileName()
        # If Exit Was Pressed Send the Exit Program Signal
        if self._InitImageFileName == "PROGEXIT": 
            self.exitSignal.emit(True)



    def resetProgram(self): 
        self.displayFrame = np.zeros((self._Height, self._Width), np.uint8)
        self.frame, self.frameDataReader = None, None
        self.plotFlag = False 

        # Program Flags
        self._PAUSE, self._IsDone, self._BegZoneReached, self._EndReached = False, False, False, False
        self._InitFrameConvted = False # This is to ensure that we conver the image first
        self._AllowDataCollection, self._CalculationsAllowed = False, False
        self._PictureTaken, self._PictureWindowName = False, "Saved Image"
        self._startDistanceCaptured = False 
        # Calibration Var
        self.calibrationFrameCntr = 0

        self.plot, self.plotFlag = plot.PLOTTER() , False 

        # Gait Speed Flags
        self._Timer = Timer.Timer("Kinect V2 Acceleration Zone Speed Timer")
        self._TimerMeasure = Timer.Timer("Measurement Zone Timer")
        self._StartDistance, self._CalibrateStartDist, self._AllowStartDistanceInit = 0, False, False
        self._CalculationsFlag = False 
        self.currentDistance, self.curr_Distance_measure_zone = 0, 0

        # Gait Speed Results
        self._TimeTakenToWalk = None
        self._Gait_Speed = None # rep as m/s

        # Instant Velocity 
        self.distanceOffset_Min = self._DistanceOffset
        self.distanceOffset_Max = self.distanceOffset_Min + self._DistanceOffset
        self.tempIV_Distance_Arr, self.tempIV_Distance_Arr_time, self.searchingForOffset = [], [], False 

        self.vf_AccelZone, self.vi_MeasureZone = None, None 
        
        self.prevDistance = 0 
        self.lastIvCalculated = False 
        
        # GUI Signal to continue program 
        self.calculationsDone = False 




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
                distance = self._OpenCVDepthHandler.getDepth(self.frameDataReader, x, y) - self._StartDistance
                # Save the Distances that are not 0 and
                # when subtracted by the start distance are still larger than or equal to
                # the endMeasurement zone
                if distance != 0 and  distance >= self._EndMeasurementZone_mm:
                    distanceArr.append((distance)) 
        # Sort the array so that the smallest distance is at the front
        distanceArr = sorted(distanceArr)
        # Return this smallest distance to see if we really are at the endpoint
        try: 
            if len(distanceArr) > 0:
                return distanceArr[0]
            else: 
                return 0
        except Exception as err: 
            self._programLog.output(2, str(traceback.format_exc()))
            print("Critical Error, please view ProgramLogs for more info")
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
        
        self.messages.emit("Calibrating Now, please ensure the area is cleared!")
        #print("Calibrating Now, please ensure the area is cleared!")
        self.createAnInitFrame()
        OrigimgName = "Kinect_Img-" + time.strftime("%Y%m%d-%H%M%S") + ".png"
        cv2.namedWindow(OrigimgName)
        cv2.imshow(OrigimgName, self._InitFrame)
       
        uiConfirmation = ui2.ConfirmationDialog()
        uiConfirmation.handleButtonPresses("Is this the Image You Want?")
        if uiConfirmation.getResponse():
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
            self.messages.emit("Calibration Complete!\n")
            imgRetrieved = False

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
            message = "No Initilization Frame, press \"Capture\" to capture one"
            self.messages.emit(message)
            #self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, message, self._BgStart, self._BgEnd,
             #                                            self._TextStart)
        


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
                   

            if not self._AllowStartDistanceInit:         
                self.messages.emit("Press \"Get Start Distance\" to get Start Distance")                                
            
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
                if self.currentDistance >= self._BeginMeasurementZone_mm and self.currentDistance <= self._EndMeasurementZone_mm:
                    if self._find_min(x_Cent, width, y_Cent, height) >= self._BeginMeasurementZone_mm:
                        self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, "Measurement Zone Entered!",
                                                                 self._BgStart, self._BgEnd, self._TextStart)
                        # Start The Timer 
                        if not self._TimerMeasure.isTimerStarted(): 
                            self._TimerMeasure.starTtimer(verbose=False) 

                        # Debug Print 
                        if self._BegZoneReached is False: 
                            print("----------------------------------------")
                            print("Patient Entered Measruement Zone")
                            print("----------------------------------------\n")
                            self._BegZoneReached = True
                            self.curr_Distance_measure_zone = self.currentDistance
                
                # Here's a Tricky part, we need to make sure that this is rlly the endpoint, or at least very close to it, before we
                # Pause the program
                elif self.curr_Distance_measure_zone >= self._EndMeasurementZone_mm:
                    # Lets check to see if this rlly is the true end point
                    distance = self._find_min(x_Cent, width, y_Cent, height) - self._BeginMeasurementZone_mm
                    if distance >= self._EndMeasurementZone_mm:
                        self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, "Patient Has Reached Enpoint! Press \"c\" to get gait speed",
                                                                        self._BgStart, self._BgEnd, self._TextStart)
                        self._PAUSE, self._EndReached = True, True
                        self._AllowDataCollection = False 
                # End broken code block
                if self._BegZoneReached: 
                    self.curr_Distance_measure_zone = self.currentDistance - self._BeginMeasurementZone_mm
                    #self._debugCntr += 1
                    #if self._debugCntr % 15 == 0:
                      #  print(self.curr_Distance_measure_zone, self.currentDistance)

            else: 
                self.messages.emit("Press \"Start\" to Start Gait Tracking")
                #self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, "Press \"s\" to Start Gait Tracking", 
                 #                                           self._BgStart, self._BgEnd, self._TextStart)


    # Now we want to do gait speed calculations 
    def doGaitSpeedCalc(self): 
        if self._CalculationsAllowed is False: 
            return 

        # Stop The Timers         
        self._Timer.endTimer()
        self._TimerMeasure.endTimer()
        

        self._EndReached, self._CalculationsAllowed = True, False 
        self._AllowDataCollection = False
        self._TimeTakenToWalk = self._TimerMeasure.getTimeDiff()

        # Now Perform Calculations 
        if self._TimeTakenToWalk > 0: 
            try: 
                self._Gait_Speed = float((self._EndMeasurementZone_mm/self._UnitConversionFactor) / self._TimeTakenToWalk)
            except ZeroDivisionError: 
                assert("No Data to Calculate Gait Speed Provided!!")
            # Append gait speed to the arr to be averaged, and then emit a signal to the ui to allow another program run
            self.gait_Speed_Arr.append(self._Gait_Speed)
            self.programRuntimes += 1 
            self.labelRuntimes += self.programRuntimes + 2
            self.aRunTimeComplete, self.calculationsDone = True, True 
            

        

    # Closing Program Function 
    def reportGait(self): 
        
        # Display Stats 
        if self._EndReached is True and self._CalculationsAllowed == False: 
            
            '''
            if not self.plot.isListEmpty():  
                self._ptLog.output(2,"------------------------------------")
                self._ptLog.output(2, "   Array Format of Current Data:   ") 
                self._ptLog.output(2,"------------------------------------")
                self._ptLog.output(2, "\n")
                self._ptLog.output(2, "X-Plot Points (Distances)" + str(self.plot.x_Points))
                self._ptLog.output(2, "Y-Plot Points (Speed)" + str(self.plot.y_Points))
                self._ptLog.output(1, "\n\n")
            '''

            self._CalculationsAllowed = True 
            self.doGaitSpeedCalc()
        
        self._ptLog.output(2,"\n\n------------------------------------")
        self._ptLog.output(2, "          Statistics:              ") 
        self._ptLog.output(2,"----------------------------------------")
        if self._EndReached is True: 
            self._ptLog.output(2,"Starting Distance: " + str(self._StartDistance))
            self._ptLog.output(2,"Program Time Elapsed: " + str(self._Timer.getTimeDiff()))
            self._ptLog.output(2,"Elapsed Time: " + str(self._TimeTakenToWalk))
            self._ptLog.output(2,"Calculated Gait Speed: " + str(self._Gait_Speed) + " m/s")


    def debugDictPrint(self, dictionary): 
        self._programLog.output(3, "\n\n")
        for x, y in dictionary.items(): 
            for i, data in enumerate(y):
                self._programLog.output(3, f"{i + 1} : {data}")


    
    def averageDict(self):
        
        currentIVHolder, currentTimeHolder, currDistance = 0,0,0
        #{ key: [{}] }
        data = self.iV_Dict[self._StartKey]
        
        # -> Note that data is currently a list of dicts
        # Iterate through each element in this list of dicts, and then grab the currIV 
        for j ,items in enumerate(data): # -> var 'items' should be a dictionary
            currentIVHolder = items['currIV']
            currentTimeHolder = items['CurrTime']
            currDistance = items['distance_Measure']
            if len(list(self.iV_Dict)) > 1: # Only iterate through if there is more than one program run time of the same patient
                
                # Now I need to loop through all the other keys and element that is equal to the current element index
                for keys in range(self._StartKey+1, self.labelRuntimes+1):
                    if keys in self.iV_Dict: 
                        # Get the Instant Velocities Average for current distance
                        currentIVHolder += self.iV_Dict[keys][j]['currIV']
                        # Get the Time Averages for current distance
                        currentTimeHolder += self.iV_Dict[keys][j]['CurrTime']  
                # Dict average structure
                # "Results": [{Distance: 3, Instant Velocity: 0.75, Time: 2}, {Distance: 3, Instant Velocity: 0.75, Time: 2}]
                currentIVHolder /= len(list(self.iV_Dict))
                currentTimeHolder /= len(list(self.iV_Dict))

            if "Results" in self._IV_Dict_Averages:
                self._IV_Dict_Averages['Results'].append({'Distance' : currDistance,'Time': currentTimeHolder, 'Instant Velocity': currentIVHolder})
            else: 
                self._IV_Dict_Averages.update({'Results': [{'Distance': currDistance, 'Time': currentTimeHolder, 'Instant Velocity': currentIVHolder}]})


        print(self._IV_Dict_Averages, end="\n\n\n")     

    def saveToDatabase(self):
        dataArr = self._IV_Dict_Averages["Results"] # var dataArr Holds the array of dicts 
        distancesArr, ivArr, timeArr = [], [], []
        for items in dataArr:
            distancesArr.append(round(items['Distance'], 4))
            timeArr.append(round(items['Time'], 4))
            ivArr.append(round(items['Instant Velocity'], 4))
            

        self._Database.uploadResults((self._PatientID, self._PatientName),distancesArr, timeArr, ivArr, round(self._Gait_Speed_Avg, 4), None)
            



    reportProgDone = pyqtSignal(float)
    def programFinished(self): 
        # Run Gait Speed Avg Calculations
        if len(self.gait_Speed_Arr) > 0: 
            self._Gait_Speed_Avg = sum(self.gait_Speed_Arr)
            self._Gait_Speed_Avg /= len(self.gait_Speed_Arr)
            self._ptLog.output(2,"\n\n---------------------------------------------")
            self._ptLog.output(2, f"Average Gait Speed: {self._Gait_Speed_Avg}") 
            self._ptLog.output(2,"---------------------------------------------")
            self._programLog.output(2, self.iV_Dict)
            # Now Calculate the Average Instant Vel and time at Each Distance
            self.averageDict()
            # Now upload the data to the database
            self.saveToDatabase()
            # Debug Print the Average For Now
            self.debugDictPrint(self._IV_Dict_Averages)

        self.closeFiles()
        if len(self.gait_Speed_Arr) > 0: 
            self.reportProgDone.emit(round(self._Gait_Speed_Avg, 4))
        else: 
            self.reportProgDone.emit(-1)



    def closeFiles(self): 
        self._programLog.closeFile()
        self._ptLog.closeFile()






