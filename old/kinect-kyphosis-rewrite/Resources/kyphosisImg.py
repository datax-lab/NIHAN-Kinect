from Resources.imageEditor import CVEDITOR_DEPTH
from Resources.mousePts import Mouse_Pts
import imageEditor 
import cv2 
import mousePts

ix,iy = None, None 
showX, showY = None, None 


class KyphosisImgEditor(CVEDITOR_DEPTH): 
    def init(self, height, width, windowName): 
        CVEDITOR_DEPTH.__init__(height=height, width=width, windowName=windowName) 
        self.aDisplayFrame = None 
        # This is to deal with saving data when there is a mouse event
        self.ptsArr = [] 

    def setDisplayFrame(self, aDisplayFrame): 
        self.aDisplayFrame = aDisplayFrame

    def drawCricleToCV(self, x, y, color=None): 
        
        if color is None: 
            color=(0,0,255)
        self.aDisplayFrame =  cv2.circle(self.aDisplayFrame, (x,y), 5, color, -1)


    def displayCoordinates(self, text): 
        coord1X, coord2X = 0,200
        coord1Y, coord2Y = 28,58
        self.aDisplayFrame = cv2.rectangle(self.aDisplayFrame, (coord1X,coord1Y), (coord2X,coord2Y), (0,0,0), -1)
        self.aDisplayFrame = cv2.putText(self.aDisplayFrame, text, (41,47), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)


    # Mouse Handling 
    def handleMousePress(self): 
        cv2.namedWindow(self._WindowName)


    def savePtToArr(self): 
        global ix, iy 
        if ix != None and iy != None: 
            self.ptsArr.append(Mouse_Pts(ix,iy))
        ix, iy = None, None 



    def _MouseController(self, event, x, y, flags, param): 
        if event == cv2.EVENT_LBUTTONDBLCLK:
            if x < self._Width and y < self._Height: 
                self.drawCricleToCV(x,y)
                global ix, iy 
                ix, iy = x,y 
                self.savePtToArr()
        
        # Below is just to show the current coordinates on the cv window, when the user is just 
        # #moving the mouse arround
        else: 
            global showX, showY 
            showX, showY 

    def resetWindow(self): 
        self.ptsArr = [] 