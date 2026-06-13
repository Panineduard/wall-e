from machine import Pin, PWM
import utime
import _thread
import config

class Motors:
    def __init__(self):
        self._r_in1 = Pin(config.MOTOR_R_IN1, Pin.OUT)
        self._r_in2 = Pin(config.MOTOR_R_IN2, Pin.OUT)
        self._r_en  = PWM(Pin(config.MOTOR_R_EN), freq=1000)

        self._l_in3 = Pin(config.MOTOR_L_IN3, Pin.OUT)
        self._l_in4 = Pin(config.MOTOR_L_IN4, Pin.OUT)
        self._l_en  = PWM(Pin(config.MOTOR_L_EN), freq=1000)

        self.stop()

    def _right(self, duty, fwd):
        self._r_in1.value(1 if fwd else 0)
        self._r_in2.value(0 if fwd else 1)
        self._r_en.duty(duty)

    def _left(self, duty, fwd):
        self._l_in3.value(1 if fwd else 0)
        self._l_in4.value(0 if fwd else 1)
        self._l_en.duty(duty)

    def forward(self, speed=None):
        s = speed or config.MOTOR_SPEED_FULL
        self._right(s, True)
        self._left(s, True)

    def backward(self, speed=None):
        s = speed or config.MOTOR_SPEED_FULL
        self._right(s, False)
        self._left(s, False)

    def turn_left(self, speed=None):
        s = speed or config.MOTOR_SPEED_TURN
        self._right(s, True)
        self._left(s, False)

    def turn_right(self, speed=None):
        s = speed or config.MOTOR_SPEED_TURN
        self._right(s, False)
        self._left(s, True)

    def stop(self):
        self._r_in1.value(0)
        self._r_in2.value(0)
        self._l_in3.value(0)
        self._l_in4.value(0)
        self._r_en.duty(0)
        self._l_en.duty(0)

    def _dance_loop(self, stop_flag):
        s = config.MOTOR_SPEED_TURN
        sf = config.MOTOR_SPEED_FULL
        steps = [
            (s,  True,  False, 350),   # spin left
            (s,  False, True,  350),   # spin right
            (sf, True,  True,  250),   # forward
            (sf, False, False, 250),   # backward
            (s,  True,  False, 350),   # spin left
            (s,  False, True,  350),   # spin right
        ]
        i = 0
        while not stop_flag[0]:
            spd, rf, lf, ms = steps[i % len(steps)]
            self._right(spd, rf)
            self._left(spd, lf)
            utime.sleep_ms(ms)
            i += 1
        self.stop()

    def start_dancing(self):
        self._stop_dance = [False]
        _thread.start_new_thread(self._dance_loop, (self._stop_dance,))

    def stop_dancing(self):
        if hasattr(self, '_stop_dance'):
            self._stop_dance[0] = True
            utime.sleep_ms(500)
