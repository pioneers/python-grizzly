import usb.core
import struct
from __future__ import division

class GrizzlyUSB(object):
	def __init__(self, idVendor = 0x03eb, idProduct=0x204f):
		dev = usb.core.find(idVendor = idVendor, idProduct = idProduct)
		if (dev == None):
			raise Exception("Could not find GrizzlyBear device (idVendor=%d, idProduct=%d)" % (idVendor, idProduct))
		try:
			dev.detach_kernel_driver(0)
		except usb.USBError:
			pass
		
		self._dev = dev
		
	def send_bytes(self, cmd):
		assert len(cmd) == 16, "Must send 16 bytes"
		self._dev.ctrl_transfer(0x21, 0x09, 0x0300, 0, cmd)
		
	def exchange_bytes(self, cmd):
		assert len(cmd) == 16, "Must send 16 bytes"
		self._dev.ctrl_transfer(0x21, 0x09, 0x0300, 0, cmd)
		numBytes = cmd[1] & 0x7f
		return self._dev.ctrl_transfer(0xa1, 0x01, 0x0301, 0, numBytes + 1)[1::]
		
		
class Grizzly(object):
	COMMAND_ENABLE_USB_MODE				= "\x9A\x81\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
	COMMAND_DISABLE_TIMEOUT             = "\x80\x82\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
	
	def __init__(self, device):
		self._dev = device
		self._ticks = 0
		self._dev.send_bytes(Grizzly.COMMAND_ENABLE_USB_MODE)
		self._dev.send_bytes(Grizzly.COMMAND_DISABLE_TIMEOUT)
	
	def set_register(self, addr, data):
		assert len(data) <= 14, "Cannot write more than 14 bytes at a time"
		cmd = chr(addr) + chr(len(data) | 0x80)
		for byte in data:
			cmd += chr(byte)
		cmd += (16 - len(cmd)) * chr(0)
		self._dev.send_bytes(cmd)
		
	def read_register(self, addr, numBytes):
		assert numBytes <= 0x7f, "Cannot read more than 127 bytes at a time"
		cmd = chr(addr) + chr(numBytes)
		cmd += (16 - len(cmd)) * chr(0)
		self._dev.exchange_bytes(cmd)
		
	def setMode(self, controlmode, drivemode):
		self.set_register(Addr.Mode, 1, [0x01 | controlmode | drivemode])
	
	def setSpeed(self, setpoint):
		buf = [0, 0, setpoint, 0, 0]
		self.set_register(Addr.Speed, buf)
		
	def _read_as_int(self, addr, numBytes):
	    buf = self.read_register(addr, numBytes)
	    rtn = 0
	    for i, byte in enumerate(buf):
	        rtn |= byte << 8 * i
	    return rtn
    
    def _set_as_int(self, addr, val, numBytes = 1):
        buf = []
        for i in range(numBytes):
            buf.append((val >> 8 * i) & 0xff)
        self.set_register(addr, buf)
	
	def MotorCurrent():
        return _read_as_int(Addr.MotorCurrent, 2)
    
    def GetTimeout():
        return _read_as_int(Addr.Timeout, 2)
    
    def ReadEncoder():
        return _read_as_int(Addr.EncoderCount, 4)
        
    def hasReset():
        currentTime = _read_as_int(Addr.Uptime, 4)
        if currentTime <= self._ticks:
            return True
        return False
    
    def LimitAcceleration(accel):
        if accel > 0x8f:
            raise Exception("Acceleration limit cannot exceed 143")
        self._set_as_int(Addr.AccelLimit, accel)
        
    def LimitCurrent(curr):
        self._set_as_int(Addr.CurrentLimit, curr)
        
    def InitPID(kp, ki, kd):
        p, i, d = map(lambda x: x * (2 ** 16), (kp, ki, kd))
        self._set_as_int(Addr.PConstant, p)
        self._set_as_int(Addr.IConstant, i)
        self._set_as_int(Addr.DConstant, d)
        
    def GetPIDConstants():
        p = self._read_as_int(Addr.PConstant, 4)
        i = self._read_as_int(Addr.IConstant, 4)
        d = self._read_as_int(Addr.DConstant, 4)
        
        return map(lambda x: x / (2 ** 16), (p, i, d))

class ControlMode(object):
	NO_PID 							= 0x02
	SPEED_PID 						= 0x04
	POSITION_PID 					= 0x06

class DriveMode(object):
	DRIVE_COAST 					= 0x00
	DRIVE_BRAKE 					= 0x10
	BRAKE_COAST 					= 0x20
	
class Addr(object):
	Mode 							= 0x01
	Speed	 						= 0x04
	MotorCurrent 					= 0x10
	EncoderCount 					= 0x20
	PConstant						= 0x30
	IConstant						= 0x34
	DConstant						= 0x38
	Timeout							= 0x80
	CurrentLimit                    = 0x82
	AccelLimit						= 0x90
	Uptime							= 0x94
