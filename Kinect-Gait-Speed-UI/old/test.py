
class Sample:
    def __init__(self): 
        self._dictHolder = {}
        self._ProgramCounter = 0 

    def data(self):
        item_4 = {
            1 : [{
                'data1' : 2,
                'data2' : 3,
                'data' : 4,
            }, 
            
            {
                'data1' : 5,
                'data2' : 6,
                'data' : 7,
            }, 
            
            ],

            2: [{
                'data1' : 8,
                'data2' : 9,
                'data' : 10,
            }, 
            
            {
                'data1' : 11,
                'data2' : 12,
                'data' : 13,
            }, 
            
            ],
        }

        
        self._dictHolder.update(item_4)
        print(type(self._dictHolder))
        #print(len(list(self._dictHolder)))
        print(type(self._dictHolder[1][0]))
        
        print(self._dictHolder[1][0]['data1'])
        print(self._dictHolder)


test = Sample()
test.data()
        