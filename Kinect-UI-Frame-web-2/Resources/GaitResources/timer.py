import time 
import random
class Timer: 
    def __init__(self, timerID = None):
        # Just timer identifiers, this is optional
        if timerID == None: 
            timerID = random.randrange(0,1000)
            timerID = str("Timer-") + str(timerID)
        
        self.timerID = timerID

        # Start and end Times 
        self._StartTime, self._EndTime = None, None 
        self._TimePaused = None 
        
        # Flags 
        self._TimerStopped, self._TimerStarted, self._TimerPaused = True, False, False 

    # Just some timer statys getter functions 
    def isTimerStopped(self) -> bool:
        return self._TimerStopped
    
    def isTimerStarted(self) -> bool:
        return self._TimerStarted
     
    def isTimerPaused(self) -> bool:
         if self._StartTime is None or self._TimePaused is None :
             print("Error, Timer ", self.timerID, "was not started....")
             return False 

         return self._TimerPaused

    def getTimeDiff(self, verbose=False) -> float:
        if self._StartTime is not None and self._EndTime is not None:
            elapsedTime = self._EndTime - self._StartTime
            if verbose is True:
                print("Elapsed time of " + str(self.timerID) + " " +str(elapsedTime) )
            return float(elapsedTime)
        else:
            print("Error, No Time Detected")
            exit(-1)

    def getCurrentTimeDiff(self) -> float: 
        if self._StartTime is not None:
            return float(time.time() - self._StartTime)


    # Now to the actual functions to start the timer, end the timer, or pause the timer  
    def starTtimer(self, verbose = False):
        if self._StartTime is None:
            if verbose is True:
                print("Timer \"", self.timerID,"\" Started\n")
            self._StartTime = time.time()
            self._TimerStarted = True
            self._TimerStopped = False
    
    def endTimer(self, verbose=False):
        if not self._TimerStopped:
            if verbose:
                print("Timer \"", self.timerID,"\" Ended")
            self._EndTime = time.time()
            self._TimerStopped = True
            self._TimerStarted = False

           
    



    

    