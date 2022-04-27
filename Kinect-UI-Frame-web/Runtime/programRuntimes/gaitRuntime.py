# Regular Librarires 
import os, time, cv2
import pandas as pd 
# Import the class to inherit
from Resources.GaitResources import gait

# Pyqt Impoorts 
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import *
from PyQt5.QtWidgets import * 


class GaitAnalyzer(gait.GAIT): 
    # Pyqt Signals
    signalShowControlWindow = pyqtSignal(str)
    signalAllowStartDistanceCapture = pyqtSignal(bool)
    
    def __init__(self): 
        
        gait.GAIT.__init__(self)
        
        self._ProgramPath = os.path.dirname(os.path.abspath(__file__))
        self._ProgramPath = os.getcwd()

        # QThread Flags
        self.threadRunning = True 
        self.wasEmitted = False 
        

        ##### Frame By Frame #####
        # Program Counter
        self.currMeasureCnt = 0
        
        # Frame by Frame Analysis Constants 
        self._FramesToRead = 5
        self._FrameRate = 30 
        self._FrameConst = (self._FramesToRead/self._FrameRate)
        self._lenConvFactor = 1000 # divide by this to get meters
        

        #
        self.currFrame = None
        self.currFrameCnt, self.prevFrameCnt = 0, 0 
        self.prevDistanceFrameBFrame = 0
        self.frameSpdsDict = {}
        


    def find_min_from_max_Frame(self, smallest):
        x_Curr_Cent, y_Curr_Cent, w_Curr, h_Curr = self.x_Cent, self.y_Cent, self.width, self.height

        distanceArr = []
        if w_Curr is None or h_Curr is None:
         x_Curr_Cent, w_Curr, y_Curr_Cent, h_Curr = self._LastPosition

        for x in range(x_Curr_Cent-w_Curr, x_Curr_Cent+w_Curr):
            for y in range(y_Curr_Cent-h_Curr, y_Curr_Cent + h_Curr):
                distance =self._OpenCVDepthHandler.getDepth(self.frameDataReader, x,y) - self._StartDistance
                if (distance - smallest) > 0:
                    distanceArr.append(distance)

        distance = sorted(distanceArr)
        if len(distanceArr) > 0:
            return distanceArr[0]
        else:
            return 0

    def reset(self):
        self.currMeasureCnt = 0 
        self.currFrameCnt, self.prevFrameCnt = 0, 0 
        self.prevDistanceFrameBFrame = 0
        self.frameSpdsDict = dict()
        self.resetProgram()
    
    
    def frameByFrame(self):
        # Should Only Be Running In The Measurement Zone
        if not self._BegZoneReached or self._EndReached or self.frameDataReader is None:
            return

        
        currDistance = self.curr_Distance_measure_zone
        currTime =  self._TimerMeasure.getCurrentTimeDiff()
        frameCntdiff = self._FramesToRead
        
        # Check if curr distance is less than prev
        # If it is find the smallest point that results in a positive difference
        if currDistance - self.prevDistanceFrameBFrame < 0:
            currDistance = self.find_min_from_max_Frame(self.prevDistanceFrameBFrame)
        # Get Our Current Speed, and The Current Time to Append To Dict
        try:
            currSpd = float(((currDistance - self.prevDistanceFrameBFrame) / self._UnitConversionFactor) / self._FrameConst)
        except Exception as err: 
            self._programLog.output(3, "There was an error in frameBFrame:")
            self._programLog.output(3, f"{frameCntdiff/self._FrameRate}")
            self._programLog.output(3, f"{currDistance-self.prevDistanceFrameBFrame}")
            exit(-1)
        # Save the Data to Our Dictionary
        self.frameSpdsDict.update(
            {self.currMeasureCnt:
                 {"CurrSpd": currSpd, "CurrTime": currTime,
                  "CurrDistance": currDistance,
                  "PrevDistance": self.prevDistanceFrameBFrame,
                  "CurrFrameCnt" : self.currFrameCnt, 
                  "PrevFrameCnt" : self.prevFrameCnt
                  }
             }
        )
        #self._saveToDict(self.frameSpdsDict[self.currMeasureCnt]['CurrSpd'], self.frameSpdsDict[self.currMeasureCnt]['CurrDistance'], self.frameSpdsDict[self.currMeasureCnt]['CurrTime'])
        # Update Previous Distance, since we are done with it
        self.prevDistanceFrameBFrame, self.prevFrameCnt = currDistance, self.currFrameCnt
        self.currMeasureCnt += 1


    def debugPrintDict(self, comment=None):
        if len(list(self.frameSpdsDict)) < 1: 
            self._programLog.output(3, "There is no data in the frame by frame Dictionary!")
            return  
        dicSum = []
        if not comment is None: 
            self._programLog.output(3, f"Debug Frame By Frame Print -> {comment}")
        else: 
            self._programLog.output(3, f"Debug Frame By Frame Print")
        for x,y in self.frameSpdsDict.items():
            self._programLog.output(3, f"{x} : {y}")
            dicSum.append(y['CurrSpd'])
        
        self._programLog.output(3, f"Average of Frame: {sum(dicSum)/len(dicSum)}\n")
        
        if self._Gait_Speed is not None: 
            self._programLog.output(3, f"Calculated Average Velocity: {self._Gait_Speed}")




    def removeNoise(self): 
        tempList = list()
        listOfPops = list()
        
        for keyVal, data in self.frameSpdsDict.items(): 
            tempList.append(data['CurrSpd'])
            if data['CurrDistance'] > self._EndMeasurementZone_mm:      
                listOfPops.append(keyVal)
          
           
        tempList = pd.DataFrame(tempList)
        tempList = tempList.quantile([0.25,0.5,0.75])
        
        
        iqr = (tempList.loc[0.75,0] - tempList.loc[0.25,0]) * 1.5 
        innerFenceL, innerFenceU = tempList.loc[0.25, 0] - iqr, tempList.loc[0.75, 0] + iqr 
        
        # Debug Prints
        self._programLog.output(2, f"Quantile 1: {tempList.loc[0.25,0]} Median: {tempList.loc[0.5,0]} Quantile 3: {tempList.loc[0.75,0]}")
        self._programLog.output(2, f'Lower Inner Fence: {innerFenceL} Median: {tempList.loc[0.5,0]} Upper Inner Fence: {innerFenceU}')
        
        
       
        for keyVal, data in self.frameSpdsDict.items(): 
            currVel = data['CurrSpd']
            if currVel < innerFenceL or currVel > innerFenceU: 
                listOfPops.append(keyVal)

        
        self._programLog.output(2, f"\nDeletions: {listOfPops} ") 
        for item in listOfPops: 
            if item in self.frameSpdsDict:
                del self.frameSpdsDict[item]
        
        self._savetoDict2(self.frameSpdsDict)
        
                 
    def _savetoDict2(self, aDict : dict() ): 
        # Current Program Run
        keyVal = self._currKey 
        
        for y in aDict.values(): 
            iVelocity, distance = y['CurrSpd'], y['CurrDistance']
            time, frameCntr =  y['CurrTime'], y['CurrFrameCnt']
            if keyVal in self.Data_Dict: 
                self.Data_Dict[keyVal].append({'currVelocity': iVelocity, 'distance_Measure': distance, 'CurrTime': time, 'id' : 'Frame', 'frame' : frameCntr, 'distanceID' : None})
            else: 
                self.Data_Dict.update({keyVal: [{'currVelocity': iVelocity, 'distance_Measure': distance, 'CurrTime': time, 'id' : 'Frame', 'frame' : frameCntr, 'distanceID' : None}]})
           
         
                

#####################################################   
#               Instant Velocity                    #
#####################################################

 # vf = [(deltaX(in meters) * 2)/time (in sec)] - vi
    # vi will always equal vf_AccelZone
    # Should return velocity in m/s 
    def _instantVelocityHelper(self, aDistance, currTime, vInital) -> float: 
        
        aDistance = aDistance/self._UnitConversionFactor # Convert from mm to m 
        
        return float(((aDistance * 2)/currTime) - vInital)

    def _findBestDistanceToOffset(self) -> tuple: 
        
        if len(self.tempIV_Distance_Arr) == 0:
            return None, None

        #distance, time = list(sorted(self.tempIV_Distance_Arr))[0], list(sorted(self.tempIV_Distance_Arr.values()))[0]
        
        distance = list(sorted(self.tempIV_Distance_Arr.keys()))[0]
        time, frameCnt = self.tempIV_Distance_Arr[distance]['Time'], self.tempIV_Distance_Arr[distance]['FrameCnt']
        
        #self._programLog.output(2, f"TempIV Array:\n{self.distanceOffset_Min} : {self.tempIV_Distance_Arr}\n")

        # Clear the Arrays since we should be done with them at this point
        self.tempIV_Distance_Arr.clear()
        self.instantVelocityCalculated = True
        return distance, time, frameCnt

    def _saveToDict(self, iVelocity, distance, time): 
        if self.lastIvCalculated is True: #or self.prevDistance == round(distance,0):
             return 
        elif (self._DistanceOffset + self.distanceOffset_Min) > self._EndMeasurementZone_mm:
            self.lastIvCalculated = True # Calculate the distance at 3942, then don't do anything else
        

        self.prevDistance = round(iVelocity, 0)

        keyVal = self._currKey
    
        if keyVal in self.Data_Dict:
            self.Data_Dict[keyVal].append({'currVelocity': iVelocity, 'distance_Measure': distance, 'CurrTime': time, 'id' : 'IV', 'frame' : None, 'distanceID' : int(self.distanceOffset_Min)})
        else: 
            self.Data_Dict.update({keyVal: [{'currVelocity': iVelocity, 'distance_Measure': distance, 'CurrTime': time, 'id' : 'IV', 'frame' : None, 'distanceID' : int(self.distanceOffset_Min)}]})




    def _iVHelper2(self, distanceVar, timeVar=None) -> float: 
        distance, time = distanceVar, self._TimerMeasure.getCurrentTimeDiff()
        if timeVar is not None:
            time = timeVar
        iVelocity = self._instantVelocityHelper(distance, time, self.vi_MeasureZone)
        self._saveToDict(iVelocity, distance, time)
        return float(iVelocity)


    def calculateInstantVelocity(self): 
        
        if self._BegZoneReached is False or self.lastIvCalculated or self.frame is None :
            return 
        elif self.vf_AccelZone is None: 
            distance, time = self._BeginMeasurementZone_mm, self._Timer.getCurrentTimeDiff()
            self._programLog.output(2, f"Reached Measurement Zone at: {time} sec")
            self.vf_AccelZone = self._instantVelocityHelper(distance, time, 0)
            self.vi_MeasureZone = self.vf_AccelZone
            self._programLog.output(2, f"Initial Velocity: {self.vi_MeasureZone}")
            self._saveToDict(0, 0, 0)
            return 
        
        # Now to actually handle instant velocities at each (of this moment) 1 ft 
        '''if round(self.curr_Distance_measure_zone, 0) % self._DistanceOffset == 0:
            self._iVHelper2(self.curr_Distance_measure_zone)
            self.prevDistance = round(self.curr_Distance_measure_zone, 0)
            #self.searchingForOffset = False 
        '''
        if self.curr_Distance_measure_zone > self.distanceOffset_Min and self.searchingForOffset is False:
            
            self.searchingForOffset = True 

        elif self.curr_Distance_measure_zone > self.distanceOffset_Max and len(self.tempIV_Distance_Arr) == 0: # Check that we didnt skip the value at the current min distance, if we did do calcs
            
            self._iVHelper2(self.distanceOffset_Min)

        elif self.curr_Distance_measure_zone >= self.distanceOffset_Max:
            self.searchingForOffset = False 
            distance, time, frameCnt = self._findBestDistanceToOffset()
            #self.frameByFrame(distance, time, frameCnt)
            if distance is not None and time is not None:
                self._iVHelper2(distance, time)
               
        

        if not self.searchingForOffset and self.curr_Distance_measure_zone >= self.distanceOffset_Max:
            if ((self._DistanceOffset + self.distanceOffset_Min) < self._EndMeasurementZone_mm): 
                self.distanceOffset_Min = self.distanceOffset_Max
                self.distanceOffset_Max = self.distanceOffset_Max + self._DistanceOffset
        elif self.searchingForOffset:
            self.tempIV_Distance_Arr.update({self.curr_Distance_measure_zone: {'Time' : self._TimerMeasure.getCurrentTimeDiff(), 'FrameCnt' : self.currFrameCnt}})





    def finishUp(self) -> bool: 
        #self.debugPrintDict(comment="NO DELETIONS")
        self.removeNoise()
        self.reportGait()
        self.programCanContinue.emit(True)
        #self.debugPrintDict()
        return False

         
   


    def runtime(self): 
        self.programStartup()
        

        # Just some local variables to make things easier down the road
        # Used just for an output statement to only be printed once
        measurementZoneReached = False 

        self.threadRunning = True 
        signalStartDistanceSent = False 
        

        # If supplied an initial image, convert from RGB to Gray, removing the third element of the tuple 
        if self._InitImageFileName is not None:
            self._convt_init_img()
            self.signalAllowStartDistanceCapture.emit(True)

        while not self._IsDone:
            
            if self._PAUSE is False and self._EndReached is False: 
                self.handleNewDepthFrames()
                self.currFrame = self.frame
            
            # For Accurate Measurment within the measuremenmt zone, set a timer to start once the pt reaches the begin measurement zone 
            #if self._TimerMeasurementZone.isTimerStarted() is False and self._BegZoneReached is True: 
            #    self._TimerMeasurementZone.starTtimer(verbose=True)

            # Opencv Requires This Otherwise Program Freezes 
            keypress = cv2.waitKey(1) & 0xFF
            if keypress == ord('q') and False: 
                exit(0)

            if self._InitFrame is None and self._InitFrameConvted is False:
               self.handleNoInitFrame()
            else: 
                if signalStartDistanceSent is False: 
                    self.signalAllowStartDistanceCapture.emit(True)
                    signalStartDistanceSent = True

                if self._PAUSE is False:

                        if self._StartDistance == 0 or self._CalibrateStartDist is True:
                            self._CalibrateStartDist = True
                            self.calibrationFrameCntr = self.handleStartDistance(self.calibrationFrameCntr)
                            
                        else:
                            self.handleGeneralDistance()
                            
                # Do Instant Velocity Calculations
                self.calculateInstantVelocity()
                 # Now Lets Do The Frame By Frame Analysis
                if self._BegZoneReached and self.frame is not None:
                    self.currFrameCnt += 1
                    if (self.currFrameCnt % self._FramesToRead) == 0:
                       self.frameByFrame()
                            
                # Lets find the instant velocity as soon as the pt reaches the measurement zone and continue from there
                #self.calculateInstantVelocity()

               
                

                # Check if the program was paused amd the end was reached
                # If so, end the timer and then do the gait speed calculations 
                if self._PAUSE and self._EndReached and not self.calculationsDone: 
                    if self._Timer.isTimerStarted():  
                        # Since we Want to Be Able to run the program again
                        measurementZoneReached = self.finishUp()  
                        
                        
                # Display a Message When the Pt Reaches the Measurement Zone
                '''
                if self._BegZoneReached is True and measurementZoneReached is False and not self.calculationsDone:
                    self._DataSave.output(3,"\n---------------------------------------------------------------------------------")
                    self._DataSave.output(3, "Patient Entered Measrument Zone at Frame: " + str(self._FrameTracker) + " and time: " + str(self._Timer.getCurrentTimeDiff())) 
                    self._DataSave.output(3,"---------------------------------------------------------------------------------\n")
                    measurementZoneReached = True
                '''
                        
            # Display The Frame
            if self.displayFrame is not None:
                
                self._OpenCVDepthHandler.displayFrame(self.displayFrame)
            
            # We Want the Pyqt5 Control Window to open once the user has either selected an init image or selected to generate one
            if not self.wasEmitted: 
                self.signalShowControlWindow.emit("DONE")
                self.wasEmitted = True 
                 
            # Since we should be done with the current frame we toss it away
            #self.currFrame = None 




        ############### Calculations Before Program Closes ###############
        self.programFinished()    
            



            
if __name__ == "__main__":
    GAITwFrame = GaitAnalyzer()
    GAITwFrame.runtime()
