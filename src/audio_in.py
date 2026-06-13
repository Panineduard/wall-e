import struct
import math
from machine import I2S, Pin
import config


def _wav_header(num_samples):
    ch   = 1
    bits = config.MIC_BITS
    rate = config.MIC_SAMPLE_RATE
    data_size = num_samples * ch * (bits // 8)
    return struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16,
        1, ch, rate,
        rate * ch * (bits // 8),
        ch * (bits // 8),
        bits,
        b'data', data_size,
    )


def _rms(buf):
    n = len(buf) // 2
    if n == 0:
        return 0
    total = 0
    for i in range(0, len(buf) - 1, 2):
        sample = struct.unpack_from('<h', buf, i)[0]
        total += sample * sample
    return int(math.sqrt(total // n))


def make_mic():
    return I2S(
        0,
        sck=Pin(config.MIC_BCK),
        ws=Pin(config.MIC_WS),
        sd=Pin(config.MIC_DATA),
        mode=I2S.RX,
        bits=config.MIC_BITS,
        format=I2S.MONO,
        rate=config.MIC_SAMPLE_RATE,
        ibuf=8192,
    )


def record(mic, duration_ms=None):
    ms = duration_ms or config.MIC_RECORD_MS
    num_samples = config.MIC_SAMPLE_RATE * ms // 1000
    buf = bytearray(num_samples * (config.MIC_BITS // 8))
    print("[MIC] recording", ms, "ms...")
    mic.readinto(buf)
    nonzero = sum(1 for i in range(0, len(buf), 100) if buf[i] != 0)
    print("[MIC] done —", nonzero, "/", len(buf)//100, "non-zero")
    return bytes(_wav_header(num_samples)) + bytes(buf)


def flush(mic, ms=1500):
    """Discard ms milliseconds of buffered audio (call after playback)."""
    chunk_samples = config.MIC_SAMPLE_RATE * config.VAD_CHUNK_MS // 1000
    chunk_bytes   = chunk_samples * (config.MIC_BITS // 8)
    chunk_buf     = bytearray(chunk_bytes)
    chunks = ms // config.VAD_CHUNK_MS
    for _ in range(chunks):
        mic.readinto(chunk_buf)
    print("[MIC] flushed", ms, "ms")


def record_vad(mic):
    """Record until the user stops speaking. Returns WAV bytes or None if no speech detected."""
    chunk_samples  = config.MIC_SAMPLE_RATE * config.VAD_CHUNK_MS // 1000
    chunk_bytes    = chunk_samples * (config.MIC_BITS // 8)
    chunk_buf      = bytearray(chunk_bytes)
    max_samples    = config.MIC_SAMPLE_RATE * config.VAD_MAX_MS // 1000
    silence_chunks = config.VAD_SILENCE_MS // config.VAD_CHUNK_MS

    print("[VAD] listening...")
    audio_data    = bytearray()
    speaking      = False
    silence_count = 0
    total_samples = 0

    while total_samples < max_samples:
        mic.readinto(chunk_buf)
        level = _rms(chunk_buf)
        total_samples += chunk_samples

        if not speaking:
            print("[VAD] rms:", level)
            if level >= config.VAD_SPEAK_THRESHOLD:
                speaking = True
                silence_count = 0
                audio_data += chunk_buf
                print("[VAD] speech detected")
        else:
            audio_data += chunk_buf
            if level < config.VAD_SILENCE_THRESHOLD:
                silence_count += 1
                if silence_count >= silence_chunks:
                    print("[VAD] silence, stopping")
                    break
            else:
                silence_count = 0

    if not speaking:
        print("[VAD] no speech")
        return None

    num_samples = len(audio_data) // (config.MIC_BITS // 8)
    print("[VAD] captured", len(audio_data), "bytes")
    return bytes(_wav_header(num_samples)) + bytes(audio_data)
