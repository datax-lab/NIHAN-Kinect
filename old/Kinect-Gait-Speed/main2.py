# Import pykinect libraries
from tkinter.constants import X
from cv2 import DIST_USER
from numpy.lib.function_base import average

# Regular Librarires 
import os, time
import traceback
import numpy as np 
# Import the class to inherit
from Resources import gait
from Resources import Logging as Log
from Resources import Logging as lg 


from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5 import uic 


class GAITUI(QtWidgets.QMainWindow, gait.GAIT):
    def __init__(self): 
        QtWidgets.QMainWindow.__init__(self)
        os.path.join(os.path.dir(os.path.abspath(__file__)))
        
    

class GAITFRAME(gait.GAIT): 
    def __init__(self): 
        gait.GAIT.__init__(self)
        self.prevFrame, self.currFrame = None, None 
        #self.prevFrameData, self.currFrameData = None, None 
        self.distanceDifference = None 
        
        self._ProgramPath = os.path.dirname(os.path.abspath(__file__))

        # Save the Stats 
        self._ptLog = lg.LOGGING(os.path.join("logs", str("Ptlog-" + time.strftime("%Y%m%d-%H%M%S") + ".txt")))

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
        #self._PtLog2 = Log.LOGGING(os.path.join("logs", str("PtLog-" + time.strftime("%Y%m%d-%H%M%S") + "Inherit.txt")))
        
        # For now this is an experimental section of the program, this may be implemented late
        # Fun Physics :(
        # Lets Handle Velocity at the acceleration zone first
        self._VelocityInitial, self._VelocityFinalAtEndOfAcce = 0, None 
        # Now Lets Use The Vars Above to get instantaneous velocity at given time intervals 
        self._VelocityMeasurementZoneInitial = self._VelocityFinalAtEndOfAcce # We can assume that the velocity at the end of the acceleration zone 
                                                                              # as our initial velocity 
        self._TimeIntervals = 2 # report every 2 seconds 
        self._recordedVelocityArr = [] 
        self._DoVelocityCalc = False 

        # Timers 
        self._TimerMeasurementZone = self._TimerMeasure # Measurement Zone Timer, Program Timer is still in parent class

        
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
        return distanceArr[0]



    def calculateDistanceDiff(self) -> float : 
        if self.currFrame is None: 
            return 
        
        distance_Curr = None
        x_Curr_Cent, y_Curr_Cent = None, None
        try: 
            x_Curr_Cent, y_Curr_Cent, w_Curr, h_Curr = self._OpenCVDepthHandler.getObjectMidPoint(self._InitFrame, self.currFrame)
        except Exception: 
            self._programLog.output(3,str(traceback.format_exc()))
            exit(-1)

        # Get the Depth of the Prev blob and the Current Blob 
        if self.frameDataReader is not None: 
           
            if (x_Curr_Cent is not None and y_Curr_Cent is not None):
                distance_Curr = self._OpenCVDepthHandler.getDepth(self.frameDataReader, x_Curr_Cent, y_Curr_Cent) - self._StartDistance
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
        self._DataSave.output(3, f"\nCurrent Time: {self._Timer.getCurrentTimeDiff()}")
        sentence = f"{self.diffCntr}. Current Distance {distance_Curr} Previous Distance {self._PrevDistance} Calculated Speed:"
        self._DataSave.output(3,f"{sentence} {np.round(saveSpd, decimals=4)}")
        #self._PrevDistance = distance_Curr
        # PLotting info
        xySave = [saveTime, np.round(float(saveSpd), 4)]
        self.plot.insertXY(xySave)

        # Return the difference if we want it
        #return float(self.distanceDifference/self._lenConvFactor)
        self._PrevDistance = distance_Curr
        
        
        return np.round(float(saveSpd),6)

 



    def runtime(self): 
        # Just some local variables to make things easier down the road
        calibrationFrameCntr = 0 
        # Used just for an output statement to only be printed once
        measurementZoneReached = False 

        

        # If supplied an initial image, convert from RGB to Gray, removing the third element of the tuple 
        if self._InitImageFileName is not None:
            self._convt_init_img()

        while not self._IsDone:
            
            if self._PAUSE is False and self._EndReached is False: 
                self.handleNewDepthFrames()
                self.currFrame = self.frame
                #self.currFrameData = self.frameDataReader
            
            # For Accurate Measurment within the measuremenmt zone, set a timer to start once the pt reaches the begin measurement zone 
            if self._TimerMeasurementZone.isTimerStarted() is False and self._BegZoneReached is True: 
                self._TimerMeasurementZone.starTtimer(verbose=True)

            if self._InitFrame is None and self._InitFrameConvted is False:
               self.handleNoInitFrame()
               self.openCVEvents(limitKeybind=True)
            else: 
                self.openCVEvents(limitKeybind=False)

                if self._PAUSE is False:

                        if self._StartDistance == 0 or self._CalibrateStartDist is True:
                            self._CalibrateStartDist = True
                            calibrationFrameCntr = self.handleStartDistance(calibrationFrameCntr)
                            self._PrevDistance = self._StartDistance
                            
                        else:
                            self.handleGeneralDistance()
                            if self._BegZoneReached is True and measurementZoneReached is False:
                                self._DataSave.output(2,"---------------------------------------------------------------------------------")
                                self._DataSave.output(2, "Patient Entered Measrument Zone at Frame: " + str(self._FrameTracker) + " and time: " + str(self._Timer.getCurrentTimeDiff())) 
                                self._DataSave.output(2,"---------------------------------------------------------------------------------\n")
                                measurementZoneReached = True

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
                    
                                 

                # Check if the program was paused amd the end was reached
                # If so, end the timer and then do the gait speed calculations 
                if self._PAUSE and self._EndReached: 
                    if self._Timer.isTimerStarted(): 
                        self._Timer.endTimer()
                        self._TimerMeasurementZone.endTimer()
                        #self._TimerMeasurementZone.endTimer()
                        self.doGaitSpeedCalc()
                        


            # Display The Frame
            if self.displayFrame is not None:
                self._OpenCVDepthHandler.displayFrame(self.displayFrame)
            
            # Since we should be done with the current frame we toss it away
            #self.currFrame = None 




        ############### Calculations Before Program Closes ###############

        self.finishProgram()
        
            




            
if __name__ == "__main__":
    GAITwFrame = GAITFRAME()
    GAITwFrame.runtime()
