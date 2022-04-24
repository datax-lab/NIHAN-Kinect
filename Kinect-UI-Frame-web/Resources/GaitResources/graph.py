from logging import raiseExceptions
import matplotlib.pyplot as plt


_colorSchemes = ["red", "blue", "green", "purple", "orange", "pink", "black", "yellow"]


class Graph: 
    def __init__(self): 
        self._xData, self._yData = [], []
        self._GraphName, self._xAxisName, self._yAxisName = None, None, None 
        self._GraphStorage, self._graphID = {}, 0
        
        self._Titles = ["xValuesF", "yValuesF", "xValuesIV", "yValuesIV"] 


    def setGraphID(self, id: int): 
        self._graphID = id 


    def insertToGraph(self, xyDataF: tuple[list, list], xyDataIV : tuple[list, list], id: int): 
        self._GraphStorage.update({id: {self._Titles[0] : xyDataF[0], self._Titles[1] : xyDataF[1], self._Titles[2]: xyDataIV[0], self._Titles[3] : xyDataIV[1]}})
   

    def setupLabels(self, graphName, xAxisName, yAxisName): 
        self._GraphName, self._xAxisName, self._yAxisName = graphName, xAxisName, yAxisName

        

    def showGraph(self, id=None, showLegendBool=False): 
        
        # Setup The Graph 
        plt.title(self._GraphName)
        plt.xlabel(self._xAxisName)
        plt.ylabel(self._yAxisName)
      
        if id is not None: 
            x_Data, y_Data = self._GraphStorage[id][self._Titles[0]], self._GraphStorage[id][self._Titles[1]]
            plt.plot(x_Data, y_Data, color=_colorSchemes[id%len(_colorSchemes)], label=f"Test {id} - Frame By Frame", marker='o')
            # IV 
            x_Data, y_Data = self._GraphStorage[id][self._Titles[2]], self._GraphStorage[id][self._Titles[3]]
            plt.plot(x_Data, y_Data, color=_colorSchemes[id%len(_colorSchemes)], label=f"Test {id} - Instant Velocity", marker='x')
        else:
            # Place The Points on The Plot
            for i, keyVal in enumerate(self._GraphStorage.keys()): 
                # Frame By Frame
                x_Data, y_Data = self._GraphStorage[keyVal][self._Titles[0]], self._GraphStorage[keyVal][self._Titles[1]]
                plt.plot(x_Data, y_Data, color=_colorSchemes[i%len(_colorSchemes)], label=f"Test {keyVal} - Frame By Frame", marker='o')
                # IV 
                x_Data, y_Data = self._GraphStorage[keyVal][self._Titles[2]], self._GraphStorage[keyVal][self._Titles[3]]
                plt.plot(x_Data, y_Data, color=_colorSchemes[i%len(_colorSchemes)], label=f"Test {keyVal} - Instant Velocity", marker='x')
            
       
        # Show the Graph
        if showLegendBool:
            plt.legend()

        plt.show()




if __name__ =="__main__":
    
    graphing = Graph()
    data1x, data1y = [i for i in range(0,10)], [i for i in range(10,20)]
    data2x, data2y = [i for i in range(10,20)], [i for i in range(20,30)]
    data3x, data3y = [i for i in range(20,30)], [i for i in range(30,40)]

    graphing.insertToGraph((data1x, data1y), 0)
    graphing.insertToGraph((data2x, data2y), 1)
    graphing.insertToGraph((data3x, data3y), 2)

    graphing.setupLabels("Test Graph", "valX", "valY")
    graphing.showGraph()


    data1x, data1y = [i for i in range(50,100)], [i for i in range(10,60)]
    data2x, data2y = [i for i in range(60,90)], [i for i in range(20,50)]
    data3x, data3y = [i for i in range(50,70)], [i for i in range(30,50)]

    graphing.insertToGraph((data1x, data1y), 3)
    graphing.insertToGraph((data2x, data2y), 4)
    graphing.insertToGraph((data3x, data3y), 5)

    graphing.showGraph()