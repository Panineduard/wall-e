import utime
from machine import Pin

import wifi_manager
import audio_in
import audio_out
import ai_client
import storyteller
import tts_stream
import web_server
import config

# ── optional hardware ────────────────────────────────────────────────────────
if config.ENABLE_MOTORS:
    import motors
    _motors = motors.Motors()
else:
    _motors = None

if config.ENABLE_SERVOS:
    import servos
    _servos = servos.Servos()
else:
    _servos = None

if config.ENABLE_DISTANCE:
    import distance

_button  = Pin(config.BUTTON_PIN, Pin.IN, Pin.PULL_UP)
_history = []
_mic     = None   # global mic — deinited during playback, reinited after


def _mic_on():
    global _mic
    if _mic is None:
        _mic = audio_in.make_mic()


def _mic_off():
    global _mic
    if _mic is not None:
        _mic.deinit()
        _mic = None


# ── helpers ──────────────────────────────────────────────────────────────────
def _avoid():
    if not _motors:
        return
    _motors.stop()
    utime.sleep_ms(200)
    _motors.backward()
    utime.sleep_ms(600)
    _motors.turn_right()
    utime.sleep_ms(500)
    _motors.stop()


def _speak(text):
    """Deinit mic, play TTS, reinit mic with flush."""
    import gc
    gc.collect()
    _mic_off()
    if _servos:
        _servos.start_talking()
    try:
        tts_stream.speak_stream(text)
    except Exception as e:
        print("TTS error:", e)
    finally:
        if _servos:
            _servos.stop_talking()
        utime.sleep_ms(300)
        _mic_on()
        audio_in.flush(_mic, ms=1500)


def _talk():
    global _history

    print("Listening...")
    if _servos:
        _servos.neck.write(60)

    wav = audio_in.record_vad(_mic)

    if _servos:
        _servos.neck.write(config.SERVO_NECK_CENTER)

    if wav is None:
        return

    print("Transcribing...")
    try:
        text = ai_client.transcribe(wav)
    except Exception as e:
        print("STT error:", e)
        return
    print("You said: [" + str(len(text)) + " chars]")
    if not text:
        return

    print("Thinking...")
    if _servos:
        _servos.neck.write(120)
    try:
        reply, _history = ai_client.chat(text, _history)
        if len(_history) > 10:
            _history = _history[-10:]
    except Exception as e:
        print("LLM error:", e)
        if _servos:
            _servos.neck.write(config.SERVO_NECK_CENTER)
        return
    print("Wall-E reply: [" + str(len(reply)) + " chars]")

    if _servos:
        _servos.neck.write(config.SERVO_NECK_CENTER)

    # LLM-driven tale / song
    if reply.startswith("[TALE:"):
        key = reply[6:reply.find("]")]
        _mic_off()
        if _servos:
            _servos.start_talking()
        try:
            storyteller.tell("/tales/" + key + ".txt")
        finally:
            if _servos:
                _servos.stop_talking()
            utime.sleep_ms(300)
            _mic_on()
            audio_in.flush(_mic, ms=1500)
        return

    if reply.startswith("[SING:"):
        key = reply[6:reply.find("]")]
        _mic_off()
        if _servos:
            _servos.start_talking()
        try:
            tts_stream.speak_stream("Зараз заспіваю!")
            storyteller.tell("/songs/" + key + ".txt")
        except Exception as e:
            print("Sing error:", e)
        finally:
            if _servos:
                _servos.stop_talking()
            utime.sleep_ms(300)
            _mic_on()
            audio_in.flush(_mic, ms=1500)
        return

    print("Speaking...")
    if _servos:
        _servos.wave(1)
    _speak(reply)

    if _servos:
        _servos.reset()


# ── conversation loop ────────────────────────────────────────────────────────
def _converse(ws, duration_ms=86400000):
    global _history
    _history = []
    deadline = utime.ticks_add(utime.ticks_ms(), duration_ms)
    print("Ready. Press BOOT or use web UI.")
    utime.sleep_ms(1000)  # ignore spurious button press during boot

    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        pending = ws.pop_pending()
        if pending:
            if pending[0] == "trigger":
                web_server.set_status("Слухаю...")
                _talk()
                ws.ready()
            elif pending[0] == "content":
                _, kind, key = pending
                _web_on_content(kind, key, web_server.set_status)
                ws.ready()
            elif pending[0] == "dance":
                web_server.set_status("Танцюю...")
                _dance()
                ws.ready()
            elif pending[0] == "disco":
                web_server.set_status("Диско!")
                _disco()
                ws.ready()
            elif pending[0] == "stopdance":
                _stop_dance_flag[0] = True

        if config.ENABLE_DISTANCE and distance.is_obstacle():
            _avoid()
            continue

        if _button.value() == 0:
            utime.sleep_ms(50)
            if _button.value() == 0:
                while _button.value() == 0:
                    utime.sleep_ms(10)
                _talk()
                ws.ready()

        utime.sleep_ms(50)

    _history = []
    _mic_off()
    if _servos:
        _servos.reset()


# ── dance / disco ────────────────────────────────────────────────────────────
_SONG_DURATION_MS = 210000
_stop_dance_flag = [False]

def _run_dance(announce=None):
    _stop_dance_flag[0] = False
    if announce:
        _speak(announce)
    if _motors: _motors.start_dancing()
    if _servos: _servos.start_dancing()
    print("Dancing...")
    deadline = utime.ticks_add(utime.ticks_ms(), _SONG_DURATION_MS)
    try:
        while utime.ticks_diff(deadline, utime.ticks_ms()) > 0 and not _stop_dance_flag[0]:
            utime.sleep_ms(200)
    finally:
        if _motors: _motors.stop_dancing()
        if _servos: _servos.stop_dancing()
        print("Dance done")

def _dance():
    _run_dance()

def _disco():
    try:
        announce, _ = ai_client.chat(
            "Ти Валлі — скажи одне смішне речення щоб оголосити початок дискотеки. Без тегів.",
            []
        )
    except Exception:
        announce = "Увага! Починаємо диско!"
    _run_dance(announce=announce)


# ── web handlers ─────────────────────────────────────────────────────────────
def _web_on_content(kind, key, status_fn):
    path = "/" + kind + "s/" + key + ".txt"
    status_fn("Розповідаю..." if kind == "tale" else "Співаю...")
    _mic_off()
    if _servos:
        _servos.start_talking()
    try:
        storyteller.tell(path)
    finally:
        if _servos:
            _servos.stop_talking()
        utime.sleep_ms(300)
        _mic_on()
        audio_in.flush(_mic, ms=1500)


# ── boot ─────────────────────────────────────────────────────────────────────
def main():
    print("Wall-E booting... (7s upload window)")
    utime.sleep(7)
    wifi_manager.connect()
    ip = wifi_manager.ip()
    print("WiFi OK —", ip)
    print("Web UI: http://" + ip)

    if _servos:
        _servos.wave(2)

    _ws = web_server.WebServer(_motors, None, None, servos=_servos)
    _ws.start()

    _mic_on()
    print("Ready. Open http://" + wifi_manager.ip())
    print("Greeting: asking GPT...")
    greeting = None
    try:
        greeting, _ = ai_client.chat(
            "Ти — Валлі, смішний маленький робот. Скажи 'Воллі тута!' і додай один кумедний випадковий факт про штучний інтелект або життя. Без тегів, одне-два речення.",
            []
        )
        print("Greeting:", len(greeting), "chars")
    except Exception as e:
        print("Greeting error:", e)
    if not greeting:
        greeting = "Воллі тута! Цікавий факт — роботи не сплять, але дуже люблять, коли їх заряджають!"
    print("Speaking greeting...")
    _speak(greeting)
    print("Greeting done")
    _converse(_ws)


main()
