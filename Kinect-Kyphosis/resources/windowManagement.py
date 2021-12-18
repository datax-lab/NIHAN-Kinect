from pygame import key
from resources import mousePts as MP
import cv2 
import numpy as np 
import time

# Global Variables since mouse handler won't properly save or allow for access of the x,y coordinates
ix, iy = None, None
showX, showY = None,None

# Controls the openCV window
# Key controls for the window
class cvWindowControl:
   
    def __init__(self, height, width, startID, loggingFile = None): 
        
        # Window Properties
        self.windowName = "Kinect V2 Depth Image"
        self.height, self.width = height, width
        # Init the frame
        self._Frame = np.zeros((self.height, self.width), np.uint8)
        # Window Creation Vars
        self.createWindow() # Automatically create a blank window upon instatiation
        self._CreatedWinow = False

        # Converted to Readable Format Flag
        self.converted = False
        # Mouse Points
        self.locations = [] 
        self.id = startID

        # Logging 
        self._Logger = loggingFile
        


    def createWindow(self):
        cv2.namedWindow(self.windowName, cv2.WINDOW_AUTOSIZE) 
        self._CreatedWinow = True
    
    # Since images are not in an editable form, we need to convert it to a usable format
    def cnvtKinectImage(self, image): 
        self._Frame = image.astype(np.uint8)
        self._Frame = np.reshape(self._Frame, (self.height, self.width))
        self._Frame = cv2.cvtColor(self._Frame, cv2.COLOR_GRAY2RGB)
        self.converted = True
        self.converted = True

        return self._Frame # Allow for frame to be returned
    
    def saveImage(self, name):
        if not self.converted: 
            if self._Logger is not None:
                self._Logger.ouptut(3, "\nImage not converted, please convert image first...")
            return
        if not self._CreatedWinow: 
            self.createWindow()
        
        cv2.imwrite(name, self._Frame)
    
    def displayImage(self):
        if not self.converted: 
            if self._Logger is not None:
                self._Logger.ouptut(3, "\nImage not converted, please convert image first...")
            return
        if not self._CreatedWinow:
            self.createWindow()
        
        self.drawCoordinates(("X:" + str(showX) + " Y:" + str(showY)))
        cv2.imshow(self.windowName, self._Frame)
    
    # Bascially a deconstructor when the program is closed
    def closeWindows(self):
        self._Logger.output(2,"Window Closed")
        cv2.destroyAllWindows()

     # Drawing a Point to the image
    def drawCircleToCV(self, x, y, color = None): 
        if color is None: 
            color = (0,0,255)
        self.Frame = cv2.circle(self._Frame, (x,y), 5, color, -1)
    
    # Show the coordinates on the screen of openCV
    def drawCoordinates(self, text): 
        coord1X, coord2X = 0,200
        coord1Y, coord2Y = 28,58
        self.Frame = cv2.rectangle(self._Frame, (coord1X,coord1Y), (coord2X,coord2Y), (0,0,0), -1)
        self.Frame = cv2.putText(self._Frame, text, (41,47), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
    
    
    ######################################
    # Mouse Handling Functions
    def handleMousePress(self): 
        cv2.namedWindow(self.windowName)
        cv2.setMouseCallback(self.windowName, self._mouseController)
        # we can save the point to the spinal cord locations
    
    # Actually handles the mouse events
    # Saves x,y coodinates to an array 
    def _mouseController(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDBLCLK:
            self.drawCircleToCV(x, y)
            if x < self.width and y < self.height:
                global ix, iy
                ix,iy = x,y
                self._saveToArray()
        else: 
            global showX, showY
            showX, showY = x,y

            
    def _saveToArray(self):
        global ix, iy
        if ix != None and iy !=None: 
            self.locations.append(MP.MOUSE_PTS(self.id, ix,iy))
        ix,iy = None, None

    # Resets the program to the original state
    def resetLocations(self): 
        self.locations = []
        self.id = 0

    ######################################
               

   
    
    
# Inherit the cvWindowControl class so that I can add functionality without breaking the main window management
# This class handle image editing  
class cvController(cvWindowControl):
    
    def __init__(self, height, width, startID, loggingFile = None): 
        super().__init__(height, width, startID, loggingFile)
        self.window2 = "Edited Image"
        self.img2 = np.zeros((self._Frame.shape), np.uint8)

        # Cropping Variables 
        self.pointsSelected = []
        self.cropping = False
         
    def showEditImage(self, img = None): 
        cv2.namedWindow(self.window2)
        if img == None: 
            cv2.imshow(self.window2, self.img2)
        elif img: 
            cv2.imshow(self.window2, img)

   
    def Edit(self): 
       self.unsharpMask()

        
    # Apply unsharpened mask algo to make image sharper 
    # sharpened = original + (original - blurred) * amount
    def unsharpMask(self): 
        sharpenedImg = None 
        blurredImage = cv2.GaussianBlur(self._Frame, (3,3), -5)
        sharpenedImg = cv2.subtract(self._Frame, blurredImage)
        sharpenedImg = (sharpenedImg * 10) + self._Frame
        self.img2 = sharpenedImg
        self.showEditImage()
    
    def setCrop(self):
        print("Set Crop")
        if self.crop: 
            self.crop = False
        else: 
            self.crop = True  


    def crop(self): 
        print("Cropping")
        if len(self.pointsSelected) < 2:
            print("Cropping")
            cv2.setMouseCallback(self.windowName, self.mouseCropping)
        else: 
            print("2 Points Placed, Please Wait...")
            croppedImg = self._Frame.copy()
            croppedImg = cv2.rectangle(croppedImg, self.pointsSelected[0].getXY(), self.pointsSelected[1].getXY(), (0,255,0), 5)
            self.showEditImage(croppedImg)
    
    def mouseCropping(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDBLCLK:
            print(x,y)
            self.pointsSelected.append(0,x,y)
           



