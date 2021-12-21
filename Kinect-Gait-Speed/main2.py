# Import pykinect libraries
from tkinter.constants import X
from pykinect2 import PyKinectRuntime 
from pykinect2 import PyKinectV2

# Regular Librarires 
import time 
import os 

# Import the class to inherit
import main as mn 
from Resources import Logging as Log


class GAITFRAME(mn.GAIT): 
    def __init__(self): 
        mn.GAIT.__init__(self)
        self.prevFrame, self.currFrame = None, None 
        self.prevFrameData, self.currFrameData = None, None 
        self.distanceDifference = None 
        self._FramesToRead = 15
        self._FrameConst = (self._FramesToRead/30)
        self._FrameTracker, self._SaveAFrame = 0, True 
        self._DataSave = Log.LOGGING(os.path.join("logs", str("log-" + time.strftime("%Y%m%d-%H%M%S") + "Inherit.txt")))
    
    def calculateDistanceDiff(self) -> float : 
        if self.prevFrame is None: 
            return 
        
        distance_Prev, distance_Curr = None, None 
        x_Prev_Cent, y_Prev_Cent, x_Curr_Cent, y_Curr_Cent = None, None, None, None

        # Get the midpoints of the previous frame blob and the current frame blob
        x_Prev_Cent, y_Prev_Cent, _, _ =  self._OpenCVDepthHandler.getObjectMidPoint(self._InitFrame, self.prevFrame)
        x_Curr_Cent, y_Curr_Cent, _, _ = self._OpenCVDepthHandler.getObjectMidPoint(self._InitFrame, self.currFrame)

        # Get the Depth of the Prev blob and the Current Blob 
        if self.prevFrameData is not None and self.currFrameData is not None: 
            if (x_Prev_Cent is not None and y_Prev_Cent is not None) and (x_Curr_Cent is not None and y_Curr_Cent is not None):
                distance_Prev = self._OpenCVDepthHandler.getDepth(self.prevFrameData, x_Prev_Cent, y_Prev_Cent)
                distance_Curr = self._OpenCVDepthHandler.getDepth(self.currFrameData, x_Curr_Cent, y_Curr_Cent)
            else: 
                return None

        # Now Calculate the Distance Difference 
        self.distanceDifference = float(distance_Curr - distance_Prev)
        self._SaveAFrame = True 
        # For Now Just Temporarily Save the info 
        self._DataSave.output(3,(str(self.distanceDifference) + "\n"))
        # Return the difference if we want it
        return float((self.distanceDifference) * (self._FrameConst))


    def runtime(self): 
        calibrationFrameCntr = 0 
        measurementZoneReached = False 

        if self._InitImageFileName is not None:
            self._Convt_init_img()

        while not self._IsDone:
            
            if (self.frame is not None and self._EndReached is False) and (self._AllowDataCollection and self._SaveAFrame): 
                self.prevFrame = self.currFrame
                self.prevFrameData = self.currFrameData
                self._SaveAFrame = False 
            if self._EndReached is False: 
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
                            message = "Press \'i\' to get Start Distance"
                            self._OpenCVDepthHandler.displayAMessageToCV(self.displayFrame, message, self._BgStart,
                                                                        self._BgEnd, self._TextStart)
                        else:
                            self.handleGeneralDistance()
                            if self._BegZoneReached is True and measurementZoneReached is False:
                                self._DataSave.output(2, "Patient Entered Measrument Zone at Frame: " + str(self._FrameTracker) + " and time: " + str(self._Timer.getCurrentTimeDiff())) 
                                measurementZoneReached = True

                # Here is where I will find the difference between to frames
                if (self._AllowDataCollection and self._PAUSE is False) and self._FrameTracker % 15 == 0:
                    self.calculateDistanceDiff()
                
                self._FrameTracker += 1 
                # Check if the program was paused amd the end was reached
                # If so, end the timer and then do the gait speed calculations 
                if self._PAUSE and self._EndReached: 
                        if self._Timer.isTimerStarted(): 
                            self._Timer.endTimer()
                            self.doGaitSpeedCalc()


            # Display The Frame
            if self.frame is not None:
                self._OpenCVDepthHandler.displayFrame(self.displayFrame)


        # Display Stats 
        if self._EndReached is True and self._CalculationsAllowed == False: 
            self._CalculationsAllowed = True 
            self.doGaitSpeedCalc()
        if self._EndReached is True: 
            print("\n\n")
            print("Starting Distance:", self._StartDistance)
            print("Elapsed Time:", self._TimeTakenToWalk)
            print("Calculated Gait Speed:", self._Gait_Speed)
        
            




            
if __name__ == "__main__":
    GAITwFrame = GAITFRAME()
    GAITwFrame.runtime()
