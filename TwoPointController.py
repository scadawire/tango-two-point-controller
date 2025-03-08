import time
from tango import AttrQuality, AttrWriteType, DispLevel, DevState, Attr, CmdArgType, UserDefaultAttrProp, DeviceProxy
from tango.server import Device, attribute, command, DeviceMeta
from tango.server import class_property, device_property
from tango.server import run
import os
import json
from json import JSONDecodeError
from threading import Thread

class TwoPointController(Device, metaclass=DeviceMeta):
    pass

    sensorValueCurrent = attribute(label="sensorValueCurrent", dtype=float,
        display_level=DispLevel.EXPERT,
        access=AttrWriteType.READ, polling_period=1000,
        unit="_", format="8.4f")

    actorValueCurrent = attribute(label="actorValueCurrent", dtype=float,
        display_level=DispLevel.EXPERT,
        access=AttrWriteType.READ, polling_period=1000,
        unit="_", format="8.4f")

    sensorValueTargetCurrent = attribute(label="sensorValueTargetCurrent", dtype=float,
        display_level=DispLevel.EXPERT,
        access=AttrWriteType.READ, polling_period=1000,
        unit="_", format="8.4f")

    difference = attribute(label="difference", dtype=float,
        display_level=DispLevel.EXPERT,
        access=AttrWriteType.READ, polling_period=1000,
        unit="_", format="8.4f")
    
    __sensorValueTarget = 0

    ActorDevice = device_property(dtype=str, default_value="")
    ActorAttribute = device_property(dtype=str, default_value="")
    SensorDevice = device_property(dtype=str, default_value="")
    SensorAttribute = device_property(dtype=str, default_value="")
    Hysteresis = device_property(dtype=float, default_value=0)
    ActorMinControlInterval = device_property(dtype=float, default_value=0)
    ActorOffValue = device_property(dtype=float, default_value=-10)
    ActorOnValue = device_property(dtype=float, default_value=10)
    regulateInterval = device_property(dtype=float, default_value=1)
    sensorValueTarget = device_property(dtype=float, default_value=0)
    deviceActor = 0
    deviceSensor = 0
    __lastChanged = time.time()
    
    def read_sensorValueCurrent(self):
        sensorValue = self.getSensorValueFloat()
        return sensorValue, time.time(), AttrQuality.ATTR_VALID
    
    def read_actorValueCurrent(self):
        actorValue = self.getActorValueFloat()
        return actorValue, time.time(), AttrQuality.ATTR_VALID

    def read_difference(self):
        difference = self.getDifference()
        return difference, time.time(), AttrQuality.ATTR_VALID

    def read_sensorValueTargetCurrent(self):
        return self.__sensorValueTarget, time.time(), AttrQuality.ATTR_VALID

    @command()
    def regulateLoop(self):
        while(1):
            try:
                self.regulate()
            except Exception as e:
                print("regulate error: " + str(e))
            time.sleep(self.regulateInterval)

    def getSensorValueFloat(self):
        sensorAttribute = self.deviceSensor.read_attribute(self.SensorAttribute)
        sensorValue = sensorAttribute.value
        if(sensorAttribute.type == CmdArgType.DevString):
            sensorValue = float(sensorValue)
        return sensorValue

    def getActorValueFloat(self):
        actorValue = 0 # if controlled actor value is not derivable  default to 0
        try:
            actorAttribute = self.deviceActor.read_attribute(self.ActorAttribute)
            actorValue = actorAttribute.value
            if(actorAttribute.type == CmdArgType.DevString):
                actorValue = float(actorValue)
        except Exception:
            pass
        return actorValue

    def getDifference(self):
        sensorValue = self.getSensorValueFloat()
        difference = float(self.__sensorValueTarget) - float(sensorValue) # reference - measurent
        return difference
        
    def regulate(self):
        actorValue = self.getActorValueFloat()
        sensorValue = self.getSensorValueFloat()
        if((time.time() - self.__lastChanged ) < self.ActorMinControlInterval):
            print("no regulation: min control interval not reached")
            return # not allowed to change again
        difference = self.getDifference()
        if(abs(difference) < self.Hysteresis):
            print("no regulation: hysteresis suppression")
            return # difference is in bounds of hysterese
        
        print("current actorValue: " + str(actorValue))
        print("current sensorValue: " + str(sensorValue))
        print("current target value: " + str(self.__sensorValueTarget))
        print("difference: " + str(difference))
        
        # Calculate control signal by using simple compare of current value
        newActorValue = self.ActorOffValue
        if(difference > 0):
            newActorValue = self.ActorOnValue

        if(actorValue != newActorValue):
            self.__lastChanged = time.time()
            print("changing actor to " + str(newActorValue))
            actorAttribute = self.deviceActor.read_attribute(self.ActorAttribute)
            if(actorAttribute.type == CmdArgType.DevString):
                newActorValue = str(newActorValue)
            self.deviceActor.write_attribute(self.ActorAttribute, newActorValue)

    def init_device(self):
        self.set_state(DevState.INIT)
        self.get_device_properties(self.get_device_class())
        self.deviceActor = DeviceProxy(self.ActorDevice)
        self.deviceSensor = DeviceProxy(self.SensorDevice)
        self.__sensorValueTarget = self.sensorValueTarget
        Thread(target=self.regulateLoop).start()
        self.set_state(DevState.ON)

if __name__ == "__main__":
    deviceServerName = os.getenv("DEVICE_SERVER_NAME")
    run({deviceServerName: TwoPointController})
