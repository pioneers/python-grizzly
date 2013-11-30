from __future__ import division
import usb.core
import struct

class GrizzlyUSB(object):
    """Handles low level Grizzly communication over the USB protocol"""
    COMMAND_GET_ADDR            = "\x9b\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    def __init__(self, addr, idVendor = 0x03eb, idProduct=0x204f):
        all_dev = usb.core.find(find_all = True, idVendor = idVendor, idProduct = idProduct)
        for dev in all_dev:
            try:
                dev.detach_kernel_driver(0)
            except usb.USBError:
                pass
            
        if len(all_dev) <= 0:
            raise usb.USBError("Could not find GrizzlyBear device (idVendor=%d, idProduct=%d)" % (idVendor, idProduct))
        if len(all_dev) == 1:
            self._dev = all_dev[0]
        else:
            for device in all_dev:
                device.ctrl_transfer(0x21, 0x09, 0x0300, 0, GrizzlyUSB.COMMAND_GET_ADDR)
                internal_addr = device.ctrl_transfer(0xa1, 0x01, 0x0301, 0, 2)[1]
                if internal_addr == (addr << 1):
                    self._dev = device
        
    def send_bytes(self, cmd):
        """Sends a 16 byte packet to the grizzly. Does not expect to read anything back.
        Packet format looks like:
        Byte 0:           Register address
        Byte 1 (bit 6:0): Length of data to read/write in bytes
        Byte 1 (bit 7):   R/W flag (1 = write)
        Byte 2-15:        Data
        
        The register address automatically increments allowing you to write up to
        14 sequential registers at a time"""
        assert len(cmd) == 16, "Must send 16 bytes"
        self._dev.ctrl_transfer(0x21, 0x09, 0x0300, 0, cmd)
        
    def exchange_bytes(self, cmd):
        """Sends a packet to the grizzly, requesting information. Reads back
        the data requested. Packet format looks like:
        Byte 0:           Register
        Byte 1 (bit 6:0): Length of data to read/write
        Byte 1 (bit 7):   R/W flag (1 = write)
        Byte 2-15:        Data
        
        The length of the read indicates how many registers you want to read from
        sequentially"""
        assert len(cmd) == 16, "Must send 16 bytes"
        self._dev.ctrl_transfer(0x21, 0x09, 0x0300, 0, cmd)
        numBytes = ord(cmd[1]) & 0x7f
        return self._dev.ctrl_transfer(0xa1, 0x01, 0x0301, 0, numBytes + 1)[1::]
        
        
class Grizzly(object):
    """The high level command API. This allows setting arbitrary registers and several
    convenience methods that could be used commonly. Almost a direct port from the
    implementation in C#. However the control loop is expected to be much greater so
    there is no need for some of the optimizations in PiER."""
    
    def __init__(self, addr=0x0f):
        """Creates the object to represent the Grizzly. Provides access to
        control the grizzly. The @device argument refers to the low level
        GrizzlyUSB object that is connected as a USB device."""
        self._dev = GrizzlyUSB(addr)
        self._ticks = 0
        self._set_as_int(Addr.EnableUSB, 1)
        self._set_as_int(Addr.Timeout, 0, 2)
        
    def set_register(self, addr, data):
        """Sets an arbitrary register at @addr and subsequent registers depending
        on how much data you decide to write. It will automatically fill extra
        bytes with zeros. You cannot write more than 14 bytes at a time.
        @addr should be a static constant from the Addr class, e.g. Addr.Speed"""
        assert len(data) <= 14, "Cannot write more than 14 bytes at a time"
        cmd = chr(addr) + chr(len(data) | 0x80)
        for byte in data:
            cmd += chr(cast_to_byte(byte))
        cmd += (16 - len(cmd)) * chr(0)
        self._dev.send_bytes(cmd)
        
    def read_register(self, addr, numBytes):
        """Reads @numBytes bytes from the grizzly starting at @addr. Due
        to packet format, cannot read more than 127 packets at a time.
        Returns a byte array of the requested data in little endian.
        @addr should be from the Addr class e.g. Addr.Speed"""
        assert numBytes <= 0x7f, "Cannot read more than 127 bytes at a time"
        cmd = chr(addr) + chr(numBytes)
        cmd += (16 - len(cmd)) * chr(0)
        return self._dev.exchange_bytes(cmd)
        
    def set_mode(self, controlmode, drivemode):
        """Higher level abstraction for setting the mode register. This will
        set the mode according the the @controlmode and @drivemode you specify.
        @controlmode and @drivemode should come from the ControlMode and DriveMode
        class respectively."""
        self.set_register(Addr.Mode, [0x01 | controlmode | drivemode])
    
    def set_target(self, setpoint):
        """Higher level abstraction for setting the speed register. This
        register is responsible for telling the grizzly at what speed or
        position to drive at. Since the @setpoint is always an int, we
        can just set the last two bytes."""
        buf = [0, 0, cast_to_byte(setpoint), cast_to_byte(setpoint >> 8), 0]
        self.set_register(Addr.Speed, buf)
        
    def _read_as_int(self, addr, numBytes):
        """Convenience method. Oftentimes we need to read a range of
        registers to represent an int. This method will automatically read
        @numBytes registers starting at @addr and convert the array into an int."""
        buf = self.read_register(addr, numBytes)
        if len(buf) >= 4:
            return struct.unpack_from("<i", buf)[0]
        else:
            rtn = 0
            for i, byte in enumerate(buf):
                rtn |= byte << 8 * i
            return rtn
    
    def _set_as_int(self, addr, val, numBytes = 1):
        """Convenience method. Oftentimes we need to set a range of registers
        to represent an int. This method will automatically set @numBytes registers
        starting at @addr. It will convert the int @val into an array of bytes."""
        if type(val) == type(int):
            raise ValueError("val must be an int. You provided: %s" % str(val))
        buf = []
        for i in range(numBytes):
            buf.append(cast_to_byte(val >> 8 * i))
        self.set_register(addr, buf)
    
    def read_motor_current(self):
        """High level abstraction. Reads back the current going through the motor
        as reported by the Grizzly. Returns a float that represents the number
        of amps going through the motor."""
        rawval = self._read_as_int(Addr.MotorCurrent, 2)
        return (5.0/1024.0) * (1000.0 / 66.0) * (rawval - 511)
    
    def read_encoder(self):
        """High level abstraction. Reads back the current encoder count in ticks.
        There are 64 ticks per motor spindle revolution."""
        return self._read_as_int(Addr.EncoderCount, 4)
        
    def write_encoder(self, count):
        """High level abstraction. Allows you to overwrite the current
        encoder count. Allows for reseting the position."""
        self._set_as_int(Addr.EncoderCount, count, 4)
        
    def has_reset(self):
        """Checks the grizzly to see if it reset itself because of
        voltage sag or other reasons."""
        currentTime = self._read_as_int(Addr.Uptime, 4)
        if currentTime <= self._ticks:
            self._ticks = currentTime
            return True
        self._ticks = currentTime
        return False
    
    def limit_acceleration(self, accel):
        """Sets the acceleration limit on the Grizzly. The max value is
        143. Units are change in pwm per millisecond."""
        if accel >= 143:
            raise ValueError("Acceleration limit cannot exceed 143. You provided: %s" % str(accel))
        if accel <= 0:
            raise ValueError("Acceleration limit must be positive. You provided: %s" % str(accel))
        self._set_as_int(Addr.AccelLimit, accel)
        
    def limit_current(self, curr):
        """Sets the current limit on the Grizzly. The units are in amps."""
        if curr <= 0:
            raise ValueError("Current limit must be a positive number. You provided: %s" % str(curr))
        current = int(curr * (1024.0 / 5.0) * (66.0 / 1000.0))
        self._set_as_int(Addr.CurrentLimit, current, 2)
        
    def init_pid(self, kp, ki, kd):
        """Sets the PID constants for the PID modes. Arguments are all
        floating point numbers."""
        p, i, d = map(lambda x: int(x * (2 ** 16)), (kp, ki, kd))
        self._set_as_int(Addr.PConstant, p, 4)
        self._set_as_int(Addr.IConstant, i, 4)
        self._set_as_int(Addr.DConstant, d, 4)
        
    def read_pid_constants(self):
        """Reads back the PID constants stored on the Grizzly."""
        p = self._read_as_int(Addr.PConstant, 4)
        i = self._read_as_int(Addr.IConstant, 4)
        d = self._read_as_int(Addr.DConstant, 4)
        
        return map(lambda x: x / (2 ** 16), (p, i, d))
        
def cast_to_byte(val):
    return int(val) & 0xff

class ControlMode(object):
    """Enum for the control modes. Use these as input to set_mode."""
    NO_PID                          = 0x02
    SPEED_PID                       = 0x04
    POSITION_PID                    = 0x06

class DriveMode(object):
    """Enum for the drive modes. Use these as inputs to set_mode."""
    DRIVE_COAST                     = 0x00
    DRIVE_BRAKE                     = 0x10
    BRAKE_COAST                     = 0x20
    
class Addr(object):
    """Enum for the i2c registers on the Grizzly. Use these as inputs
    to all addr arguments."""
    Mode                            = 0x01
    Speed                           = 0x04
    MotorCurrent                    = 0x10
    EncoderCount                    = 0x20
    PConstant                       = 0x30
    IConstant                       = 0x34
    DConstant                       = 0x38
    Timeout                         = 0x80
    CurrentLimit                    = 0x82
    AccelLimit                      = 0x90
    Uptime                          = 0x94
    EnableUSB                       = 0x9A
    AddressList                     = 0x9B
