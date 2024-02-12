"""
Author: Joe Ingham
Date Created: 08/02/2024
Description: USB Power Meter GUI - allows a user to continually check the measured power from a power meter without it hanging the PC.
"""





from PyQt6 import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import sys
import pyvisa as pv 
import time
from threading import Thread
import queue
import os



q = queue.Queue()

stopFlag = 0
exitFlag = 0




#Application Controller
class app(QApplication):

    #Initialiser
    def __init__(self, args):       
        global stopFlag
        super(app, self).__init__(args)
        
        

        #Open the first window
        mw = main_window(self)
        mw.show()
        sys.exit(self.exec())


#Main window the USB Power Meter 
class main_window(QWidget):

    def __init__(self, master):
        global q 

        super(main_window, self).__init__()
        
        #Set the window title
        self.setWindowTitle("USB Power Meter Display")

        #Determine the layout (i.e. grid style)
        layout = QGridLayout()
        

        #Place the widgets in the layout (i.e. buttons/textboxes etc)
        #AVERAGE
        avgLabel = QLabel("Average")
        avgLabel.setFont(QFont("Arial", 23))
        avgLabel.setStyleSheet("color: rgb(255,199,62);")
        layout.addWidget(avgLabel, 0, 0)

        self.avgBox = QLineEdit(self)
        self.avgBox.setText("10")
        self.avgBox.setStyleSheet("color: rgb(255,199,62);")
        self.avgBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avgBox.setFont(QFont("Arial", 23))
        self.avgBox.setFixedWidth(150)
        layout.addWidget(self.avgBox, 0, 1)

        #OFFSET
        layoutLabel = QLabel("Offset")
        layoutLabel.setFont(QFont("Arial", 23))
        layoutLabel.setStyleSheet("color: rgb(255,199,62);")
        layout.addWidget(layoutLabel, 1, 0)

        self.offsetBox = QLineEdit(self)
        self.offsetBox.setText("0")
        self.offsetBox.setStyleSheet("color: rgb(255,199,62);")
        self.offsetBox.setFont(QFont("Arial", 23))
        self.offsetBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.offsetBox.setFixedWidth(150)
        layout.addWidget(self.offsetBox, 1, 1)


        dbLabel = QLabel("dB")
        dbLabel.setFont(QFont("Arial", 23))
        dbLabel.setStyleSheet("color: rgb(255,199,62);")
        layout.addWidget(dbLabel, 1, 2)

        #FREQUENCY
        freqLabel = QLabel("Frequency")
        freqLabel.setStyleSheet("color: rgb(255,199,62);")
        freqLabel.setFont(QFont("Arial", 23))
        layout.addWidget(freqLabel, 2, 0)

        self.frequencyBox = QLineEdit(self)
        self.frequencyBox.setText("5")
        self.frequencyBox.setStyleSheet("color: rgb(255,199,62);")
        self.frequencyBox.setFont(QFont("Arial", 23))
        self.frequencyBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frequencyBox.setFixedWidth(150)
        layout.addWidget(self.frequencyBox, 2, 1)

        GHZLabel = QLabel("GHz")
        GHZLabel.setFont(QFont("Arial", 23))
        GHZLabel.setStyleSheet("color: rgb(255,199,62);")
        layout.addWidget(GHZLabel, 2, 2)


        #DELAY
        delayLabel = QLabel("Delay")
        delayLabel.setFont(QFont("Arial", 23))
        delayLabel.setStyleSheet("color: rgb(255,199,62);")
        layout.addWidget(delayLabel, 3, 0)

        self.delayBox = QLineEdit(self)
        self.delayBox.setText("0.5")
        self.delayBox.setStyleSheet("color: rgb(255,199,62);")
        self.delayBox.setFont(QFont("Arial", 23))
        self.delayBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.delayBox.setFixedWidth(150)
        layout.addWidget(self.delayBox, 3, 1)

        sLabel = QLabel("S")
        sLabel.setFont(QFont("Arial", 23))
        sLabel.setStyleSheet("color: rgb(255,199,62);")
        layout.addWidget(sLabel, 3, 2)


        #SINGLE READING BUTTON
        singleRead = QPushButton(self)
        singleRead.setText("Single")
        singleRead.setStyleSheet("color: rgb(255,255,255); background-color:rgb(255,137,14); border: 2px rgb(188,188,188);")
        singleRead.setFont(QFont("Arial", 18))
        singleRead.clicked.connect(self.singlePMRead)
        layout.addWidget(singleRead, 4, 2)


        #continuous READING BUTTON 
        continuousRead = QPushButton(self)
        continuousRead.setText("Continuous")
        continuousRead.setStyleSheet("color: rgb(255,255,255); background-color:rgb(255,137,14); border: 2px rgb(188,188,188);")
        continuousRead.setFont(QFont("Arial", 18))
        continuousRead.clicked.connect(self.continuousPMRead)
        layout.addWidget(continuousRead, 4, 3)


        #ERROR LABEL (also displays power reading)
        self.errLabel = QLabel("PRESS A BUTTON")
        self.errLabel.setFont(QFont("Arial", 34))
        self.errLabel.setStyleSheet("color: rgb(255,199,62);")
        self.errLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        q.put(self.errLabel)
        layout.addWidget(self.errLabel, 1, 3, 3, 5)


        #STOP BUTTON
        self.stopButton = QPushButton(self)
        self.stopButton.setText("Stop")
        self.stopButton.setStyleSheet("color: rgb(255,255,255); background-color:rgb(255,137,14); border: 2px rgb(188,188,188);")
        self.stopButton.setFont(QFont("Arial", 18))
        self.stopButton.clicked.connect(self.stopContinuous)
        self.stopButton.setDisabled(True)
        layout.addWidget(self.stopButton, 5, 3)


        #Place the widgets into the layout
        self.master = master
        self.setStyleSheet("background-color: black;")
        
        self.setLayout(layout)
        
        
    def closeEvent(self, event):
        global exitFlag

        exitFlag = 1

        event.accept() 

        os._exit(0)



    #Connects to a Power Meter and sets it up- returns the power meter object
    def connectToPM(self):

        
        #Check if a valid power meter is connected
        det_rm = pv.ResourceManager()
        res_list = det_rm.list_resources()

        print(res_list)

        pm_detected = 0        


        for dev in res_list:
            print(f"{dev}")
            print(f"-{dev[:4]}-----{dev[22:24]}-")

            if dev[:4] == "USB0" and dev[22:24] == "MY":
                
                
                pm_id = dev
                self.errLabel.setStyleSheet("color: black")
                pm_detected = self.testConnect(det_rm, pm_id)
                #pm_detected = 1
                if pm_detected:
                    break

        
        if not pm_detected:
            self.errLabel.setText("No PM detected - Restart App")
            self.errLabel.setStyleSheet("color: red")
            return False

        

        try:

            print(pm_id)
            #Connect to the power meter
            pm = det_rm.open_resource(pm_id)
            

          
            #Setup the power meter
            #Offset
            pm.write(f"CALCulate:GAIN {self.offsetBox.text()}")
            #Frequency
            pm.write(f"SENS:Freq {self.frequencyBox.text()} GHZ")

            #Trigger
            pm.write(f"TRIG:LEV:AUTO 1")
            pm.write(f"TRIG:DEL")

        
        except:
            self.errLabel.setText = "Error setting up Power Meter"
            self. errLabel.setStyleSheet("color: red")
            

        #det_rm.close()

        #Return the power meter object
        return pm


    #Check if its a valid connection
    def testConnect(self, detRM, pmID):
        try:
            pm = detRM.open_resource(pmID)

            test = pm.query("*IDN?")

            if test:
                return 1


        except Exception as e:
            print(e)
            return 0





    #Reads one measurement from a power meter
    def singlePMRead(self):
        global stopFlag
        stopFlag = 1

        pm = self.connectToPM()

        if not pm:
            return
        
        #Take one measurement

        pm.write("INIT1:CONT 1")

        result = pm.query("FETC1:POW:AC?")
        print(result)

        try:
            result = float(result) + float(self.offsetBox.text())
        except:
            self.errLabel.setText("Invalid Offset")
            self.errLabel.setStyleSheet("color: red")
            return
        
        self.errLabel.setText(f"{round(result,2)} dBm")
        self.errLabel.setStyleSheet("color: rgb(255,199,62);")


        pm.close()
        
        



    #Continually reads from a power meter
    def continuousPMRead(self):

        global q
        global stopFlag

        stopFlag = 0
        self.stopButton.setDisabled(False)      


        pm = self.connectToPM()

        if not pm:
            return       

        try:
            averageNum = float(self.avgBox.text())
        except:
            self.errLabel.setText = "Invalid Average"
            self.errLabel.setStyleSheet("color: red")
            return
      
        
        self.powerList = []

        pm.write("INIT1:CONT 1")     

        #Start a timer
        start_time = time.time()

        #Go forever
        while True:
            QApplication.processEvents()

            #If enough time has passed take another reading
            if (curr_time := time.time() - start_time) >= float(self.delayBox.text()):

                #Read the current power value
                result = pm.query("FETC1:POW:AC?")

                #Try add the offset
                try:
                    result = float(result) + float(self.offsetBox.text())
                except:
                    self.errLabel.setText("Invalid Offset")
                    self.errLabel.setStyleSheet("color: red")
                    return

                #add to total or replace first value?
                if len(self.powerList) == averageNum:
                    self.powerList.pop(0)
                    self.powerList.append(result)
                else:
                    self.powerList.append(result) 


                q.put(self.powerList)                   

                start_time = time.time()

                if stopFlag == 1:
                    pm.close()
                    return
    


    #Stops the continuous reading
    def stopContinuous(self):
        global stopFlag

        stopFlag = 1
        self.stopButton.setDisabled(True)
        os._exit(0)



#Seperate thread function that calcualtes the running average and updates the label on the GUI
def updatePwrLabel():

    global q 
    global stopFlag
    global exitFlag

    errLabel = q.get()

    #Runs forever
    while True:           
        #If exit flag goes high - close the thread
        if exitFlag:
            return

        #If the other thread isnt telling it to stop, calc the avg
        if stopFlag == 0:

            powerList = q.get()
            print(powerList)

            #Calculate the average power
            total = 0
            for i in powerList:
                total = total + i

            powerAvg = total / len(powerList)

            print(f"{powerAvg} dBm")

            #Change the label
            errLabel.setText(f"{round(powerAvg,2)} dBm")
            errLabel.setStyleSheet("color: rgb(255,199,62);")




if __name__ == "__main__":
    

    t1 = Thread(target = app, args=[sys.argv])
    t2 = Thread(target = updatePwrLabel)
    

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    sys.exit()




