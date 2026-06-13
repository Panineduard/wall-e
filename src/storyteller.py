import tts_stream
import gc

def _sentences(text):
    text = text.replace("...", "…")
    buf = ""
    for ch in text:
        buf += ch
        if ch in ".!?…" and len(buf) > 1:
            s = buf.strip()
            if s:
                yield s
            buf = ""
    if buf.strip():
        yield buf.strip()


def _tts_chunks(text, max_chars=700):
    chunk = ""
    for sentence in _sentences(text):
        if len(sentence) > max_chars:
            parts = [p.strip() for p in sentence.split(",") if p.strip()]
            for part in parts:
                if len(chunk) + len(part) + 2 > max_chars:
                    if chunk:
                        yield chunk.strip()
                    chunk = part + ", "
                else:
                    chunk += part + ", "
        elif len(chunk) + len(sentence) + 1 > max_chars:
            if chunk:
                yield chunk.strip()
            chunk = sentence + " "
        else:
            chunk += sentence + " "
    if chunk.strip():
        yield chunk.strip()


def tell(path):
    print("Storyteller: reading", path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        print("File not found:", path)
        return False

    for i, chunk in enumerate(_tts_chunks(text)):
        print("TTS chunk:", len(chunk), "chars")
        for attempt in range(3):
            gc.collect()
            try:
                tts_stream.speak_stream(chunk)
                break
            except Exception as e:
                print("TTS error (attempt", attempt + 1, "):", e)
                if attempt == 2:
                    return False
    return True
