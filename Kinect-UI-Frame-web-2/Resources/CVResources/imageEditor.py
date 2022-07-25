import cv2
from matplotlib import image
import numpy as np
# Manages the basics of CV library, such as image conversion and display
class CVEditor:
    def __init__(self, height, width, windowName):
        # Image Parameters
        self._Height, self._Width = height, width
        self._WindowName = windowName
        #cv2.namedWindow(self._WindowName)

        # Image
        # _LayeredFrame = the frame that contains the layers that mimics the 3d image, may be used to display to window
        # _2DFrame = the 2d true grayscale frame, used for processing
        self._FrameOrig, self._2DFrame, self._LayeredFrame = None, None, None

        # Converted Flag
        self._IsCnvt = False

       

    def __ConvtToLayeredImg(self):
        self._IsCnvt = False
        self._LayeredFrame = self._LayeredFrame.astype(np.uint8)
        self._LayeredFrame = np.reshape(self._LayeredFrame, (self._Height, self._Width))
        self._LayeredFrame = cv2.cvtColor(self._LayeredFrame, cv2.COLOR_GRAY2RGB)
        self._IsCnvt = True
        return self._LayeredFrame

    def __ConvtTo2D(self):
        self._IsCnvt = False
        self._2DFrame = np.reshape(self._2DFrame, (424, 512))
        self._2DFrame.clip(1, 4000) / 16.
        self._2DFrame >>= 4
        self._2DFrame = self._2DFrame.astype(np.uint8)
        self._IsCnvt = True
        return self._2DFrame

    def convtImg(self, img):
        self._FrameOrig = img
        self._LayeredFrame = self._FrameOrig.copy()
        self._2DFrame = self._FrameOrig.copy()
        return self.__ConvtToLayeredImg(), self.__ConvtTo2D()



    # Displaying and Saving Functions Below
    def saveImage(self, fileName, img=None):
        if img is None:
            img = self._LayeredFrame
        try:
            cv2.imwrite(fileName, img)
        except Exception as err:
            print("There was an error saving the image: " + str(err))
 
    def displayAMessageToCV(self, img, message, beginRectangleCoord, endrectangleCoord, startTextCoord): 
        imgTemp = cv2.rectangle(img, beginRectangleCoord, endrectangleCoord, (0,0,255), -1)
        imgTemp = cv2.putText(img, message,startTextCoord, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
        return imgTemp

    def display3dand2dImg(self):
        cv2.namedWindow("2D Image")
        cv2.namedWindow("3D Image")
        cv2.imshow("2D Image", self._2DFrame)
        cv2.imshow("3D Image", self._LayeredFrame)

    def displayFrame(self, frame):
        cv2.namedWindow(self._WindowName)
        cv2.resizeWindow(self._WindowName, self._Width, self._Height)
        cv2.imshow(self._WindowName, frame)

    def closeWindows(self):
        cv2.waitKey(1)
        cv2.destroyWindow("2D Image")
        cv2.destroyWindow("3D Image")
        

    def closeAllWindows(self):
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        

    def displayFloatingMessage(self, img, textOut :str, xyStartText : tuple, color : tuple): 
        imgTemp = cv2.putText(img, textOut, xyStartText, cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.9, color, 2)
        return imgTemp




# Handles any manipulations, and grabbing depth information
class CVEDITOR_DEPTH(CVEditor):
    # This requires a frame to output contour drawing to, the displayFrame should be the frame that we want to show
    # as the front end to the user, so it should allow for colors, (basically 3d imge, not 2d)
    def __init__(self, height, width, windowName):
        CVEditor.__init__(self, height, width, windowName)
        
        # Boolean for Gausian Blur 
        self.BLUR_VAL = 23; 
        

    # Grab the Depth Value from the FrameDataReader
    def getDepth(self, frameData, x, y):
        if frameData is None: 
            print("Error")
            return 0
        return frameData[(y * self._Width) + x]

    
    def setBlurValue(self, val : int):
        if(not isinstance(val, int)): return 
        self.BLUR_VAL = val 
         
    def getBlurvalue(self): return self.BLUR_VAL   
    
    
    def closeAWindow(self, aDisplayFrame=None):
        print(f"Destroying Window {aDisplayFrame}", flush=True)
        cv2.waitKey(1)
        try: 
            cv2.destroyWindow(aDisplayFrame)
        except Exception: 
            pass 
    
    

    # Function that gets the background of an image
    def identifyBackground(self, initFrame, src2):
        # Blur Both Images, to remove any noise that may make the program think its a foreground object
        if initFrame is None or src2 is None:
            assert("Error, one of the sources are empty!")

        frame1 = cv2.GaussianBlur(initFrame, (self.BLUR_VAL,self.BLUR_VAL), 0)
        frame2 = cv2.GaussianBlur(src2, (self.BLUR_VAL,self.BLUR_VAL), 0)
        #frame1 = cv2.medianBlur(initFrame, 7)
        #frame2 = cv2.medianBlur(src2, 7)
        #cv2.imshow("Internal 1", src2)
        #cv2.imshow("Internal", frame2)
        # Create the Delta Frame
        frameDelta = cv2.absdiff(frame1, frame2)
        # Debug Show For Now
        #cv2.imshow("Delta Frame", frameDelta)

        # Clean Up the Image a bit more, to better the bacgkround isolation
        threshImg = cv2.threshold(frameDelta, 35,255, cv2.THRESH_BINARY)[1]
        threshImg = cv2.dilate(threshImg, None, iterations=2)
        # Debug Image
        #cv2.imshow("Thresholded Image", threshImg)

        # Return the background thresholded image
        return threshImg


    # Find the Center of a Identified Contour
    def __GetContourMidPoint(self, x, y, w, h, aDisplayFrame=None) -> int:
        try:
            x_Center, y_Center = (int((x+(x+w))/2)), (int((y+(y+h))/2))
            if aDisplayFrame is not None:
                cv2.circle(aDisplayFrame, (x_Center, y_Center), 10, (0, 0,255), -1)
        except Exception as err:
            raise("There was an error getting the midpoint of the contour:", err)

        return int(x_Center), int(y_Center)


    # Find the midpoint of a foreground object (should be relatively large contour as the focus of the image should be a person)
    # Should return 4 items, the xy center point, and then the width and height, in the case something wants to be done with
    # these values
    # Returns None, if error
    def getObjectMidPoint(self, initFrame, frame, aDisplayFrame=None):
        # Obtain the Background, using background identifier function, it is based of the initFrame
        threshold = self.identifyBackground(initFrame.copy(), frame.copy())

        # Find the contours of a foreground object
        contours, _ = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Make sure that there is some contour detected
        if len(contours) > 0:
            # Get the object with the largest contour
            maxContour = max(contours, key=cv2.contourArea)
            # Get the Dimensions of the largest object's contour
            (x,y,w,h) = cv2.boundingRect(maxContour)
            # Ensure that the contour is somewhat large, as it should be a person, not noise
            if w > 21 and h > 21:
                x_Cent, y_Cent = self.__GetContourMidPoint(x,y,w,h, aDisplayFrame)
                # Draw the rectangle around the largest contour
                if aDisplayFrame is not None:
                    cv2.rectangle(aDisplayFrame, (x,y), (x+w, y+h), (0,255,0),3)
                    cv2.circle(aDisplayFrame, (x_Cent,y_Cent), 10, (0,0,255), -1)
                # Return Coordinates
                return x_Cent, y_Cent, w, h

        return None, None, None, None


