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
# Import the class to inherit
from main import GAIT
from Resources import Logging as Log


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
        
        self._LastPosition2 = []
        # Program Logging
        self._DataSave = Log.LOGGING(os.path.join("logs", str("PtLog-" + time.strftime("%Y%m%d-%H%M%S") + "Inherit.txt")))
        #self._PtLog2 = Log.LOGGING(os.path.join("logs", str("PtLog-" + time.strftime("%Y%m%d-%H%M%S") + "Inherit.txt")))
        # Debug 
        self.diffCntr = 0 

    
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
                distance = self._OpenCVDepthHandler.getDepth(self.frameDataReader, x, y)
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
                distance_Prev = self._OpenCVDepthHandler.getDepth(self.prevFrameData, x_Prev_Cent, y_Prev_Cent)
                distance_Curr = self._OpenCVDepthHandler.getDepth(self.currFrameData, x_Curr_Cent, y_Curr_Cent)
                # Since we can assume the person is always moving forward, we want to find a vlaue larger than the previous distance
                if distance_Curr < distance_Prev: 
                    distance_Curr = self._find_min_from_max(x_Curr_Cent, w_Curr, y_Curr_Cent, h_Curr, distance_Prev)     
                self.diffCntr += 1
            else: 
                return None

        # Now Calculate the Distance Difference 
        self.distanceDifference = float(distance_Curr - distance_Prev)
        self._SaveAFrame, self._FindDiffNeeded = True, False
        # For Now Just Temporarily Save the info
        sentence = str(self.diffCntr) +  ". Current Distance: " + str(distance_Curr) + " Previous Distance: " + str(distance_Prev) + " Calculate Difference:  "
        self._DataSave.output(3,(sentence + str(np.round(((self.distanceDifference/self._lenConvFactor) * self._FrameConst),4)) + " m/s\n"))
        # Return the difference if we want it
        return np.round(float((self.distanceDifference/self._lenConvFactor) * (self._FrameConst)),4)





    def runtime(self): 
        calibrationFrameCntr = 0 
        measurementZoneReached = False 
        distanceDiffs = []
        # If supplied an initial image, convert from RGB to Gray, removing the third element of the tuple 
        if self._InitImageFileName is not None:
            self._convt_init_img()

        while not self._IsDone:
            
            if (self.frame is not None and self._EndReached is False) and (self._AllowDataCollection and self._SaveAFrame) and self._PAUSE is False: 
                self.prevFrame = self.currFrame
                self.prevFrameData = self.currFrameData
                self._SaveAFrame = False 
            if self._PAUSE is False: 
                self.handleNewDepthFrames()
                self.currFrame = self.frame
                self.currFrameData = self.frameDataReader
            
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
                                self._DataSave.output(2, "Patient Entered Measrument Zone at Frame: " + str(self._FrameTracker) + " and time: " + str(self._Timer.getCurrentTimeDiff()) +"\n") 
                                measurementZoneReached = True

                if self._AllowDataCollection is True and self.frame is not None: 
                    self._FrameTracker += 1 

                # Here is where I will find the difference between to frames
                if (self._AllowDataCollection and self._PAUSE is False) and self.prevFrame is not None: 
                    if (self._FrameTracker % self._FramesToRead == 0) or self._FindDiffNeeded:
                        if self.currFrame is not None: 
                            distanceDiffs.append(self.calculateDistanceDiff())
                        else: 
                            # In the Case that the current frame is none, we will need to find the difference once we get a valid frame
                            self._FindDiffNeeded = True
                
              
                # Check if the program was paused amd the end was reached
                # If so, end the timer and then do the gait speed calculations 
                if self._PAUSE and self._EndReached: 
                    if self._FindDiffNeeded: 
                        self.calculateDistanceDiff()
                    if self._Timer.isTimerStarted(): 
                        self._Timer.endTimer()
                        self.doGaitSpeedCalc()
                #if self._FrameTracker == 121 : 
                    #print(self._Timer.getCurrentTimeDiff())
                    #exit(0)


            # Display The Frame
            if self.frame is not None:
                self._OpenCVDepthHandler.displayFrame(self.displayFrame)

        # Calculate the distance 
        self._DataSave.output(3, "Sum of Distance: " + str(sum(distanceDiffs)))
        # Display Stats 
        if self._EndReached is True and self._CalculationsAllowed == False: 
            self._CalculationsAllowed = True 
            self.doGaitSpeedCalc()
        if self._EndReached is True: 
            self._DataSave.output(1, "\n\n")
            self._DataSave.output(3,"Starting Distance: " + str(self._StartDistance))
            self._DataSave.output(3,"Elapsed Time: " + str(self._TimeTakenToWalk))
            self._DataSave.output(3,"Calculated Gait Speed: " + str(self._Gait_Speed) + " m/s")
        
        self._programLog.closeFile()
        self._DataSave.closeFile()
        
            




            
if __name__ == "__main__":
    GAITwFrame = GAITFRAME()
    GAITwFrame.runtime()
