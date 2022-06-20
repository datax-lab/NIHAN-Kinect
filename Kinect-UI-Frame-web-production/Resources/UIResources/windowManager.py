import tkinter as tk
import tkinter.font as tkFont
from tkinter import filedialog

import os, cv2



class ConfirmationDialog:
    def __init__(self):
        # Variables 
        self.response = None 
        self.height, self.width = 160, 500
        self.root = None

    def handleButtonPresses(self, textOut):
        self.root = tk.Tk()
        self.root.title("Confirmation")
        #setting window size
        screenwidth = self.root.winfo_screenwidth()
        screenheight = self.root.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (self.width, self.height, (screenwidth - self.width) / 2, (screenheight - self.height) / 2)
        self.root.geometry(alignstr)
        self.root.resizable(width=False, height=False)

        GLabel_912=tk.Label(self.root)
        ft = tkFont.Font(family='Times',size=10)
        GLabel_912["font"] = ft
        GLabel_912["fg"] = "#333333"
        GLabel_912["justify"] = "center"
        GLabel_912["text"] = textOut
        GLabel_912.place(x=70,y=30,width=333,height=54)

        GButton_260=tk.Button(self.root)
        GButton_260["bg"] = "#efefef"
        ft = tkFont.Font(family='Times',size=10)
        GButton_260["font"] = ft
        GButton_260["fg"] = "#000000"
        GButton_260["justify"] = "center"
        GButton_260["text"] = "Confirm"
        GButton_260.place(x=90,y=110,width=70,height=25)
        GButton_260["command"] = self.confirmed

        GButton_198=tk.Button(self.root)
        GButton_198["bg"] = "#efefef"
        ft = tkFont.Font(family='Times',size=10)
        GButton_198["font"] = ft
        GButton_198["fg"] = "#000000"
        GButton_198["justify"] = "center"
        GButton_198["text"] = "Cancel"
        GButton_198.place(x=310,y=110,width=70,height=25)
        GButton_198["command"] = self.canceled

        self.root.mainloop()


    def confirmed(self):
        self.response= True
        self.root.destroy()


    def canceled(self):
        self.response = False
        self.root.destroy()

    def getResponse(self) -> bool: 
        return self.response
    
        

class FileDialog:
    def __init__(self):
        # Response Var
        self.response = None 
        self._initImgFileName = None 
        
        # Windows
        self.height, self.width = 160, 500
        self.root, self.window2 = None, None
       
       

    def handleButtonPresses(self):
        self.root = tk.Tk()
        self.root.title("Initilization Image Selector")
        screenwidth = self.root.winfo_screenwidth()
        screenheight = self.root.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (self.width, self.height, (screenwidth - self.width) / 2, (screenheight - self.height) / 2)
        self.root.geometry(alignstr)
        self.root.resizable(width=False, height=False)

        GLabel_912=tk.Label(self.root)
        ft = tkFont.Font(family='Times',size=10)
        GLabel_912["font"] = ft
        GLabel_912["fg"] = "#333333"
        GLabel_912["justify"] = "center"
        GLabel_912["text"] = "Please Select An Option: "
        GLabel_912.place(x=70,y=30,width=333,height=54)

        GButton_260=tk.Button(self.root)
        GButton_260["bg"] = "#efefef"
        ft = tkFont.Font(family='Times',size=10)
        GButton_260["font"] = ft
        GButton_260["fg"] = "#000000"
        GButton_260["justify"] = "center"
        GButton_260["text"] = "Generate Image"
        GButton_260.place(x=30,y=110,width=120,height=25)
        GButton_260["command"] = self.generateImg

        GButton_198=tk.Button(self.root)
        GButton_198["bg"] = "#efefef"
        ft = tkFont.Font(family='Times',size=10)
        GButton_198["font"] = ft
        GButton_198["fg"] = "#000000"
        GButton_198["justify"] = "center"
        GButton_198["text"] = "Select Image"
        GButton_198.place(x=200,y=110,width=120,height=25)
        GButton_198["command"] = self.openFileExplorer

        GButton_883=tk.Button(self.root)
        GButton_883["bg"] = "#efefef"
        ft = tkFont.Font(family='Times',size=10)
        GButton_883["font"] = ft
        GButton_883["fg"] = "#000000"
        GButton_883["justify"] = "center"
        GButton_883["text"] = "Exit"
        GButton_883.place(x=360,y=110,width=120,height=25)
        GButton_883["command"] = self.exitFullProgram

        self.root.mainloop()

    def done(self):
        cv2.destroyWindow("Init Image")
        self.root.destroy()

    def reprompt(self):
        cv2.destroyWindow("Init Image")
        self._initImgFileName = None
        self.window2.destroy()

    def confirm(self):
        self.window2 = tk.Toplevel(self.root)
        self.window2.title("Confirmation")
        #setting window size
        screenwidth = self.window2.winfo_screenwidth()
        screenheight = self.window2.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (self.width, self.height, (screenwidth - self.width) / 2, (screenheight - self.height) / 2)
        self.window2.geometry(alignstr)
        self.window2.resizable(width=False, height=False)

        GLabel_912=tk.Label(self.window2)
        ft = tkFont.Font(family='Times',size=10)
        GLabel_912["font"] = ft
        GLabel_912["fg"] = "#333333"
        GLabel_912["justify"] = "center"
        GLabel_912["text"] = "Is this the image you want?"
        GLabel_912.place(x=70,y=30,width=333,height=54)

        GButton_260=tk.Button(self.window2)
        GButton_260["bg"] = "#efefef"
        ft = tkFont.Font(family='Times',size=10)
        GButton_260["font"] = ft
        GButton_260["fg"] = "#000000"
        GButton_260["justify"] = "center"
        GButton_260["text"] = "yes"
        GButton_260.place(x=110,y=110,width=70,height=25)
        GButton_260["command"] = self.done

        GButton_883=tk.Button(self.window2)
        GButton_883["bg"] = "#efefef"
        ft = tkFont.Font(family='Times',size=10)
        GButton_883["font"] = ft
        GButton_883["fg"] = "#000000"
        GButton_883["justify"] = "center"
        GButton_883["text"] = "no"
        GButton_883.place(x=290,y=110,width=70,height=25)
        GButton_883["command"] = self.reprompt
        try:
            cv2.namedWindow("Init Image")
            cv2.imshow("Init Image", cv2.imread(self._initImgFileName))
        except Exception as err:
            pass

    def exitFullProgram(self):
        self._initImgFileName = "PROGEXIT"
        self.root.destroy()
        

    def openFileExplorer(self):
        directory = os.getcwd()
        self._initImgFileName=filedialog.askopenfilename(initialdir=directory, title="Image Selection", filetypes=(("Images", "*.png *.jpg")
                                                                                                                ,("all files", "*.*")))
        self.confirm()


    def generateImg(self):
        self._initImgFileName = None 
        self.root.destroy()



    def getFileName(self) -> str: 
        return self._initImgFileName