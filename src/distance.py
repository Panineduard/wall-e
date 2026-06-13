from machine import Pin, time_pulse_us
import utime
import config

_trig = Pin(config.DIST_TRIG, Pin.OUT)
_echo = Pin(config.DIST_ECHO, Pin.IN)

def read_cm():
    _trig.value(0)
    utime.sleep_us(2)
    _trig.value(1)
    utime.sleep_us(10)
    _trig.value(0)

    duration = time_pulse_us(_echo, 1, 30000)  # 30 ms timeout ≈ 5 m max
    if duration < 0:
        return None  # timeout — nothing detected
    return duration * 0.0171  # µs → cm  (speed of sound / 2)

def is_obstacle():
    dist = read_cm()
    return dist is not None and dist < config.DIST_OBSTACLE_CM
