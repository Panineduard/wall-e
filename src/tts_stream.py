"""Stream TTS PCM audio directly to I2S without buffering the full response."""
import socket
import ssl
import struct
import utime
from machine import I2S, Pin
import config

_HOST = "api.openai.com"
_PORT = 443
_CHUNK = 1024
_PREBUFFER = 65536  # ~1.4 seconds at 24kHz 16-bit before starting playback
_addr = None  # cached DNS


def _i2s():
    return I2S(
        1,
        sck=Pin(config.SPK_BCK),
        ws=Pin(config.SPK_WS),
        sd=Pin(config.SPK_DATA),
        mode=I2S.TX,
        bits=config.SPK_BITS,
        format=I2S.MONO,
        rate=config.SPK_SAMPLE_RATE,
        ibuf=65536,  # large buffer to survive network gaps
    )


def _send_request(sock, text):
    import ujson
    body = ujson.dumps({
        "model": config.TTS_MODEL,
        "voice": config.TTS_VOICE,
        "input": text,
        "response_format": "pcm",
    }).encode("utf-8")
    auth = ("Bearer " + config.OPENAI_API_KEY).encode()
    request = (
        b"POST /v1/audio/speech HTTP/1.1\r\n"
        b"Host: api.openai.com\r\n"
        b"Authorization: " + auth + b"\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(body)).encode() + b"\r\n"
        b"Connection: close\r\n\r\n"
        + body
    )
    sock.write(request)


def _skip_headers(sock):
    """Read HTTP headers. Raises on non-200. Returns True if chunked."""
    chunked = False
    status = 200
    first = True
    while True:
        line = b""
        while not line.endswith(b"\r\n"):
            line += sock.read(1)
        if first:
            parts = line.split()
            status = int(parts[1]) if len(parts) >= 2 else 0
            first = False
        if line == b"\r\n":
            break
        if b"chunked" in line.lower():
            chunked = True
    if status != 200:
        body = sock.read(512)
        raise RuntimeError("TTS HTTP " + str(status) + ": " + str(body))
    return chunked


def _read_chunk_size(sock):
    line = b""
    while not line.endswith(b"\r\n"):
        line += sock.read(1)
    return int(line.strip(), 16)


def speak_stream(text):
    print("[TTS] streaming", len(text), "chars")

    import gc; gc.collect()
    print("[TTS] free mem:", gc.mem_free())

    sd_pin = Pin(config.SPK_SD, Pin.OUT)
    sd_pin.value(1)
    spk = _i2s()
    print("[TTS] i2s ok")

    global _addr
    if _addr is None:
        print("[TTS] dns...")
        _addr = socket.getaddrinfo(_HOST, _PORT)[0][-1]
    print("[TTS] connecting...")
    raw = socket.socket()
    raw.settimeout(30)
    raw.connect(_addr)
    print("[TTS] ssl...")
    sock = ssl.wrap_socket(raw, server_hostname=_HOST)
    print("[TTS] sending request...")

    try:
        _send_request(sock, text)
        print("[TTS] reading headers...")
        chunked = _skip_headers(sock)
        print("[TTS] streaming audio...")

        buf = bytearray(_CHUNK)
        mv  = memoryview(buf)

        # collect prebuffer before starting playback
        prebuf = bytearray()
        started = False
        played_bytes = 0

        def _play_chunk(data):
            nonlocal prebuf, started, played_bytes
            if started:
                spk.write(data)
                played_bytes += len(data)
            else:
                prebuf += data
                if len(prebuf) >= _PREBUFFER:
                    spk.write(prebuf)
                    played_bytes += len(prebuf)
                    prebuf = bytearray()
                    started = True

        if chunked:
            while True:
                size = _read_chunk_size(sock)
                if size == 0:
                    break
                remaining = size
                while remaining > 0:
                    to_read = min(remaining, _CHUNK)
                    data = sock.read(to_read)
                    if not data:
                        break
                    _play_chunk(data)
                    remaining -= len(data)
                sock.read(2)
        else:
            while True:
                data = sock.read(_CHUNK)
                if not data:
                    break
                _play_chunk(data)

        # flush remaining prebuffer (short responses may never hit _PREBUFFER)
        if prebuf:
            spk.write(prebuf)

        # wait for I2S DMA to finish playing before deinit
        total_bytes = played_bytes + len(prebuf)
        drain_ms = total_bytes * 1000 // (config.SPK_SAMPLE_RATE * 2) + 1500
        utime.sleep_ms(drain_ms)

    finally:
        sock.close()
        raw.close()
        spk.deinit()
        sd_pin.value(0)
        print("[TTS] stream done")
