import network
import utime
import config

_wlan = network.WLAN(network.STA_IF)

def connect():
    _wlan.active(True)
    if _wlan.isconnected():
        return
    _wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    for _ in range(20):
        if _wlan.isconnected():
            return
        utime.sleep(1)
    raise OSError("WiFi connection failed")

def ensure():
    if not _wlan.isconnected():
        connect()

def ip():
    return _wlan.ifconfig()[0]
