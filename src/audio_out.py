import struct
from machine import I2S, Pin
import config

def _pcm_from_wav(wav_bytes):
    # Locate the 'data' chunk — skip any metadata chunks before it
    offset = 12
    while offset < len(wav_bytes) - 8:
        chunk_id = wav_bytes[offset:offset + 4]
        chunk_size = struct.unpack_from('<I', wav_bytes, offset + 4)[0]
        if chunk_id == b'data':
            return wav_bytes[offset + 8: offset + 8 + chunk_size]
        offset += 8 + chunk_size
    raise ValueError("No data chunk found in WAV")

def play(wav_bytes):
    pcm = wav_bytes  # already raw PCM from OpenAI
    print(f"[SPK] playing {len(pcm)} bytes of PCM audio…")

    sd_pin = Pin(config.SPK_SD, Pin.OUT)
    sd_pin.value(1)  # enable amplifier

    spk = I2S(
        1,
        sck=Pin(config.SPK_BCK),
        ws=Pin(config.SPK_WS),
        sd=Pin(config.SPK_DATA),
        mode=I2S.TX,
        bits=config.SPK_BITS,
        format=I2S.MONO,
        rate=config.SPK_SAMPLE_RATE,
        ibuf=8192,
    )

    # Write in chunks so we don't stall if pcm is large
    chunk = 1024
    mv = memoryview(pcm)
    for i in range(0, len(pcm), chunk):
        spk.write(mv[i: i + chunk])

    spk.deinit()
    sd_pin.value(0)  # mute amplifier when done
    print("[SPK] done")


def play_file(path):
    print("[SPK] loading", path)
    with open(path, "rb") as f:
        data = f.read()
    play(data)


def play_file(path):
    print(f"[SPK] loading {path}…")
    with open(path, "rb") as f:
        wav_bytes = f.read()
    play(wav_bytes)
