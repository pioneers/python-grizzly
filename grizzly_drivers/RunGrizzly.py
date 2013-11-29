from libgrizzlyusb import *
from xbox_read import event_stream

g = GrizzlyUSB()
grizzly = Grizzly(g)
grizzly.setMode(ControlMode.POSITION_PID, DriveMode.DRIVE_BRAKE)
grizzly.InitPID(2, .001, 5)
inputs = event_stream(4000)

for event in inputs:
    if event.key == "Y2":
        throttle = int(event.value) / 4
        grizzly.setSpeed(throttle)
