#!/usr/bin/env python3
'''
    File name: Milight.py
    Author: Maxime Bergeron
    Date last modified: 6/02/2019
    Python Version: 3.7

    The Milight BLE bulbs handler class
'''
import functools
import bluepy.btle as ble
from devices.common import *
from devices.Bulb import Bulb

def connect_ble(_f):
    """ Wrapper for functions which requires an active BLE connection using bluepy """
    @functools.wraps(_f)
    def _conn_wrap(self, *args):
        if self._connection is None:
            try:
                debug.write("CONnecting to device ({})...".format(self.description), 0, self.device_type)
                self._connection = ble.Peripheral(self.device)
            except Exception as ex:
                debug.write("Device ({}) connection failed. Exception: {}" \
                                      .format(self.description, ex), 1, self.device_type)
                self._connection = None
        return _f(self, *args)
    return _conn_wrap


class Milight(Bulb):
    """ Methods for driving a milight BLE lightbulb """
    def __init__(self, devid, config):
        super().__init__(devid, config)
        self.device_type = "Milight"
        self.id1 = config["DEVICE"+str(devid)]["ID1"]
        self.id2 = config["DEVICE"+str(devid)]["ID2"]
        self.state = "0"
        self.color_type = "255"
        self.color_temp = int(config["DEVICE"+str(devid)]["DEFAULT_TEMP"])
        if self.color_temp < 2000 or self.color_temp > 6500:
            debug.write("Default color temperature should be between 2000K and 6500K. Quitting.", 2, self.device_type)
            quit()
        #TODO is this accurate enough?
        self.color_temp = int((self.color_temp-2000)*125/6500)
        self.color_brightness = int(config["DEVICE"+str(devid)]["DEFAULT_BRIGHTNESS"])
        if self.color_brightness < 0 or self.color_brightness > 100:
            debug.write("Default bulb brightness should be between 0 and 100. Quitting.", 2, self.device_type)
            quit()

    def turn_on(self):
        """ Helper function to turn on device """
        if not self._write(self.get_query(32, 161, 1, self.id1, self.id2), "1"): return False
        return self._write(self.get_query(20, 161, 4, self.id1, self.id2, 1, 4, 255), "1")

    def turn_off(self):
        """ Helper function to turn off device """
        debug.write("Setting ({}) OFF".format(self.description), 0, self.device_type)
        return self._write(self.get_query(32, 161, 2, self.id1, self.id2), "0")

    def turn_on_and_set_color(self, color):
        """ Helper function to change color """
        debug.write("Setting ({}) to COLOR {}".format(self.description, color), 0, self.device_type)
        if self.state == "0":
            if not self.turn_on(): return False
        if type(color) is tuple:
            if not self._write(self.get_query(45, 161, 4, self.id1, self.id2, int(color[0]), 2, 100), color[0]): return False
            return self._write(self.get_query(45, 161, 5, self.id1, self.id2, int(color[0]), 2, int(color[1])), color)
        else:
            if not self._write(self.get_query(45, 161, 4, self.id1, self.id2, color, 2, 100), color): return False
            return self._write(self.get_query(45, 161, 5, self.id1, self.id2, color, 2, self.color_brightness), color)

    def turn_on_and_dim_on(self, color):
        """ Helper function to turn on device to default intensity """
        debug.write("Setting ({}) ON".format(self.description), 0, self.device_type)
        if not self.turn_on(): return False
        return self.dim_on(color)

    def dim_on(self, color):
        """ Helper function to set default intensity """
        return self._write(self.get_query(20, 161, 5, self.id1, self.id2, self.color_temp, 4, self.color_brightness), color)

    def color(self, color, priority):
        """ Checks the request and trigger a light change if needed """
        if color == LIGHT_OFF:
            if not self.turn_off(): 
                return False
        elif color == LIGHT_ON:
            if not self.turn_on_and_dim_on(color):
                return False         
        else:
            if not self.turn_on_and_set_color(color): 
                return False
        debug.write("({}) color changed to {}".format(self.description, color), 0, self.device_type)
        return True

    def get_query(self, value1, value2, value3, id1, id2, value4=0, value5=2, value6=0):
        """
        Generate encrypted request string.
        ON (value3 = 1)/OFF (value3 = 2): value1 = 32, value2 = 161
        CHANGE COLOR: value1 = 45, value2 = 161, value3 = 4, value4 = colorid
        """
        packet = self._create_command("[" + str(value1) + ", " + str(value2) + ", " + str(id1)
                                      + ", " + str(id2) + ", " + str(value5) + ", " + str(value3)
                                      + ", " + str(value4) + ", " + str(value6) + ", 0, 0, 0]")
        return packet

    @connect_ble
    def _write(self, command, color):
        _oldcolor = self.state
        try:
            if self._connection is not None:
                self.state = color
                self._connection.getCharacteristics(uuid="00001001-0000-1000-8000-00805f9b34fb")[0] \
                                                    .write(bytearray.fromhex(command \
                                                                             .replace('\n', '') \
                                                                             .replace('\r', '')))
                self.success = True
                return True
            self.state = _oldcolor
            debug.write("Connection error to device ({}). Retrying" \
                                  .format(self.description), 1, self.device_type)
            return False
        except:
            self.state = _oldcolor
            debug.write("Error sending data to device ({}). Retrying" \
                                   .format(self.description), 1, self.device_type)
            self._connection = None
            return False

    def _create_command(self, bledata):
        _input = eval(bledata)
        k = _input[0]
        j = 0
        i = 0
        while i <= 10:
            j += _input[i] & 0xff
            i += 1
        checksum = ((((k ^ j) & 0xff) + 131) & 0xff)
        xored = [(s&0xff)^k for s in _input]
        offs = [0, 16, 24, 1, 129, 55, 169, 87, 35, 70, 23, 0]
        adds = [x+y&0xff for(x, y) in zip(xored, offs)]
        adds[0] = k
        adds.append(checksum)
        hexs = [hex(x) for x in adds]
        hexs = [x[2:] for x in hexs]
        hexs = [x.zfill(2) for x in hexs]

        return ''.join(hexs)