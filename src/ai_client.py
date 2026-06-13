import ujson
import urequests
import config

_WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"
_CHAT_URL    = "https://api.openai.com/v1/chat/completions"
_TTS_URL     = "https://api.openai.com/v1/audio/speech"

_BOUNDARY = b"WallEBoundary42"


def _multipart(fields, file_name, file_bytes, file_type=b"audio/wav"):
    parts = bytearray()
    for name, value in fields.items():
        parts += (
            b"--" + _BOUNDARY + b"\r\n"
            b'Content-Disposition: form-data; name="' + name.encode() + b'"\r\n\r\n'
            + value.encode() + b"\r\n"
        )
    parts += (
        b"--" + _BOUNDARY + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename="' + file_name + b'"\r\n'
        b"Content-Type: " + file_type + b"\r\n\r\n"
        + file_bytes
        + b"\r\n--" + _BOUNDARY + b"--\r\n"
    )
    return bytes(parts)


def transcribe(wav_bytes):
    body = _multipart({"model": "whisper-1", "language": "uk"}, b"audio.wav", wav_bytes)
    resp = urequests.post(
        _WHISPER_URL,
        headers={
            "Authorization": "Bearer " + config.OPENAI_API_KEY,
            "Content-Type": "multipart/form-data; boundary=" + _BOUNDARY.decode(),
        },
        data=body,
    )
    text = ujson.loads(resp.content)["text"].strip()
    resp.close()
    return text


def chat(user_text, history=None):
    messages = [{"role": "system", "content": config.LLM_SYSTEM}]
    messages += list(history or [])
    messages.append({"role": "user", "content": user_text})

    payload = ujson.dumps({
        "model": config.LLM_MODEL,
        "max_tokens": 256,
        "messages": messages,
    }).encode("utf-8")
    resp = urequests.post(
        _CHAT_URL,
        headers={
            "Authorization": "Bearer " + config.OPENAI_API_KEY,
            "Content-Type": "application/json",
            "Content-Length": str(len(payload)),
        },
        data=payload,
    )
    result = ujson.loads(resp.content)
    resp.close()

    if "error" in result:
        raise RuntimeError(result["error"].get("message", str(result["error"])))
    reply = result["choices"][0]["message"]["content"].strip()
    history_out = list(history or [])
    history_out.append({"role": "user", "content": user_text})
    history_out.append({"role": "assistant", "content": reply})
    return reply, history_out


def speak(text):
    payload = ujson.dumps({
        "model": config.TTS_MODEL,
        "voice": config.TTS_VOICE,
        "input": text,
        "response_format": "pcm",
    }).encode("utf-8")
    resp = urequests.post(
        _TTS_URL,
        headers={
            "Authorization": "Bearer " + config.OPENAI_API_KEY,
            "Content-Type": "application/json",
            "Content-Length": str(len(payload)),
        },
        data=payload,
    )
    wav = resp.content
    resp.close()
    return wav
