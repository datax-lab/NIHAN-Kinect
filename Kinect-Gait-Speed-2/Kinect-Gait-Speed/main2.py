# Import pykinect libraries
from tkinter.constants import X
from cv2 import DIST_USER
from numpy.lib.function_base import average

from pykinect2 import PyKinectRuntime
from pykinect2 import PyKinectV2

# Regular Librarires 
import time 
import os 
import traceback
import numpy as np 
import matplotlib as plt 
import math
import Resources 
# Import the class to inherit
from main import GAIT
from Resources import Logging as Log
from Resources import timer




    

class GAITFRAME(GAIT): 
    def __init__(self): 
        GAIT.__init__(self)
        self.prevFrame, self.currFrame = None, None 
        self.prevFrameData, self.currFrameData = None, None 
        self.distanceDifference = None 
        
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
    '''
    def _instantVelocity(self, displacement, currTime) -> float:
        currVelocity = ((displacement * 2) / currTime) - self._VelocityInitial
        return float(currVelocity) 

    # Using equation of vf = [(displacement * 2) / givenTime] - Vi
    # vi is the == to the vf at the end of the acceleration zone 
    def calculateGaitSpeedAtGivenTime(self):
        if self._VelocityFinalAtEndOfAcce == None: 
            self._VelocityFinalAtEndOfAcce = self._instantVelocity(self._BeginMeasurementZone, self._Timer.getCurrentTimeDiff())
        else: 
            self._recordedVelocityArr.append(self._instantVelocity(self.distanceDiffArr[len(self.distanceDiffArr) - 1], 
                                            self._TimerMeasurementZone.getCurrentTimeDiff())
                                            )
        self._DoVelocityCalc = False 
    '''


    # Functions to be called in functions
    def _find_min_from_max(self, x_Start, width, y_Start, height, min):
        distanceArr = []
        # Go Through Distances Around the Object Midpoint searching for ones larger than or equal to the endzone distance
        if width is None or height is None: 
            x_Start, width, y_Start, height = self._LastPosition2[0], self._LastPosition2[1], self._LastPosition2[2], self._LastPosition2[3]
            self._programLog.output(2, "Fall Back Point was Used at x_Start: " + str(x_Start) + "y_Start: " + str(y_Start))
        
        # Since the kinect may lose the person at random points, this is a fallback point
        self._LastPosition2=[x_Start, width, y_Start, height]

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
        if self.prevFrame is None: 
            return 
        
        distance_Prev, distance_Curr = None, None 
        x_Prev_Cent, y_Prev_Cent, x_Curr_Cent, y_Curr_Cent = None, None, None, None

        # Get the midpoints of the previous frame blob and the current frame blob
        try: 
            x_Prev_Cent, y_Prev_Cent, _, _ =  self._OpenCVDepthHandler.getObjectMidPoint(self._InitFrame, self.prevFrame)
            x_Curr_Cent, y_Curr_Cent, w_Curr, h_Curr = self._OpenCVDepthHandler.getObjectMidPoint(self._InitFrame, self.currFrame)
        except Exception: 
            self._programLog.output(3,str(traceback.format_exc()))
            exit(-1)

        # Get the Depth of the Prev blob and the Current Blob 
        if self.prevFrameData is not None and self.currFrameData is not None: 
            if (x_Prev_Cent is not None and y_Prev_Cent is not None) and (x_Curr_Cent is not None and y_Curr_Cent is not None):
                distance_Prev = self._OpenCVDepthHandler.getDepth(self.prevFrameData, x_Prev_Cent, y_Prev_Cent) - self._StartDistance
                distance_Curr = self._OpenCVDepthHandler.getDepth(self.currFrameData, x_Curr_Cent, y_Curr_Cent) - self._StartDistance
                # Since we can assume the person is always moving forward, we want to find a vlaue larger than the previous distance
                if distance_Curr < distance_Prev: 
                    distance_Curr = self._find_min_from_max(x_Curr_Cent, w_Curr, y_Curr_Cent, h_Curr, distance_Prev)     
                self.diffCntr += 1
            else: 
                return None

        # Info needed to plot, make sure to get the immediate time, otherwise it may be inaccurate
        saveTime = self._Timer.getCurrentTimeDiff()
        
        
        # Now Calculate the Distance Difference 
        self.distanceDifference = float(distance_Curr - distance_Prev)
        self._SaveAFrame, self._FindDiffNeeded = True, False
        saveSpd = float((self.distanceDifference/self._lenConvFactor) * self._FrameConst)
        
        # For Now Just Temporarily Save the info
        sentence = str(self.diffCntr) +  ". Current Distance: " + str(distance_Curr) + " Previous Distance: " + str(distance_Prev) + " Calculate Difference:  "
        self._DataSave.output(3,(sentence + str(np.round(saveSpd,4)) + " m/s\n"))
        
        # PLotting info
        xySave = [saveTime, np.round(float(saveSpd), 4)]
        self.plot.insertXY(xySave)

        # Return the difference if we want it
        #return float(self.distanceDifference/self._lenConvFactor)
        self.prevFrame, self.prevFrameData = None, None
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
            
            
            if (self.frame is not None and self._EndReached is False) and (self._AllowDataCollection and self._SaveAFrame) and self._PAUSE is False: 
                self.prevFrame = self.currFrame
                self.prevFrameData = self.currFrameData
                self._SaveAFrame = False 
            
            # Always clear the current frame
            # This allows the program to calculate the frame difference once the pt reaches the end of the measurement zone
            self.currFrame = None


            if self._PAUSE is False: 
                self.handleNewDepthFrames()
                self.currFrame = self.frame
                self.currFrameData = self.frameDataReader
            
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

                # Here is where I will find the distance difference between two frames
                if (self._AllowDataCollection is True and self._PAUSE is False) or (self.prevFrame is not None and self._EndReached is True): 
                    if (self._FrameTracker % self._FramesToRead == 0):# or self._FindDiffNeeded:
                        if self.currFrame is not None:
                            distanceDiffTemp = self.calculateDistanceDiff()
                            if distanceDiffTemp is not None:
                                self.distanceDiffArr.append(distanceDiffTemp)
                    
                    
                        
                                
                       
                '''
                # May be added in later, but for now this if statement does nothing
                # Handle Instantaneous Gait Speed Calculations 
                if self._DoVelocityCalc: 
                    if self._VelocityFinalAtEndOfAcce is None: 
                        self.calculateGaitSpeedAtGivenTime()
                    elif self._TimerMeasurementZone.isTimerStarted() and self._VelocityFinalAtEndOfAcce is not None:
                        #if ((math.round(self._Timer.getCurrentTimeDiff()) % self._TimeIntervals) == 0):
                        self.calculateGaitSpeedAtGivenTime()
                '''

                # Check if the program was paused amd the end was reached
                # If so, end the timer and then do the gait speed calculations 
                if self._PAUSE and self._EndReached: 
                    if self._Timer.isTimerStarted(): 
                        self._Timer.endTimer()
                        self._TimerMeasurementZone.endTimer()
                        #self._TimerMeasurementZone.endTimer()
                        self.doGaitSpeedCalc()
                        


            # Display The Frame
            if self.frame is not None:
                self._OpenCVDepthHandler.displayFrame(self.displayFrame)




        ############### Calculations Before Program Closes ###############

        
        '''
        self._DataSave.output(3, "Sum of Distance: " + str(sum(self.distanceDiffArr)))
        self._DataSave.output(3, self._recordedVelocityArr)
        
        try: 
            self._DataSave.output(3,"Length of Velocity Array: " + str(len(self._recordedVelocityArr)) +  "\nSum of velocities: " + str(sum(self._recordedVelocityArr)) + "\n")
        except Exception: 
            print("Length of Velocity Array: " + str(len(self._recordedVelocityArr)) +  "\nSum of velocities: " + str(sum(self._recordedVelocityArr)) + "\n")
            self._DataSave.output(2, str(traceback.traceback.format_exc()))
        
        self._DataSave.output(3, "\nVelocity Initial: " + str(self._VelocityFinalAtEndOfAcce))
        '''
        
        
        self._DataSave.output(3,"\n\n------------------------------------")
        self._DataSave.output(3, "          Statistics:              ") 
        self._DataSave.output(3,"------------------------------------")
        # Display Stats 
        if self._EndReached is True and self._CalculationsAllowed == False: 
            
            if self.plotFlag is False: 
                self._programLog.output(2,"------------------------------------")
                self._programLog.output(2, "          Statistics:              ") 
                self._programLog.output(2,"------------------------------------")
                self._programLog.output(3, "\n")
                self._programLog.output(3, "X-Plot Points (Times)" + str(self.plot.x_Points))
                self._programLog.output(3, "Y-Plot Points (Speed)" + str(self.plot.y_Points))
                self.plot.plotPts("test.png", "Time (sec)", "Distance (m/s)")

            self._CalculationsAllowed = True 
            self.doGaitSpeedCalc()
        if self._EndReached is True: 
            self._DataSave.output(1, "\n\n")
            self._DataSave.output(3,"Starting Distance: " + str(self._StartDistance))
            self._DataSave.output(3,"Program Time Elapsed: " + str(self._Timer.getTimeDiff()))
            self._DataSave.output(3,"Elapsed Time: " + str(self._TimeTakenToWalk))
            self._DataSave.output(3,"Calculated Gait Speed: " + str(self._Gait_Speed) + " m/s")
        
        self._programLog.closeFile()
        self._DataSave.closeFile()
        
            




            
if __name__ == "__main__":
    GAITwFrame = GAITFRAME()
    GAITwFrame.runtime()
