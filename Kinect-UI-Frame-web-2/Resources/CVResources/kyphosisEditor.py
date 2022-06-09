from Resources.CVResources import imageEditor as iEdit
import cv2 

# Just to hold the basic xy mouse points 
class ptsStruct:
    def __init__(self, xyTuple): 
        self.x, self.y = xyTuple
    
    def getXY(self): 
        return self.x, self.y


# Summary:
# Inherit from CVEDITOR_DEPTH so that I can access the return depth data function simply, along with 
# the other variables I need such as the set width and heigh, and the display window
#
# This Class Needs To Handle: 
# 1. Mouse Events 
# 2. Save and Return the Coordinates of Mouse Presses on Window
# 3. Draw Circle To CV Window 
# 

class KyphosisImg(iEdit.CVEDITOR_DEPTH): 
    def __init__(self, height, width, windowName): 
        super(KyphosisImg, self).__init__(height, width, windowName)
        # Save Clciked Mouse Points Temporarily
        self.ix, self.iy = None, None 
        self.displayX, self.displayY = None, None
        # Array to Hold Mouse Pts
        self._PtsArr = []
        # Hold a Display Frame to Show Points to 
        self.aDisplayFrame = None  

    # Set the Display Frame 
    def setDisplayFrame(self, aDisplayFrame): 
        self.aDisplayFrame = aDisplayFrame
     
    def saveImg(self,filName,imSave): 
        super().saveImage(filName, imSave)

    def getDepth(self, frameData, x, y): 
        return frameData[(y*self._Width) + x]

    # Draw Points to Display
    def drawPoints(self, img, xyTuple, color=None):
        if color == None: 
            color = [0,0,255]
        return cv2.circle(img, xyTuple, 5, color, -1) 

    # Draw Points to Display
    def drawCoordinates(self,img, text): 
        coord1X, coord2X = 0,self._Width
        coord1Y, coord2Y = 0,50
        text=f"{text} {self.displayX, self.displayY}"
        img = cv2.rectangle(img, (coord1X, coord1Y), (coord2X,coord2Y), (0,0,0), -1)
        img = cv2.putText(img, text, (0,25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
        
        return img

    # Handle Mouse Events 
    def handleMouseEvents(self): 
        cv2.namedWindow(self._WindowName)
        cv2.setMouseCallback(self._WindowName, self.__mousePress)

    # Handle Mouse Events Helper 
    def __mousePress(self,event, x, y, flags, param): 
        if event == cv2.EVENT_LBUTTONDBLCLK: 
            if x < self._Width and y < self._Height: 
                self.ix, self.iy = x, y
                self.__push()
                self.ix, self.iy = None, None 
        else: 
            self.displayX, self.displayY = x,y
            
    
            
    # Save the Pressed x and y save to list 
    def __push(self): 
        self._PtsArr.append(ptsStruct((self.ix, self.iy)))

    # Get the Most Recent Mouse Points 
    def popData(self) -> tuple: 
        return self._PtsArr.pop().getXY()

    def getLen(self): 
        return len(self._PtsArr)
    
    # Reset The Array That Holds the Poitns 
    def resetList(self): 
        self._PtsArr = [] 