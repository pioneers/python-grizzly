#!/usr/bin/env python

from libgrizzlyusb import *
from xbox_read import event_stream

grizzly = Grizzly()
grizzly.set_mode(ControlMode.NO_PID, DriveMode.DRIVE_BRAKE)
grizzly.limit_acceleration(20)
grizzly.limit_current(5)

inputs = event_stream(4000)
for event in inputs:
    if event.key == "Y2":
        throttle = int(event.value) / 327
        grizzly.set_target(throttle)
    if event.key == "A":
        print("Current: " + str(grizzly.read_motor_current()) + "Encoder: " + str(grizzly.read_encoder()))


# Appendix: Keys
# --------------
# Key:                      Range of values:
# X1                        -32768 : 32767
# Y1                        -32768 : 32767
# X2                        -32768 : 32767
# Y2                        -32768 : 32767
# du                        0, 1
# dd                        0, 1
# dl                        0, 1
# dr                        0, 1
# back                      0, 1
# guide                     0, 1
# start                     0, 1
# TL                        0, 1
# TR                        0, 1
# A                         0, 1
# B                         0, 1
# X                         0, 1
# Y                         0, 1
# LB                        0, 1
# RB                        0, 1
# LT                        0 : 255
# RT                        0 : 255
