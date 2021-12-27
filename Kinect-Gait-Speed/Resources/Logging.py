import os 
import time

class LOGGING: 

    def __init__(self, logFileName = None, checkForAFile = False):
        
        writeType = "w"
        if logFileName == None: 
            self.PROGRAM_FILE = "Program-LogFile.txt"
        else: 
            if os.path.exists(logFileName): 
                #print("Error, creating logfile, it already exists, opening in append mode...")
                writeType = "a"
            self.PROGRAM_FILE = logFileName 

        self.PROGRAM_LOG = open(self.PROGRAM_FILE, writeType)
        self.updateLogFile()

            
        
    def updateLogFile(self): 
        self.PROGRAM_LOG.write("\n----------------------------------------------------\n")
        currTime = time.localtime()
        timeData = time.strftime("%m-%d-%Y, %H:%M:%S", currTime)
        self.PROGRAM_LOG.write("Program running: " + timeData + "\n") 
        self.PROGRAM_LOG.write("----------------------------------------------------\n")

    def closeFile(self):
        self.PROGRAM_LOG.write("\n----------------------------------------------------\n")
        currTime = time.localtime()
        timeData = time.strftime("%m-%d-%Y, %H:%M:%S", currTime)
        self.PROGRAM_LOG.write("Program finished: " + timeData + "\n") 
        self.PROGRAM_LOG.write("----------------------------------------------------\n") 
        self.PROGRAM_LOG.close()


    def output(self,outputLoc, message):
        try: 
            outputLoc = int(outputLoc)
        except Exception as Err: 
            print("Error, incompatible type usage, expecting integer, can not output data: " + str(Err))
            return 

        if self.PROGRAM_LOG.closed: 
            self.PROGRAM_LOG = open(self.PROGRAM_FILE, 'a')
        if(outputLoc == 1):
            print(message)
        elif(outputLoc == 2):
            self.PROGRAM_LOG.write(str(message) + "\n")
        elif(outputLoc == 3): 
            print(message)
            self.PROGRAM_LOG.write(str(message) + "\n")
        else: 
            print("Call error, expecting integer from 1 - 3 to display message")