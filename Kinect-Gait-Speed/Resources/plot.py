import matplotlib.pyplot as plt


class PLOTTER: 
    def __init__(self):
        self.x_Points = [] 
        self.y_Points = []
        self.plotDisplayed = False 
    
    def insertXY(self, xy_tuple): 
        if len(xy_tuple) < 2: 
           raise("Error, please provide a tuple of xy points, x being at index 0 and y at index 1")
        if xy_tuple[0] is not None and xy_tuple[1] is not None:
            self.x_Points.append(xy_tuple[0])
            self.y_Points.append(xy_tuple[1])
    
    def getSize(self):
        return len(self.x_Points) # It doesnt necessarily matter whether we use the x or y, since their len should be equal all the time
        

    def plotPts(self, fileName, xLabel, yLabel): 
        if len(self.x_Points) < 0  or len(self.y_Points) < 0:
            print("No Data")
            return 
        # Handle Plotting if there is data to plot
        plt.plot(self.x_Points, self.y_Points, marker='o')
        plt.xlabel(xLabel)
        plt.ylabel(yLabel)
        plt.savefig(fileName)
        self.plotDisplayed = True 
        plt.show()
       

