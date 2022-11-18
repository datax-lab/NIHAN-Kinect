# Pykinect Library imports
from Resources.pykinect2 import PyKinectV2
from Resources.pykinect2 import PyKinectRuntime

# General Libraries
import os, traceback, time, sys 
import cv2
import numpy as np
# import pandas as pd  
from pandas import DataFrame, concat 

# UI Imports 
from Resources.UIResources import initImageWindow as ui2
# pyQt Imports
from PyQt5.QtCore import QThread, pyqtSignal

# Custom Libraries
from Resources.CVResources import imageEditor as IMPROC
from Resources.GaitResources import timer as Timer
from Resources import Logging as lg
from Resources.GaitResources import graph
from Resources.uploadData import dataUploader

# Debug for now 
_DebugMode = False 
if len(sys.argv) > 1 and sys.argv[1] == "--DEBUG": 
        _DebugMode = True 
       




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
        self._KinectDev = None #PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
        self._Height, self._Width = None, None #self._KinectDev.depth_frame_desc.Height, self._KinectDev.depth_frame_desc.Width
        ######################################################
        #               End Kinect Setup                     #
        ######################################################
 

        ######################################################
        #               Program Constants                    #
        ######################################################
        self._MaxFrameCalibrationCnt = 5
        self.programRuntimes = 0 # So that the current index of the gait speed is the same as the program run times
        self._runTimeCntr = 0 
        # self._runTimeCntr = self.programRuntimes; 
        # Gait Constants
        self._BeginMeasurementZone_mm, self._EndMeasurementZone_mm = 1000, 4000 #0,500 #1000,<- Debug 4000 # Begin Measurement Zone at 1m and end at 4m
        self._UnitConversionFactor = 1000
        # Instant Velocity Constants
        self._DistanceOffset = 304.8 # For now its every 1 foot report
        self._trimDistance = 1.5 # every 1.5 feet to trim data

        # Program Logging and Data Collection 
        self._ProgramPath = os.path.dirname(os.path.abspath(__file__))
        self._programLog, self._ptLog = None, None 

        # Instantiate Image Processing Custom Library
        self._OpenCVDepthHandler = None #IMPROC.CVEDITOR_DEPTH(self._Height, self._Width, "Kinect V2 Gait Analyzer")

        # UI Integrations
        self._FileExplorerSelection = None 
        # Grab Initial Image from a UI
        self._InitImageFileName = None
        self._InitFrame = None # To Hold the Initial Frame, will be used to find what's a foreground object and what's not

        # Message Formats
        self._BgStart, self._BgEnd, self._TextStart = None, None, None #(0, 0), (self._Width, 50), (40, 25)
        ######################################################
        #               End Program Constants                #
        ######################################################
        # Must init in constructor
        self._InitFrameConvted = False # This is to ensure that we conver the image first
        
        
        # Image Processing Vars
        # Now Create Frames For Analysis and Displaying
        #   displayframe -> the frame that will be displayed to the viewfinder
        #   frame -> the internal frame to do calculations with
        #   framedataReader -> The object that will hold the depth frame data (i.e. 3d array of depth data)
        self.displayFrame = None #np.zeros((self._Height, self._Width), np.uint8)
        self.frame, self.frameDataReader = None, None
         
        # Data Plotting
        self.plot, self.plotFlag = None, bool 
        

        # Program Flags
        self.aRunTimeComplete = bool 
        self._PAUSE, self._IsDone, self._BegZoneReached, self._EndReached = bool, bool, bool, bool
        
        self._AllowDataCollection, self._CalculationsAllowed = bool, bool
        self._PictureTaken, self._PictureWindowName = bool, "Saved Image"
        self._startDistanceCaptured = bool 
        # Calibration Var
        self.calibrationFrameCntr = int
        self.calculationsDone = bool
        
        self.wasEmitted = False 
        
        # Error Handling
        self._LastPosition = []

        self.x_Cent, self.y_Cent, self.width, self.height = None, None, None, None

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

        self.plot, self.plotFlag = graph.Graph() , False 



        # Instance Data Frame 
        self.iv_data_frame, self.frame_data_frame = DataFrame, DataFrame
        ######################################################
        #               Instant Velocity                     #
        ######################################################
        # Dictionary to save data
        self.Data_Dict = dict() #  Dictionary = {
                                  # '1': [{'distance_Measure': 15, 'currVelocity': 12, 'CurrTime': 15}, {'distance_Measure': 31, 'currVelocity': 12, 'CurrTime': 70}]
                                  #  } 
        
        # Distance Management 
        self.distanceOffset_Min, self.distanceOffset_Max = float, float
        self.tempIV_Distance_Arr, self.tempIV_Distance_Arr_time, self.searchingForOffset = None, None, bool 

        # Standard Vars 
        self.vf_AccelZone, self.vi_MeasureZone = None, None     
        self.prevDistance = 0 
        self.lastIvCalculated = False 
        self.currDistanceIteration = 0

        ######################################################
        #             End Instant Velocity                   #
        ######################################################

        # Debug Timer 
        self._debugCntr = 0

        # Patient Info 
        self._PatientID, self._PatientName = None, None 
        self._Database = dataUploader() # This will actually be set in the setDataDatabase Function

        # Arrays to Help With Averaging 
        self._IV_Overall, self._IV_time_Overall = [], []

        # Arrays to help with output 
        self._IV_Dict_Averages = {}
        self._IV_Avg_Graph = graph.Graph()
        # To Help With Final Graphing Later
        # self._FrameBFrame_Dict, self._IV_Dict = dict(), dict()
        # Program Setup Functions
        self.setupDirectories()
      
        
        self._DataFrame = DataFrame()
        
    def setupKinect(self): 
        self._KinectDev = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
        self._Height, self._Width = self._KinectDev.depth_frame_desc.Height, self._KinectDev.depth_frame_desc.Width
        
        self._OpenCVDepthHandler = IMPROC.CVEDITOR_DEPTH(self._Height, self._Width, "Kinect V2 Gait Analyzer")
        
        self._BgStart, self._BgEnd, self._TextStart = (0, 0), (self._Width, 50), (40, 25)


   

        
    def setupAvgGraph(self, title): 
        avgFrameDataFrame, avgIVDataFrame = self.__setupAvgGraphHelper()
        self._IV_Avg_Graph.setupLabels(title, 'Distance (m)', 'Speed (m/s)')
        self._IV_Avg_Graph.insertToGraph((avgFrameDataFrame['distance'], avgFrameDataFrame['velocity']), (avgIVDataFrame['distance'], avgIVDataFrame['velocity']), id=1) 
        self.Data_Dict = (concat([avgFrameDataFrame, avgIVDataFrame], axis=0)).to_dict('records')
        
        if _DebugMode: 
            avgIVDataFrame.to_csv('iv_averages.csv')
            avgFrameDataFrame.to_csv('frame_averages.csv')
    
    
    # {'Results': [{'Distance': currDistance, 'Time': currentTimeHolder, 'Instant Velocity': currentIVHolder}]}
    # This Function Also Handles Formatting the Data to be uploaded, since this is where we average all the data
    # Disable for now --> Want to isolate new data structure
    def __setupAvgGraphHelper(self) -> DataFrame: 
        
        # new dataframe to store all the avg values 
        frame_dataframe_avg, iv_dataframe_avg = {}, {}
    
        # Lets calculate averages of iv data
        for i in range(self.iv_data_frame['distance_ID'].max() + 1): 
            templist = self.iv_data_frame.loc[self.iv_data_frame['distance_ID'] == i]
            if len(iv_dataframe_avg) == 0: 
                iv_dataframe_avg = {
                    'type' : [], 
                    'time' : [],
                    'distance' : [], 
                    'velocity' : []
                }
            iv_dataframe_avg['type'].append('Instant Velocity')
            iv_dataframe_avg['time'].append(templist['time'].mean())
            iv_dataframe_avg['distance'].append(templist['curr_distance'].mean())
            iv_dataframe_avg['velocity'].append(templist['velocity'].mean())
            
            
        
       # Lets calculate averages of frame data
        minFrameCnt = self.frame_data_frame['frame_ID'].min()
        print(self.frame_data_frame['frame_ID'].max())
        maxFrameCnt = self.frame_data_frame['frame_ID'].max()
        for i in range(minFrameCnt, maxFrameCnt + minFrameCnt, minFrameCnt): 
            templist = self.frame_data_frame.loc[self.frame_data_frame['frame_ID'] == i]
            if len(frame_dataframe_avg) == 0:
                frame_dataframe_avg = {
                    'type' : [], 
                    'time' : [], 
                    'distance' : [], 
                    'velocity' : [], 
                }
            frame_dataframe_avg['type'].append('Frame')
            frame_dataframe_avg['time'].append(templist['time'].mean())
            frame_dataframe_avg['distance'].append(templist['curr_distance'].mean())
            frame_dataframe_avg['velocity'].append(templist['velocity'].mean())
            
        return (DataFrame.from_dict(frame_dataframe_avg)).dropna(), (DataFrame.from_dict(iv_dataframe_avg)).dropna()
      
        # frameData, ivData = self.avgData()
        
        # self._programLog.output(0, f"{frameData.shape, ivData.shape}")
        # self._IV_Avg_Graph.setupLabels(title, "Distance (m)", "Speed (m/s)")
        # self._IV_Avg_Graph.insertToGraph((frameData['distance'], frameData['velocity']), (ivData['distance'], ivData['velocity']), 1)
        
        # # Since we should be done w the original dict, we need to clear it, and then re-create it for data uploading
        # self.Data_Dict.clear()
        # # Format of Gait Dictionary
        # #[
        # #   {
        # #         'Type' : , # This is indicates whether the current results are from Frame By Frame or Instant Velocity 
        # #         'Time' : , 
        # #         'Distance' : , 
        # #         'Velocity' : , 
        # #   }
        # # ]
        # self.Data_Dict = (pd.concat([frameData, ivData], axis=0)).to_dict('records')
        # #self.Data_Dict = (frameData.append(ivData)).to_dict('records')
        
        # self._programLog.output(0,f"\n Frame By Frame Average Data:\n{frameData}")
        # self._programLog.output(0, f"\nInstant Velocity Average Data:\n{ivData}")
    
    # Disable for now --> Want to isolate new data structure
    def displayAvgGraph(self, id=1): 
        # Only Allow Graph to Be Shown if There is Data, otherwise it will crash if there isnt a check for data
        if(len(self.gait_Speed_Arr) > 0):
            self._IV_Avg_Graph.showGraph(id, showLegendBool=True, average=self._Gait_Speed_Avg, customText="Averages For")



    def processNParition(self, aDict : DataFrame) -> tuple[dict, dict]: 
        # Convert all the data into m/s
        aDict['distance_Measure'] = aDict['distance_Measure'].div(self._UnitConversionFactor)
        # Now Partition Data into a Frame By Frame and instant velocity for easy graphing 
        return (aDict[aDict['id'] == 'Frame']).to_dict('records'), (aDict[aDict['id'] == 'IV']).to_dict('records') 
    
    
    # When inserting the data to the graph, we should first have the frame-by-frame and the iv data from the child class appended to the 
    # currrent instance pd.Dataframe
    def copyToDataFrame(self, iv_store : dict, frame_store : dict): 
        
        if(self.iv_data_frame.empty) : self.iv_data_frame = self.removeNoise(DataFrame.from_dict(iv_store))
        else: self.iv_data_frame = concat([self.iv_data_frame, self.removeNoise(DataFrame.from_dict(iv_store))], axis=0)
        
        if(self.frame_data_frame.empty) : self.frame_data_frame = self.removeNoise(DataFrame.from_dict(frame_store))
        else: self.frame_data_frame = concat([self.frame_data_frame, self.removeNoise(DataFrame.from_dict(frame_store))], axis=0)
        
        
    def getCurrIterationData(self) -> DataFrame: 
        '''Gets all captured frame measurements and iv measurements of the current iteration of the program for a patient'''
        return (self.frame_data_frame.loc[self.frame_data_frame['iteration_ID'] == self._runTimeCntr], 
                self.iv_data_frame.loc[self.iv_data_frame['iteration_ID'] == self._runTimeCntr])
    
       
        
    # Now that we have copied all data to a dataframe lets append it to the graph, altho this should prolly only be done if requested 
    # to save resources --> Implement later
    def insertGraphData(self, title): 
        self.plot.setupLabels(title, 'Distance (m)', 'Speed (m/s)')
        #  tempIV_dict.loc[tempIV_dict['distanceID'] == i
        currFrameData, currIVData = self.getCurrIterationData()
        self.plot.insertToGraph((currFrameData['curr_distance'], currFrameData['velocity']), 
                                (currIVData['curr_distance'], currIVData['velocity']), int(self._runTimeCntr))
       
    
 
    # Disable graphing --> Temporary to test only new structure of the data gathered
    def displayGraph(self, id=None, showLegend=True): 
        if(len(self.gait_Speed_Arr) > 0) and id != -1: 
            self.plot.showGraph(id=self._runTimeCntr - 1, showLegendBool=showLegend)
        elif id == -1: # Tells program to show average graph
            self.plot.showGraph(id=None, showLegendBool=showLegend)
    
        # if(len(self.gait_Speed_Arr) > 0 ): 
        #     if id == None: 
        #         self.plot.showGraph(id=self._currKey-1, showLegendBool=showLegend)
        #     elif id == -1: 
        #         self.plot.showGraph(showLegendBool=showLegend)
            

    
    def setDatabaseInstance(self, database): 
        self._Database = database
        
    def setPatientInfo(self, ptInfo): 
        self._PatientID, self._PatientName = ptInfo


    def setupDirectories(self):
        # Just wrap in a try and except to catch all errors
        try:  
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
        
        except Exception as e: 
            print(f"There was an error: {e}")
        



    exitSignal = pyqtSignal(bool) 
    def programStartup(self): 
        self._FileExplorerSelection = ui2.FileDialog()
        self._FileExplorerSelection.handleButtonPresses()
        self._InitImageFileName = self._FileExplorerSelection.getFileName()
        # If Exit Was Pressed Send the Exit Program Signal
        if self._InitImageFileName == "PROGEXIT": 
            self.exitSignal.emit(True)
        else: 
            self.setupKinect()
            self._reinit()



    # This function is meant to be a helper function for gait.py::fullReset(), gait.py::ProgramStartup(), and for gaitRuntime.py::reset(); 
    # this performs the reinitilization that allows for multiple runs on the same patient, but when used with fullReset() will allow for 
    # the "switch user" and "logout" functionality to work properly
    def _reinit(self): 
        self.displayFrame = np.zeros((self._Height, self._Width), np.uint8)
        self.frame, self.frameDataReader = None, None
        self.plotFlag = False 

        # Program Flags
        self._PAUSE, self._IsDone, self._BegZoneReached, self._EndReached = False, False, False, False
        
        self._AllowDataCollection, self._CalculationsAllowed = False, False
        self._PictureTaken, self._PictureWindowName = False, "Saved Image"
        self._startDistanceCaptured = False 
        # Calibration Var
        self.calibrationFrameCntr = 0

      

        # Gait Speed Flags
        self._Timer, self._TimerMeasure = None, None
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
        self.tempIV_Distance_Arr, self.tempIV_Distance_Arr_time, self.searchingForOffset = {}, [], False

        self.vf_AccelZone, self.vi_MeasureZone = None, None 
        
        self.prevDistance = 0 
        self.lastIvCalculated = False 
        self.currDistanceIteration = 0
        
        # GUI Signal to continue program 
        self.calculationsDone = False 
        
        # We want to increment this, since this would indicate we are running the program again on the same patient, it is used 
        # to help identify which graph to display 
        # self._runTimeCntr = self.programRuntimes




    # This function allows the program to completely reset itself and allow for the "switch patient " functionality to work
    # This should be called in the gaitRuntime.py::reset(resetAllBool : bool) when the resetAllBool is set to True 
    def _fullReset(self): 
        # Clear the init frame
        self._InitFrame, self._InitImageFileName, self._InitFrameConvted = None, None, False 
        self.Data_Dict = dict()
        self._IV_Dict_Averages = {}
        self._IV_Avg_Graph = graph.Graph()
        self.wasEmitted = False
        self.frame_data_frame = DataFrame
        self.plot = graph.Graph()
        self.iv_data_frame = DataFrame
        self._runTimeCntr = 0
        # To Help With Final Graphing Later
        # self._FrameBFrame_Dict, self._IV_Dict = dict(), dict()
        self._reinit()


    def handleNewDepthFrames(self) -> np.ndarray:
        if self._KinectDev.has_new_depth_frame():
            self.frame, self.frameDataReader = self._KinectDev.get_last_depth_frame(), self._KinectDev._depth_frame_data
            self.displayFrame, self.frame = self._OpenCVDepthHandler.convtImg(self.frame)
        else: 
            self.frame = None 

        return self.frame # We do a return here, cause we will alsol use this function to find the person's starting
                       # from the camera, along with capturing an init frame
        
    


    # Functions to be called in functions
    
    # Find min allows me to check all points within the rectangle area to confirm the patient has reacehd the end zone, since the kinect may at times 
    # stop the program earlier than its supposed to. 
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

        # If an init image file was selected, convert and use it, since the file image should alreday be in the proper format
        # We just need to grayscale and read it
        if self._InitImageFileName is not None:
            self._InitFrame = cv2.imread(self._InitImageFileName)
            self._InitFrame = cv2.cvtColor(self._InitFrame, cv2.COLOR_RGB2GRAY)
            self._InitFrameConvted = True
        # if we just took an init image, then we must do all the conversion to make it a standard picture
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

        else:
            self._InitFrame = None
            cv2.destroyWindow(OrigimgName)
            


    def handleNoInitFrame(self):
        if self.displayFrame is None: 
            return 
        
        # If we have no init image display a message asking to capture one
        if self._InitFrame is None and self._InitFrameConvted is False:
            # Print The Error, and display message to capture an init frame 
            message = "No Initilization Frame, press \"Capture\" to capture one"
            self.messages.emit(message)
            
            

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
            self.x_Cent, self.y_Cent, self.width, self.height = self._OpenCVDepthHandler.getObjectMidPoint(self._InitFrame, self.frame,
                                                                                       self.displayFrame)
            x_Cent, y_Cent, width, height = self.x_Cent, self.y_Cent, self.width, self.height
            

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
                            self._TimerMeasure.starTtimer() 

                        # Debug Print 
                        if self._BegZoneReached is False: 
                            self._BegZoneReached = True
                            self.curr_Distance_measure_zone = self.currentDistance
                
                # Here's a Tricky part, we need to make sure that this is rlly the endpoint, or at least very close to it, before we
                # Pause the program
                elif self.curr_Distance_measure_zone >= self._EndMeasurementZone_mm:
                    # Lets check to see if this rlly is the true end point
                    distance = self._find_min(x_Cent, width, y_Cent, height) - self._BeginMeasurementZone_mm
                    #distance = self.curr_Distance_measure_zone
                    if distance >= self._EndMeasurementZone_mm:
                        self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, "Patient Has Reached Enpoint!",
                                                                        self._BgStart, self._BgEnd, self._TextStart)
                        self._PAUSE, self._EndReached = True, True
                        self._AllowDataCollection = False 
    
                if self._BegZoneReached: 
                    self.curr_Distance_measure_zone = self.currentDistance - self._BeginMeasurementZone_mm
                    #self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, f"Distance: {self.curr_Distance_measure_zone}",
                    #                                               self._BgStart, self._BgEnd, self._TextStart)
                   
                   

            else: 
                self.messages.emit("Press \"Start\" to Start Gait Tracking")
                #self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, "Press \"s\" to Start Gait Tracking", 
                 #                                           self._BgStart, self._BgEnd, self._TextStart)



    def removeNoise(self, aDataFrame : DataFrame):
         '''Takes a given dataframe (must have the standard keys that have been set in this program) and removes all outliers'''
         q3, q1 = np.quantile(aDataFrame['velocity'], 0.75), np.quantile(aDataFrame['velocity'], 0.25) 
         iqr = (q3 - q1) * 1.5 
         innerFenceL,innerFenceU = q1 - iqr, q3 + iqr
         return aDataFrame.loc[(aDataFrame['velocity'] > innerFenceL) & (aDataFrame['velocity'] < innerFenceU)]
         
         
    # def removeNoise(self): 
    #     currFrameData, currIVData = self.getCurrIterationData()
        

        

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
            self._runTimeCntr += 1
            self.aRunTimeComplete, self.calculationsDone = True, True 
                

    

    # Closing Program Function 
    def reportGait(self): 
        
        # Display Stats 
        if self._EndReached is True and self._CalculationsAllowed == False: 
            self._CalculationsAllowed = True 
            if not self.frame_data_frame.empty and not self.iv_data_frame.empty: 
                self.insertGraphData("Kinect Gait Analysis")
            self.doGaitSpeedCalc()
            
            
        
        # Log only if we r in debug mode
        if(len(sys.argv) > 1 and sys.argv[1] == "--DEBUG"):
            self._ptLog.output(2,"\n\n------------------------------------")
            self._ptLog.output(2, "          Statistics:              ") 
            self._ptLog.output(2,"----------------------------------------")
            if self._EndReached is True: 
                self._ptLog.output(2,"Starting Distance: " + str(self._StartDistance))
                self._ptLog.output(2,"Program Time Elapsed: " + str(self._Timer.getTimeDiff()))
                self._ptLog.output(2,"Elapsed Time: " + str(self._TimeTakenToWalk))
                self._ptLog.output(2,"Calculated Gait Speed: " + str(self._Gait_Speed) + " m/s")
        





    # def debugDictPrint(self, dictionary, label=None):
    #     self._programLog.output(1, "\n\n")
    #     if label is not None: 
    #         self._programLog.output(1,label)
    #     for x, y in dictionary.items(): 
    #         print(f"\nCurrent Key Val: {x}")
    #         for i, data in enumerate(y):
    #             self._programLog.output(1, f"{i + 1} : {data}")
    #         # Save this data as a dataframe
    #         if self._DataFrame is None: 
    #             self._DataFrame = DataFrame.from_dict(y)
    #         else: 
    #             self._DataFrame = self._DataFrame.append(DataFrame.from_dict(y))
        


    # def debugDictPrint2(self, dictionary, label=None):
    #     sum = 0
    #     cntr = 0
    #     self._programLog.output(1, "\n\n")
    #     if label is not None:
    #         self._programLog.output(1,label)
    #     for x, y in dictionary.items():
    #         for i, data in enumerate(y):
    #             self._programLog.output(1, f"{i + 1} : {data}")
    #             sum += data['Instant Velocity']
    #             cntr +=1

    #     self._programLog.output(1, f"\nAverage of Instant Velocities: {sum/cntr}")


   

    def getCurrGaitSpd(self): 
        return self.gait_Speed_Arr[self.programRuntimes - 1]
        
    
        
    # This function takes the dictionary that holds all the results and re-structures the results dictionary to make it appropriate for the 
    # database it will be uploaded to
    def saveToDatabase(self):
        self._Database.uploadGaitResults((self._PatientID, self._PatientName), self.Data_Dict, self._Gait_Speed_Avg)   
      
            

    reportProgDone = pyqtSignal(float)
    def programFinished(self): 
        # Run Gait Speed Avg Calculations
        if len(self.gait_Speed_Arr) > 0: 
            self._Gait_Speed_Avg = sum(self.gait_Speed_Arr)
            self._Gait_Speed_Avg /= len(self.gait_Speed_Arr)
            # Now Calculate the Average Instant Vel and time at Each Distance
            self.setupAvgGraph("Average Graph")
            # Now upload the data to the database
            if(len(sys.argv) > 1 and sys.argv[1] == "--DEBUG"):
                self.iv_data_frame.to_csv('iv_data.csv')
                self.frame_data_frame.to_csv('frame_data.csv') 
            else: 
                self.saveToDatabase()

            # if(len(sys.argv) > 1 and sys.argv[1] == "--DEBUG"):
            #     self._ptLog.output(2,"\n\n---------------------------------------------")
            #     self._ptLog.output(2, f"Average Gait Speed: {self._Gait_Speed_Avg}") 
            #     self._ptLog.output(2,"---------------------------------------------")
            #     # Debug Calls 
            #     self._programLog.output(0, "Dictionary Format of Data:\n")
            #     self._programLog.output(0, self.Data_Dict)
            #     # End Debug
            
            
          
            #self.debugDictPrint2(self._IV_Dict_Averages, label="Averages")
            

        self.closeFiles()
        if len(self.gait_Speed_Arr) > 0: 
            self.reportProgDone.emit(round(self._Gait_Speed_Avg, 4))
        else: 
            self.reportProgDone.emit(0)
        self._KinectDev.close()


    def closeVid(self): 
        self._OpenCVDepthHandler.closeAllWindows()
        
    def closeFiles(self): 
        self._programLog.closeFile()
        self._ptLog.closeFile()






