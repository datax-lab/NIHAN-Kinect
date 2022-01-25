from datetime import datetime
from logging import exception
from numpy import character
from pygame import Cursor
import pymongo
from pymongo import MongoClient

import json 
import os 
class DataHandler : 
    def __init__(self):
        passwdFile = open(os.path.join(os.path.join(os.getcwd(), "secrets"), "secrets.json"))
        linkFile = json.load(passwdFile)

        self._ConnectionString = linkFile["ConnectionString"]
        #self._ConnectionString =           # localhost goes here
        self._DatabaseName = "Kinect"
        
        # Collection That I will Use
        self._patientCollection = "Patient-Information"
        self._patientResults = "Patient-Results"
        
        self._client = None 


        # Connect the DataBase 
        self.connect()

    def connect(self): 
        self._client = MongoClient(self._ConnectionString)

        try: 
            self._client.server_info()
        except exception as err: 
            print(f"Unable to Connect to Server {err}")
            exit(-1)
        
        # Link the Database 
        self._DatabaseName = self._client[self._DatabaseName]
        self._patientCollection = self._DatabaseName[self._patientCollection]
        self._patientResults = self._DatabaseName[self._patientResults]

   
    def cleanInput(self, ptInfo) -> tuple[str,str]:
        ptID, ptName = ptInfo

        cleanedName, cleanedNum = " ".join(ptName.split()), ''

        for numbers in str(ptID):
            if numbers.isalnum():
                cleanedNum += str(numbers)
            
        return str(cleanedNum), str(cleanedName)

    


    # Just to Check if a patient exists and then return the reference
    def findPatient(self, ptInfo) -> tuple[int, pymongo.CursorType]: 
        ptID, ptName = self.cleanInput(ptInfo)
        name = f"^{ptName}$"
        patient = self._patientCollection.find({'$and' : [{'PatientID' : ptID}, {'PatientName' : {'$regex': name, '$options' : 'i'}}]})
        
        matchCnt = len(list(patient))

        if matchCnt == 0: 
            return 0, patient
        elif matchCnt > 1:
            print("Error, duplicate patient found!")
            return len(list(patient)), patient
        elif matchCnt == 1: 
            return 1, patient 
        
        


    def queryKyphosisResults(self, patient) -> list: 
        
        kyphArr = []
        # Since the patients object should be a pointer reference, we will have to parse through all data that lives in this
        for items in patient:
            kyphArr.append(items['Results.Kyphosis Index'])
        
        return kyphArr
    
    # Since Gaits Results have multiple fields we will give the choice if we want all of them or just a single one of them 
    # optionChoices: 
    # GaitResults
    # AverageSpeed   
    def queryGaitResults(self, patient, optionChoice) -> tuple:
        '''
        if optionChoice == "DISTANCES":
            distanceList = []
            for items in patient:
                distanceList.append(items['Results.Gait Results.Distances'])
        if optionChoice == "VELOCITIES": 
            velocityArr = []
            for items in patient: 
                velocityArr.append(items['Results.Times'])
        '''
        results, avgSpdArr = [], []
        if optionChoice == "GAITRESULTS":
            for items in patient: 
                results.append(items["Results.Gait Results"]) # This is a list of dictionaries
        if optionChoice == "AverageSpeed": 
            for items in patient:
                avgSpdArr.append(items["Results.Gait Results.Average Speed"])
        
        return results, avgSpdArr


    ##############################
    #   Data Creation Functions  #
    ##############################
    
    def createPatient(self, ptInfo):
        # Query and make sure this new patient is really not in the database
        matchCnt, _ = self.findPatient(ptInfo)
        
        if matchCnt != 0:
            return -1 

        # Create the patient to add in patient database
        patient_item = {
            "PatientID" : str(ptInfo[0]),
            "PatientName" : str(ptInfo[1]),
            
        } 

        # Upload to the patient database 
        self._patientCollection.insert_one(patient_item)

        return 1
    

    # By the time this is called I should have verified the patient already exists
    def uploadResults(self, ptInfo, gaitDistances, gaitTimesArr, gaitInstantVeloArr, gaitAvgSpd, kyphosisIndex):
        
        # Clean The Name and ID 
        ptID, ptName = self.cleanInput(ptInfo)
        
        # Lets Format the Data First 
        date = datetime.now().date().isoformat()

        patient_update = {
            "PatientID" : str(ptID),
            "PatientName" : str(ptName),
            "Date" : date,
            "Results" : {
                "Gait Results": {
                    "Distances" : gaitDistances,
                    "Times" : gaitTimesArr, 
                    "Instant Velocities" : gaitInstantVeloArr, 
                    "Average Speed" : gaitAvgSpd,
                },

                "Kyphosis Index" : kyphosisIndex,

            },

        }

        # Check if we have data matching the same date
        name = f"^{ptName}$"
        if len(list(self._patientResults.find({'$and' : [{"PatientID": ptID}, {"PatientName": {'$regex': name, '$options' : 'i'}}, {"Date" : date}]}))) > 0: 
            if gaitTimesArr is not None:
                self._patientResults.update_many({'$and' : [{"PatientID": ptID}, {"Date" : date}, {"PatientName": {'$regex': name, '$options' : 'i'}}]}, 
                                        {'$set': {"Results.Gait Results" : {"Distances": gaitDistances, "Times": gaitTimesArr, "Instant Velocities" : gaitInstantVeloArr, "Average Speed": gaitAvgSpd}}})
            elif  kyphosisIndex is not None: 
                self._patientResults.update_many({'$and': [{"PatientID": ptID}, {"Date": date}, {"PatientName": {'$regex': name, '$options' : 'i'}}]}, 
                                                    {'$set' : {"Results.Kyphosis Index": kyphosisIndex}})

        else:
            # Since we should have already verified that this patient exists, we can just simply upload this new document, if there were no duplicates of the same day
            self._patientResults.insert_one(patient_update)
   
                 

if __name__ == "__main__":
    data = DataHandler()
    data.createPatient((17685, "Cedric Men")) 
    patientInfo = (17685, "Cedric Men")
    # Generate Random Results 
    gaitTimes = [1,2,3]
    gaitIV = [0.76,0.91,0.65]
    gaitAvg = 1.15

    data.uploadResults((17685, "Cedric Men"), gaitTimes, gaitIV, gaitAvg, 48.4)
        

