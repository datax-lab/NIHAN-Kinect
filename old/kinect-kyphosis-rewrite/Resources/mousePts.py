
class Mouse_Pts: 
    
    def __init__(self, x, y, id=None): 
       
       # Just a label, if its needed 
       self._ID = 0 
       if id != None: 
            self._ID = id  

       # Will be used to hold the distance of  
       self._X, self._Y = x, y  
       self._Distances = []
       self._DistanceSum, self._DistanceAvg = None, None
       self._X_Space_Location, self._Y_Space_Location = None, None 


    # Getter Functions 
    def get_Point_ID(self) -> int: 
        return self.get_Point_ID
    
    # Must return int, as I can't index decimal vals in a 3d depth array 
    def getXY(self) -> tuple: 
        return int(self._X), int(self._Y)   
    
    def getAvgDistance(self): 
        return self._DistanceAvg

    def getSpcPoints(self): 
        return self._X_Space_Location, self._Y_Space_Location
    # Setter Functions 
    def set_Distance(self, distanceVal): 
        self._Distances.append(distanceVal)

    def calculateAvgDistance(self):
        if len(self._Distances) == 0:
            return 
        
        if self._DistanceSum is None or self._DistanceAvg is None: 
            self._DistanceSum = 0 
            self._DistanceAvg = 0

        # Do the Calculations of Distance and then get its average 
        for distances in self._Distances: 
            self._DistanceSum += float(distances)
        self._DistanceAvg = float(self._DistanceSum)/len(self._Distances)


    def set_RealSpc_Vals(self, xSpcPosition, ySpcPosition): 
        self._X_Space_Location, self._Y_Space_Location = xSpcPosition, ySpcPosition

      
