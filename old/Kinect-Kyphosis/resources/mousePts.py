

# This class will store the depth values of the given x,y coordinates of C7, T12/L1, and S1 (must be manually palpated)
# This utilizes getter and setter functions to obtain data and set data
class MOUSE_PTS: 
    def __init__(self, id ,x, y): 
        self._Point_ID = id
        self._x, self._y = x, y 
        self._depthValArr = []
        self._avgDistance2 = None
        self._x_Real_Distance, self._y_RealDistance = None, None 

    def get_Pt_ID(self):
        return self._Point_ID

    def setDepth_Val(self, deptVal): 
        #print("Appending Depth Value: " + str(deptVal) + " to coordinate: " + str(self._x) + " " + str(self._y)) # Debug print
        self._depthValArr.append(deptVal)
    
    def set_Real_Distances(self, distanceX, distanceY): 
        self._x_Real_Distance = distanceX 
        self._y_RealDistance = distanceY

    # Save avg distance to the last index of the depthValArr 
    def setAvgDistance(self, avgDistance): 
        self._avgDistance2 = avgDistance

    # Getter Functions
    def getXY(self): 
        return self._x, self._y 
    
    def getDepthValsArr(self) -> None:
        return self._depthValArr

    # Getter Function of depth/distance
    def getAvgDistance(self): 
        return self._avgDistance2

    def getRealDistances(self):
        return self._x_Real_Distance, self._y_RealDistance
    