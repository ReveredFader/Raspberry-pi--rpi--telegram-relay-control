import RPi.GPIO as GPIO

class RPI:
    def __init__(self, pins):
        GPIO.setmode(GPIO.BCM)
        for i in pins:
            GPIO.setup(i, GPIO.OUT)
            GPIO.output(pin, True)
        self.pins = pins
    
    def re_init_pins(self, pins):
        GPIO.setmode(GPIO.BCM)
        for i in pins:
            GPIO.setup(i, GPIO.OUT)
        self.pins = pins

    def pin_status(self, pin):
        if pin in self.pins:
            return GPIO.input(pin)

    def pin_off(self, pin):
        if pin in self.pins:
            if self.pin_status(pin) == 1:
                GPIO.output(pin, False)
                return True
            else:
                print("Pin is already off")
                return True
        else:
            print("Incorrect pin")
            return False

    def pin_on(self, pin):
        if pin in self.pins:
            if self.pin_status(pin) == 0:
                GPIO.output(pin, True)
                return True
            else:
                print("Pin is already on")
                return True
        else:
            return False
