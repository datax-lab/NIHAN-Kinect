class obj:

    def _findBestDistanceToOffset(self) -> tuple: 
            
            if len(self.tempIV_Distance_Arr) == 0:
                return None, None

            #distance, time = list(sorted(self.tempIV_Distance_Arr))[0], list(sorted(self.tempIV_Distance_Arr.values()))[0]
            
            distance = list(sorted(self.tempIV_Distance_Arr.keys()))[0]
            time, frameCnt = self.tempIV_Distance_Arr[distance]['Time'], self.tempIV_Distance_Arr[distance]['FrameCnt']
            
            self._programLog.output(2, f"TempIV Array:\n{self.distanceOffset_Min} : {self.tempIV_Distance_Arr}\n")

            # Clear the Arrays since we should be done with them at this point
            self.tempIV_Distance_Arr.clear()
            self.instantVelocityCalculated = True
            return distance, time, frameCnt
        
        
        
    def _iVHelper2(self, distanceVar, timeVar=None) -> float: 
        distance, time = distanceVar, self._TimerMeasure.getCurrentTimeDiff()
        if timeVar is not None:
            time = timeVar
        iVelocity = self._instantVelocityHelper(distance, time, self.vi_MeasureZone)
        self._saveToDict(iVelocity, distance, time)
        return float(iVelocity)


    def calculateInstantVelocity(self): 
        
        if self._BegZoneReached is False or self.lastIvCalculated or self.frame is None :
            return 
        elif self.vf_AccelZone is None: 
            distance, time = self._BeginMeasurementZone_mm, self._Timer.getCurrentTimeDiff()
            self._programLog.output(2, f"Reached Measurement Zone at: {time} sec")
            self.vf_AccelZone = self._instantVelocityHelper(distance, time, 0)
            self.vi_MeasureZone = self.vf_AccelZone
            print(f"Initial Velocity: {self.vi_MeasureZone}")
            self._saveToDict(self.vi_MeasureZone, 0, 0)
            return 
        
        # Now to actually handle instant velocities at each (of this moment) 1 ft 
        
        '''if round(self.curr_Distance_measure_zone, 0) % self._DistanceOffset == 0:
            self._iVHelper2(self.curr_Distance_measure_zone)
            self.prevDistance = round(self.curr_Distance_measure_zone, 0)
            #self.searchingForOffset = False 
        '''
        if self.curr_Distance_measure_zone > self.distanceOffset_Min and self.searchingForOffset is False:
            
            self.searchingForOffset = True 

        elif self.curr_Distance_measure_zone > self.distanceOffset_Max and len(self.tempIV_Distance_Arr) == 0: # Check that we didnt skip the value at the current min distance, if we did do calcs
            
            self._iVHelper2(self.distanceOffset_Min)

        elif self.curr_Distance_measure_zone >= self.distanceOffset_Max:
            self.searchingForOffset = False 
            distance, time, frameCnt = self._findBestDistanceToOffset()
            #self.frameByFrame(distance, time, frameCnt)
            if distance is not None and time is not None:
                self._iVHelper2(distance, time)
            
        

        if not self.searchingForOffset and self.curr_Distance_measure_zone >= self.distanceOffset_Max:
            if ((self._DistanceOffset + self.distanceOffset_Min) < self._EndMeasurementZone_mm): 
                self.distanceOffset_Min = self.distanceOffset_Max
                self.distanceOffset_Max = self.distanceOffset_Max + self._DistanceOffset
        elif self.searchingForOffset:
            self.tempIV_Distance_Arr.update({self.curr_Distance_measure_zone: {'Time' : self._TimerMeasure.getCurrentTimeDiff(), 'FrameCnt' : self.currFrameCnt}})
            
        
    def _saveToDict(self, iVelocity, distance, time): 
        if self.lastIvCalculated is True: #or self.prevDistance == round(distance,0):
             return 
        elif (self._DistanceOffset + self.distanceOffset_Min) > self._EndMeasurementZone_mm:
            self.lastIvCalculated = True # Calculate the distance at 3942, then don't do anything else
        

        self.prevDistance = round(iVelocity, 0)

        keyVal = self._currKey
    
        if keyVal in self.iV_Dict:
            self.iV_Dict[keyVal].append({'currVelocity': iVelocity, 'distance_Measure': distance, 'CurrTime': time})
        else: 
            self.iV_Dict.update({keyVal: [{'currVelocity': iVelocity, 'distance_Measure': distance, 'CurrTime': time}]})
            
            
     # This will create a new dictionary which will tie the distances to their average speed based from each
    # program run
    def averageDict(self):
        
        currentIVHolder, currentTimeHolder, currDistance = 0,0,0
        #{ key: [{}] }
        data = self.iV_Dict[self._StartKey]
        
        # -> Note that data is currently a list of dicts
        # Iterate through each element in this list of dicts, and then grab the currVelocity 
        for j ,items in enumerate(data): # -> var 'items' should be a dictionary
            
            currentIVHolder = items['currVelocity']
            currentTimeHolder = items['CurrTime']
            currDistance = items['distance_Measure']

            if len(list(self.iV_Dict)) > 1: # Only iterate through if there is more than one program run time of the same patient
                currentIVHolder, currentTimeHolder, currDistance = 0, 0, 0 
                # Now I need to loop through all the other keys and element that is equal to the current element index
                for keys in range(self._StartKey, self._currKey):
                    if keys in self.iV_Dict: 
                        # Get the Instant Velocities Average for current distance
                        currentIVHolder += self.iV_Dict[keys][j]['currVelocity']
                        # Get the Time Averages for current distance
                        currentTimeHolder += self.iV_Dict[keys][j]['CurrTime']  
                        # Get Distance
                        currDistance += self.iV_Dict[keys][j]['distance_Measure']
                # Dict average structure
                # "Results": [{Distance: 3, Instant Velocity: 0.75, Time: 2}, {Distance: 3, Instant Velocity: 0.75, Time: 2}]
                currentIVHolder /= len(list(self.iV_Dict))
                currentTimeHolder /= len(list(self.iV_Dict))
                currDistance /= len(list(self.iV_Dict))
                
            # Should only run once
            if "Results" in self._IV_Dict_Averages:
                self._IV_Dict_Averages['Results'].append({'Distance' : currDistance,'Time': currentTimeHolder, 'Instant Velocity': currentIVHolder})
            # Should run thereafter
            else: 
                self._IV_Dict_Averages.update({'Results': [{'Distance': currDistance, 'Time': currentTimeHolder, 'Instant Velocity': currentIVHolder}]})


       # print(self._IV_Dict_Averages, end="\n\n\n")     