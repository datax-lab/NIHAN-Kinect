# Import pykinect libraries
import enum
from PyQt5.QtCore import pyqtSignal
from PyQt5.uic.uiparser import QtCore
 
import cv2 
# Regular Librarires 
import os, time
import traceback
import numpy as np 
 
# Custom Resource Program
from Resources import Logging as lg 

# Import the class to inherit
from Resources import gait

# Pyqt Impoorts 
from PyQt5.QtGui import *
from PyQt5.QtWidgets import * 

  

    
class GaitAnalyzer(gait.GAIT): 
    # Pyqt Signals
    signalShowControlWindow = pyqtSignal(str)
    signalAllowStartDistanceCapture = pyqtSignal(bool)
    
    def __init__(self): 
        gait.GAIT.__init__(self)
        self.prevFrame, self.currFrame = None, None 
        #self.prevFrameData, self.currFrameData = None, None 
        self.distanceDifference = None 
        
        self._ProgramPath = os.path.dirname(os.path.abspath(__file__))
        self._ProgramPath = os.getcwd()


        # Frame by Frame Analysis Vars
        self._FramesToRead = 15
        self._FrameConst = (self._FramesToRead/30)
        self._lenConvFactor = 1000 # divide by this to get meters
        # Allow saving of a previous frame
        self._FrameTracker, self._SaveAFrame = 0, True 
        self._FindDiffNeeded = True 
        # Create an array that can be read from anywhere in the program that contains all the distance differences among the frames
        self.distanceDiffArr = [] 
        
        # A Fail Safe Array, to prevent program crash 
        self._LastPosition2 = []
        # Program Logging
        self._DataSave = self._ptLog
        

        # Timers 
        self._TimerMeasurementZone = self._TimerMeasure # Measurement Zone Timer, Program Timer is still in parent class

        
        # QThread Flags
        self.threadRunning = True 
        self.wasEmitted = False 

        # Debug  
        self.diffCntr = 0 
        self._PrevDistance = None



    # Functions to be called in functions
    def _find_min_from_max(self, x_Start, width, y_Start, height, min):
        distanceArr = []
        # Go Through Distances Around the Object Midpoint searching for ones larger than or equal to the endzone distance
        if width is None or height is None: 
            x_Start, width, y_Start, height = self._LastPosition2[0], self._LastPosition2[1], self._LastPosition2[2], self._LastPosition2[3]
            self._programLog.output(2, "Fall Back Point was Used at x_Start: " + str(x_Start) + "y_Start: " + str(y_Start))
        
        # Since the kinect may lose the person at random points, this is a fallback point
        #self._LastPosition2=[x_Start, width, y_Start, height]

        for x in range(x_Start, x_Start+width):
            for y in range(y_Start, y_Start+height):
                distance = self._OpenCVDepthHandler.getDepth(self.frameDataReader, x, y) - self._StartDistance
                # Save the Distances that are not 0 and
                # when subtracted by the start distance are still larger than or equal to
                # the endMeasurement zone 
                if ( distance - min) > 0:
                    distanceArr.append((distance))

        # Sort the array so that the smallest distance is at the front
        distanceArr = sorted(distanceArr)
        # Return this smallest distance to see if we really are at the endpoint
        if len(distanceArr) > 0:
            return distanceArr[0]
        else:
            return 0

    # There was a bug where the program would not end at the endzone, so this was a temp fix
    def checkForEndZone(self, intObject):
        if intObject >= self._EndMeasurementZone_mm: 
            self._PAUSE, self._EndReached = True, True
            self._AllowDataCollection = False  


    def calculateDistanceDiff(self) -> float : 
        if self.currFrame is None: 
            return 
        
        distance_Curr = None
        x_Curr_Cent, y_Curr_Cent = None, None
        try: 
            x_Curr_Cent, y_Curr_Cent, w_Curr, h_Curr = self._OpenCVDepthHandler.getObjectMidPoint(self._InitFrame, self.currFrame, self.displayFrame)
        except Exception: 
            self._programLog.output(3,str(traceback.format_exc()))
            exit(-1)
 
        # Get the Depth of the Prev blob and the Current Blob 
        if self.frameDataReader is not None: 
           
            if (x_Curr_Cent is not None and y_Curr_Cent is not None):
                distance_Curr = self.currentDistance
                # Since we can assume the person is always moving forward, we want to find a vlaue larger than the previous distance
                if distance_Curr < self._PrevDistance: 
                    distance_Curr = self._find_min_from_max(x_Curr_Cent, w_Curr, y_Curr_Cent, h_Curr, self._PrevDistance)     
                self.diffCntr += 1
            else: 
                return None

        # Info needed to plot, make sure to get the immediate time, otherwise it may be inaccurate
        saveTime = self._Timer.getCurrentTimeDiff()
        
        
        # Now Calculate The Difference
        self.distanceDifference = float(distance_Curr - self._PrevDistance)
        saveSpd = float((self.distanceDifference/self._lenConvFactor) * self._FrameConst)
        
        # For Now Just Temporarily Save the info
        self._DataSave.output(2, f"\nCurrent Time: {self._Timer.getCurrentTimeDiff()}")
        sentence = f"{self.diffCntr}. Current Distance {distance_Curr} Previous Distance {self._PrevDistance} Calculated Speed:"
        self._DataSave.output(2,f"{sentence} {np.round(saveSpd, decimals=4)}")
        if self._BegZoneReached: 
            self._DataSave.output(2, f"Current Distance in Measurement Zone: {self.curr_Distance_measure_zone}")
        #self._PrevDistance = distance_Curr
        # PLotting info
        xySave = [saveTime, np.round(float(saveSpd), 4)]
        self.plot.insertXY(xySave)

        # Return the difference if we want it
        #return float(self.distanceDifference/self._lenConvFactor)
        self._PrevDistance = distance_Curr
        #self.checkForEndZone(distance_Curr)
        
        
        return np.round(float(saveSpd),6)

    # To be used if decided to put cv2 window into pyqt window
    def stopSending(self): 
        self.threadRunning = False 

    # Stuff I Should Record For Now 
    # Struct currDistance{
    #   currDistance = 1 Ft 
    #   currTime    =  5 sec 
    #   currVeloctiy = ...
    #   }
    # Maybe later place into a dictionary 
    # in a dictionary => iterationCnt : {'currVelocity': {'currDistance: ', 'currTime': } }
    
   


    def frameByFrameAnalysis(self): 
        # Track and Record Frames 
        if (self._AllowDataCollection is True and self.frame is not None) and self._PAUSE is False: 
            self._FrameTracker += 1 
            if self.prevFrame is None and self._EndReached is False: 
                self.prevFrame, self.prevFrameData = self.currFrame, self.frameDataReader

        # Here is where I will find the distance difference between two frames
        if (self._AllowDataCollection is True and self._PAUSE is False) or (self.prevFrame is not None and self._EndReached is True): 
            if (self._FrameTracker % self._FramesToRead == 0):# or self._FindDiffNeeded:
                if self.currFrame is not None:
                    distanceDiffTemp = self.calculateDistanceDiff()
                    if distanceDiffTemp is not None:
                        self.distanceDiffArr.append(distanceDiffTemp)
            if self._EndReached: 
                self.prevFrame = None 



    # vf = [(deltaX(in meters) * 2)/time (in sec)] - vi
    # vi will always equal vf_AccelZone
    # Should return velocity in m/s 
    def _instantVelocityHelper(self, aDistance, currTime, vInital) -> float: 
        
        aDistance = aDistance/self._UnitConversionFactor # Convert from mm to m 
        
        return float(((aDistance * 2)/currTime) - vInital)

    def _findBestDistanceToOffset(self) -> tuple: 
        
        if len(self.tempIV_Distance_Arr) == 0 or len(self.tempIV_Distance_Arr_time) == 0: 
            return None, None
        
        

        # Sort the arrays
        
        self.tempIV_Distance_Arr_time = sorted(self.tempIV_Distance_Arr_time)
        #self.tempIV_Distance_Arr = sorted(self.tempIV_Distance_Arr)
        # Now save [distance, time] of the first element, element[0]
        distance =  self.tempIV_Distance_Arr[0]  # Maybe remove the distance var later, because what's rlly happening, is that im looking 
                                                                     # for the time in which the distance closest was reached
        
        time = self.tempIV_Distance_Arr_time[0]
                
        # Clear the Arrays since we should be done with them at this point
        self.tempIV_Distance_Arr.clear()
        self.tempIV_Distance_Arr_time.clear()

        self.instantVelocityCalculated = True

        # Return the saved [distance, time] pair 
        #return self.distanceOffset_Min, time 
        return distance, time

    def _saveToDict(self, iVelocity, distance, time): 
        if self.lastIvCalculated is True or self.prevDistance == round(distance,0):
             return 
        elif (self._DistanceOffset + self.distanceOffset_Min) > self._EndMeasurementZone_mm:
            self.lastIvCalculated = True # Calculate the distance at 3942, then don't do anything else
        

        self.prevDistance = round(iVelocity, 0)
    
        if self.labelRuntimes in self.iV_Dict:
            self.iV_Dict[self.labelRuntimes].append({'currIV': iVelocity, 'distance_Measure': distance, 'CurrTime': time})
        else: 
            self.iV_Dict.update({self.labelRuntimes: [{'currIV': iVelocity, 'distance_Measure': distance, 'CurrTime': time}]})

        # Upload to graph alongisde dictionary
        self.saveToGraph((distance/self._UnitConversionFactor), iVelocity) # Should Graph in M and m/s

    def saveToGraph(self, distance, iVelocity):
        self.plot.insertXY((distance, iVelocity))


    def _iVHelper2(self, distanceVar, timeVar=None): 
        distance, time = distanceVar, self._TimerMeasure.getCurrentTimeDiff()
        if timeVar is not None:
            time = timeVar
        iVelocity = self._instantVelocityHelper(distance, time, self.vf_AccelZone)
        self._saveToDict(iVelocity, distance, time)

   
        

    def calculateInstantVelocity(self): 
        
        if self._BegZoneReached is False or self.lastIvCalculated:
            return 
        elif self.vf_AccelZone is None: 
            distance, time = self._BeginMeasurementZone_mm, self._Timer.getCurrentTimeDiff()
            self.vf_AccelZone = self._instantVelocityHelper(distance, time, 0)
            self.vi_MeasureZone = self.vf_AccelZone
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
            distance, time = self._findBestDistanceToOffset()
            if distance is not None and time is not None:
                self._iVHelper2(distance, time)

        

        if not self.searchingForOffset and self.curr_Distance_measure_zone >= self.distanceOffset_Max:
            if ((self._DistanceOffset + self.distanceOffset_Min) < self._EndMeasurementZone_mm): 
                self.distanceOffset_Min = self.distanceOffset_Max
                self.distanceOffset_Max = self.distanceOffset_Max + self._DistanceOffset
        elif self.searchingForOffset:
            self.tempIV_Distance_Arr.append(self.curr_Distance_measure_zone)
            self.tempIV_Distance_Arr_time.append(self._TimerMeasure.getCurrentTimeDiff())



    def finishUp(self) -> bool: 
        self.doGaitSpeedCalc()
        self.reportGait()
        #self.averageDict()
        self.diffCntr = 0 # This was for frame by frame analysis, may not need anymore
        self.programCanContinue.emit(True)
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
                            self._PrevDistance = self._StartDistance
                            
                        else:
                            self.handleGeneralDistance()
                            
                # Lets find the instant velocity as soon as the pt reaches the measurement zone and continue from there
                self.calculateInstantVelocity()
                # Now Lets Do The Frame By Frame Analysis
                #self.frameByFrameAnalysis()
                

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
