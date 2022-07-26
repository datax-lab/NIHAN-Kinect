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
        try:
            self.PROGRAM_LOG.write("\n----------------------------------------------------\n")
            currTime = time.localtime()
            timeData = time.strftime("%m-%d-%Y, %H:%M:%S", currTime)
            self.PROGRAM_LOG.write("Program running: " + timeData + "\n") 
            self.PROGRAM_LOG.write("----------------------------------------------------\n")
        except Exception as e: 
            print(f"Error in logging program ---> updateLogFile()\n{e}") 

    def closeFile(self):
        try:
            self.PROGRAM_LOG.write("\n----------------------------------------------------\n")
            currTime = time.localtime()
            timeData = time.strftime("%m-%d-%Y, %H:%M:%S", currTime)
            self.PROGRAM_LOG.write("Program finished: " + timeData + "\n") 
            self.PROGRAM_LOG.write("----------------------------------------------------\n") 
            self.PROGRAM_LOG.close()
        except Exception as e: 
           print(f"Error in logging program ---> closeFile()\n{e}") 


    def output(self,outputLoc, message):
        try: 
            outputLoc = int(outputLoc)
        except Exception as Err: 
            print("Error, incompatible type usage, expecting integer, can not output data: " + str(Err))
            return 
        try: 
            if self.PROGRAM_LOG.closed: 
                self.PROGRAM_LOG = open(self.PROGRAM_FILE, 'a')
            if(outputLoc == 0): return 
            elif(outputLoc == 1):
                print(message)
            elif(outputLoc == 2):
                self.PROGRAM_LOG.write(str(message) + "\n")
            elif(outputLoc == 3): 
                print(message)
                self.PROGRAM_LOG.write(str(message) + "\n")
            else: 
                print("Call error, expecting integer from 1 - 3 to display message")
        
        except Exception as e: 
            print(f"Error in logging program ---> output()\n{e}") 
        
        else: 
            self.PROGRAM_LOG.flush()