

# This class will store the depth values of the given x,y coordinates of C7, T12/L1, and S1 (must be manually palpated)
# This utilizes getter and setter functions to obtain data and set data
class MOUSE_PTS: 
    def __init__(self, id ,xyTuple): 
        self._Point_ID = id
        self._x, self._y = xyTuple
        self._depthValArr = []
        self._avgDistance2 = None
        self._x_Real_Distance, self._y_RealDistance = None, None 

   # Append a Depth Value to the Array, since we will be taking distances over the span of approx 5 frames and then averaging
    def setDepth_Val(self, deptVal): 
        self._depthValArr.append(deptVal)
    
    def set_Real_Distances(self, distanceX, distanceY): 
        self._x_Real_Distance = distanceX 
        self._y_RealDistance = distanceY

    # Save avg distance 
    def setAvgDistance(self, avgDistance): 
        self._avgDistance2 = avgDistance

    # Getter Functions
    def get_Pt_ID(self) -> int:
        return self._Point_ID
    
    def getXY(self) -> tuple: 
        return self._x, self._y 
    
    def getDepthValsArr(self) -> list:
        return self._depthValArr

    # Getter Function of depth/distance
    def getAvgDistance(self) -> float: 
        return self._avgDistance2

    def getRealDistances(self):
        return self._x_Real_Distance, self._y_RealDistance
    