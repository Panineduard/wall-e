from machine import Pin, PWM
import utime
import _thread
import config

# At 50 Hz the period is 20 ms.
# duty_u16 maps 0-65535 to 0-20 ms.
# Typical servo pulse: 0.5 ms (0°) … 2.5 ms (180°)
_MIN_US = 500
_MAX_US = 2500
_PERIOD_US = 20000

def _angle_to_duty(angle):
    us = _MIN_US + (_MAX_US - _MIN_US) * angle // 180
    return us * 65535 // _PERIOD_US


class Servo:
    def __init__(self, pin):
        self._pwm = PWM(Pin(pin), freq=50)

    def write(self, angle):
        angle = max(0, min(180, angle))
        self._pwm.duty_u16(_angle_to_duty(angle))

    def deinit(self):
        self._pwm.deinit()


class Servos:
    def __init__(self):
        self.right = Servo(config.SERVO_RIGHT_PIN)
        self.left  = Servo(config.SERVO_LEFT_PIN)
        self.neck  = Servo(config.SERVO_NECK_PIN)
        self.reset()

    def reset(self):
        self.right.write(config.SERVO_RIGHT_REST)
        self.left.write(config.SERVO_LEFT_REST)
        self.neck.write(config.SERVO_NECK_CENTER)

    def wave(self, times=3):
        for _ in range(times):
            self.right.write(165)
            self.left.write(165)
            utime.sleep_ms(250)
            self.right.write(config.SERVO_RIGHT_REST)
            self.left.write(config.SERVO_LEFT_REST)
            utime.sleep_ms(250)

    def start_talking(self):
        self.neck.write(config.SERVO_NECK_CENTER - 15)

    def stop_talking(self):
        self.neck.write(config.SERVO_NECK_CENTER)

    def start_driving(self):
        self.neck.write(config.SERVO_NECK_CENTER + 10)
        self.right.write(130)
        self.left.write(130)

    def stop_driving(self):
        self.reset()

    def _dance_loop(self, stop_flag):
        c = config.SERVO_NECK_CENTER
        moves = [
            (c - 35, 170, 50),
            (c + 35, 50,  170),
            (c - 35, 170, 50),
            (c + 35, 50,  170),
            (c,      170, 170),
            (c,      50,  50),
        ]
        i = 0
        while not stop_flag[0]:
            neck, r, l = moves[i % len(moves)]
            self.neck.write(neck)
            self.right.write(r)
            self.left.write(l)
            i += 1
            utime.sleep_ms(350)
        self.reset()

    def start_dancing(self):
        self._stop_dance = [False]
        _thread.start_new_thread(self._dance_loop, (self._stop_dance,))

    def stop_dancing(self):
        if hasattr(self, '_stop_dance'):
            self._stop_dance[0] = True
            utime.sleep_ms(500)
