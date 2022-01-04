import cv2
import os
# UI Library Imports
import tkinter as tk
from tkinter import filedialog
from PIL import Image
from PIL import ImageTk
import threading


class FileExplorer:
    def __init__(self, height, width):
        # Window Parameters
        self._Height, self._Width = height, width
        # Create the Window
        self._Window = None
        self._ConfirmationWindow = None

        # File Path of the Initialization Image
        self._initImgFileName=None
        # Whether to create a new initial frame or not
        self._CreateNewFrame = False
        # Exit Full Program Flag
        self._Exit = False

    # Tell the calling class to create a new init frame
    def createNewInitiFrame(self):
        self._CreateNewFrame = True
        self._Window.destroy()
        self._initImgFileName = None
        self.returnInitImage()

    # Return the init image path
    def returnInitImage(self):
        return self._initImgFileName

    # If exit selected end the whole program
    def exitFullProgram(self):
        exit(0)

    def done(self):
        cv2.destroyWindow("Init Image")
        self._Window.destroy()
    def reprompt(self):
        cv2.destroyWindow("Init Image")
        self._initImgFileName = None
        self._ConfirmationWindow.destroy()

    def confirm(self):
        self._ConfirmationWindow = tk.Toplevel(self._Window)
        self._ConfirmationWindow.title("Confirm")
        self._ConfirmationWindow.geometry("200x200")
        labelConfirmation = tk.Label(self._ConfirmationWindow, anchor="nw", text="Is this the image you want?", width=50, height=4, fg="blue")
        button_yes = tk.Button(self._ConfirmationWindow, text="yes", command=self.done)
        button_no = tk.Button(self._ConfirmationWindow, text="no", command=self.reprompt)
        labelConfirmation.pack()
        button_yes.pack()
        button_no.pack()
        try:
            cv2.namedWindow("Init Image")
            cv2.imshow("Init Image", cv2.imread(self._initImgFileName))
        except Exception as err:
            pass
    # Prompt For An Initial Image if one is avaliable
    def openFileExplorer(self):
        directory = os.getcwd()
        self._initImgFileName=filedialog.askopenfilename(initialdir=directory, title="Image Selection", filetypes=(("Images", "*.png *.jpg")
                                                                                                             ,("all files", "*.*")))
        print(self._initImgFileName)
        self._FilePathLabel.config(text="File Opened " + self._initImgFileName)
        self.confirm()

    def handleButtonPresses(self):
        # Create The Tkinter Window
        self._Window = tk.Tk()
        self._Window.title("Initial Image Prompt")
        self._Window.geometry(str(self._Width) + "x" + str(self._Height))
        self._Window.config(background="white")

        # Create Buttons
        self._FilePathLabel = tk.Label(self._Window, anchor="nw", text="File Path", width=100, height=4, fg="blue")
        button_file_explorer = tk.Button(self._Window, text="Select Image", command=self.openFileExplorer)
        button_gen_image = tk.Button(self._Window, text="Generate New Init Image", command=self.createNewInitiFrame)
        button_exit = tk.Button(self._Window, text="Exit", command=self.exitFullProgram)

        self._FilePathLabel.pack()
        button_file_explorer.pack()
        button_gen_image.pack()
        button_exit.pack()

        self._Window.mainloop()


class ConfirmationDialogBox:
    def __init__(self, promptText, height, width):
        self._Window = None
        self._promptLabel = promptText
        self.button_Yes, self.button_No = None, None
        self._Width, self._Height = 200, 200
        self.response = None

    def getResponse(self):
        return self.response
    def setResponseToYes(self):
        self.response=True
        self._Window.destroy()

    def setResponseToNo(self):
        self.response =False
        self._Window.destroy()

    def handleButtonPress(self):
        self._Window = tk.Tk()
        self._Window.title("Confirmation Dialog")
        self._Window.geometry(str(self._Height) + "x" + str(self._Width))
        self._Window.config(background="white")

        # Create Buttons
        self._PromptText = tk.Label(self._Window, anchor="center", text=self._promptLabel, width=50,
                                    height=4, fg="black").pack()
        self.button_Yes = tk.Button(self._Window, text="Yes", command=self.setResponseToYes).pack()
        self.button_No = tk.Button(self._Window, text="No", command=self.setResponseToNo).pack()


        # Main Loop
        self._Window.mainloop()