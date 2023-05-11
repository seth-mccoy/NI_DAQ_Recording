import nidaqmx
import time
from timeit import default_timer as timer
from pyfirmata2 import Arduino
import datetime

sys=nidaqmx.system.System.local()
dev=sys.devices[3]
task=nidaqmx.Task('AcquireVoltage')
task.ai_channels.add_ai_voltage_chan(dev.name+'/ai0', 'Volt 1')
task.ai_channels.add_ai_voltage_chan(dev.name+'/ai1', 'Volt 0')
task.timing.cfg_samp_clk_timing(50000, samps_per_chan=25000)
measurement={}
measurement['Voltage 1']=[]
measurement['Timestamp']=[]
measurement['Voltage 2']=[]
measurement['Power']=[]

board=Arduino(Arduino.AUTODETECT)
board.digital[12].write(0)
init=timer()
previouslyStable=False
currentlyStable=False
powerAtTime1=timer()-init
outputHigh=False
measuring=False
measurementCounter=0
postMeasurementActive=False
preMeasurementActive=True
highHold=False
numSteps=1
step=0
previousPower=0

while True:
    ls=task.read()
    timestamp=timer()-init
    voltage=ls[0]*100
    current=110.243*(ls[1]-2.5)-2.9340064
    power=current*voltage
    if measuring:
        measurement['Voltage 1'].append(ls[0])
        measurement['Timestamp'].append(timestamp)
        measurement['Voltage 2'].append(ls[1])
        measurement['Power'].append(power)
    elif postMeasurementActive:
        if measurementCounter<12000:
            measurementCounter+=1
            measurement['Voltage 1'].append(ls[0])
            measurement['Timestamp'].append(timestamp)
            measurement['Voltage 2'].append(ls[1])
            measurement['Power'].append(power)
        else:
            postMeasurementActive=False
    elif preMeasurementActive and len(measurement['Voltage 1'])>11999:
        measurement['Voltage 1'].pop(0).append(ls[0])
        measurement['Timestamp'].pop(0).append(timestamp)
        measurement['Voltage 2'].pop(0).append(ls[1])
        measurement['Power'].pop(0).append(power)
    elif preMeasurementActive and len(measurement['Voltage 1'])<11999:
        measurement['Voltage 1'].append(ls[0])
        measurement['Timestamp'].append(timestamp)
        measurement['Voltage 2'].append(ls[1])
        measurement['Power'].append(power)
    else:
        pass
    
    
    
    avgPower=0
    if len(measurement['Power'])>30:
        for i in range(1,31):
            avgPower+=measurement['Power'][-i]
        avgPower=avgPower/30
        
    if power>2000 or power<-2000:
        preMeasurementActive=False
        measuring=True
        previousPower=power
        if abs(power) > abs(avgPower*0.9) and abs(power) < abs(avgPower*1.1):
            if timer()-powerAtTime1>60:
                currentlyStable=True
                print('Condition Met')
                measuring=False
        else:
            currentlyStable=False
            powerAtTime1=timer()-init
    if currentlyStable and not previouslyStable:
        measurementCounter=0
        postMeasurementActive=True
        previouslyStable=currentlyStable
        outputHigh=True
    elif previouslyStable and not currentlyStable:
        previouslyStable=currentlyStable
    else:
        outputHigh=False

    if outputHigh:
        board.digital[12].write(1)
        highHold=True
        startTime=timer()
        step+=1
        powerAtTime1=timer()-init
    if highHold:
        if timer()-startTime>5:
            highHold=False
            board.digital[12].write(0)
            if step==numSteps:
                now=datetime.datetime.now()
                with open(f'Data_from_python_{now.hour}-{now.minute}-{now.second}.txt', 'a+') as myFile:
                    myFile.write('Timestamp,Voltage 1,Voltage 2,Power\n')
                    for i in range(len(measurement['Voltage 1'])):
                        myFile.write(str(measurement['Timestamp'][i]))
                        myFile.write(',')
                        myFile.write(str(measurement['Voltage 1'][i]))
                        myFile.write(',')
                        myFile.write(str(measurement['Voltage 1'][i]))
                        myFile.write(',')
                        myFile.write(str(measurement['Power'][i]))
                        myFile.write('\n')
                print('stop')
                break