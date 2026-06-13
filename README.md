# Wall-E Robot — AI Talking Robot on ESP32

A MicroPython-powered Wall-E robot that listens, thinks, and talks using cloud AI (Ukrainian language).

## Hardware

| Part | Role |
|------|------|
| LILYGO TTGO T8 V1.7 (ESP32-WROVER) | Brain — MicroPython, WiFi, 4 MB PSRAM |
| MAX98357 I2S mono amplifier (3 W) | Audio output → speaker |
| INMP441 MEMS microphone (I2S) | Audio input ← microphone |
| L298N dual motor driver | Track motors (left + right) |
| 2× servo motors | Hands (left + right) |
| Servo motor | Neck / head pan |
| HC-SR04 ultrasonic sensor | Obstacle avoidance |

## AI Pipeline

```
[BOOT button] or [Web UI button]
        │
        ▼
  MEMS mic (I2S)
        │  PCM audio buffer (in PSRAM)
        ▼
  Whisper API  ──→  transcribed text (Ukrainian)
        │
        ▼
  GPT-4o       ──→  reply text (Ukrainian)
        │
        ▼
  OpenAI TTS   ──→  PCM audio (voice: alloy)
        │
        ▼
  MAX98357 (I2S) ──→ speaker
```

## Project Layout

```
wall-e/
├── src/                  # MicroPython source — deploy to board
│   ├── main.py           # State machine (idle → listen → think → speak)
│   ├── config.py         # Pin map, WiFi credentials, API keys, feature flags
│   ├── wifi_manager.py   # WiFi connect / auto-reconnect
│   ├── motors.py         # L298N PWM track control
│   ├── servos.py         # Hand + neck servos
│   ├── distance.py       # HC-SR04 distance measurement
│   ├── audio_in.py       # I2S mic → PCM capture → WAV bytes
│   ├── audio_out.py      # WAV bytes → I2S → MAX98357
│   └── ai_client.py      # Whisper STT + GPT-4o + OpenAI TTS
├── tools/
│   └── upload.py         # Bulk upload src/ to board via mpremote
├── firmware/             # MicroPython .bin file (not committed)
├── wall-e.ino            # Original Arduino demo (reference only)
└── README.md
```

## Wiring

### Power rails

| TTGO T8 Pin | Voltage | Connect to |
|-------------|---------|------------|
| 3V3 | 3.3 V | MEMS mic VDD only |
| 5V | 5 V | MAX98357 VIN, HC-SR04 VCC, L298N logic |
| GND | 0 V | all modules — any GND pin, they are all shared |

> All GND pins on the board are internally connected. One GND pin per module is enough; you do not need a separate GND for each one.

---

### MEMS Microphone (INMP441) → TTGO T8

| Mic Pin | TTGO T8 | Notes |
|---------|---------|-------|
| VDD | 3V3 | 3.3 V only — 5 V will damage it |
| GND | GND | |
| SCK (BCLK) | GPIO 32 | bit clock |
| WS (LRC) | GPIO 25 | word select |
| SD (DOUT) | GPIO 33 | data out |
| L/R | GND | **must be connected** — selects left channel |

---

### MAX98357 Amplifier → TTGO T8

| Amp Pin | TTGO T8 | Notes |
|---------|---------|-------|
| VIN | 5V | |
| GND | GND | |
| BCLK | GPIO 26 | bit clock |
| LRC | GPIO 22 | word select |
| DIN | GPIO 21 | data in |
| SD | GPIO 19 | shutdown — HIGH = on, LOW = mute |
| GAIN | — | see volume note below |

Connect your speaker (4 Ω or 8 Ω) to the amp's **+** and **−** output terminals.

**Volume / GAIN pin:**

| GAIN wiring | Volume |
|-------------|--------|
| Unconnected (floating) | 9 dB — default |
| GAIN → GND | 6 dB — quieter |
| GAIN → SD pin (GPIO 19) | 15 dB — **maximum, recommended** |

> To get maximum volume with zero CPU cost: bridge the **GAIN** pin directly to the **SD** pin on the MAX98357 board with a short wire or solder bridge.

---

### L298N Motor Driver → TTGO T8

| L298N Pin | TTGO T8 | Notes |
|-----------|---------|-------|
| IN1 | GPIO 27 | right motor direction |
| IN2 | GPIO 4 | right motor direction |
| ENA | GPIO 14 | right motor PWM speed — add 10kΩ pull-down to GND |
| IN3 | GPIO 13 | left motor direction |
| IN4 | GPIO 12 | left motor direction |
| ENB | GPIO 15 | left motor PWM speed — add 10kΩ pull-down to GND |
| 5V | 5V | logic power |
| GND | GND | |

---

### Servos → TTGO T8

| Servo | TTGO T8 | Notes |
|-------|---------|-------|
| Right hand signal | GPIO 5 | PWM 50 Hz |
| Left hand signal | GPIO 18 | PWM 50 Hz |
| Neck signal | GPIO 23 | PWM 50 Hz |
| VCC (all) | 5V | |
| GND (all) | GND | |

---

### HC-SR04 Distance Sensor → TTGO T8

| HC-SR04 Pin | TTGO T8 | Notes |
|-------------|---------|-------|
| VCC | 5V | |
| GND | GND | |
| TRIG | GPIO 2 | |
| ECHO | GPIO 36 | input-only pin, 3.3 V safe |

---

### Trigger Button

The built-in **BOOT button** (GPIO 0) is used as the talk trigger — no extra wiring needed.

---

## Getting Started

### 1. Create a virtual environment

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

> If PowerShell blocks script execution run:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 2. Install host tools

```powershell
pip install mpremote esptool
```

### 3. Flash MicroPython firmware

Download **Firmware (Support for SPIRAM / WROVER)** from:
`https://micropython.org/download/ESP32_GENERIC/`

Place the `.bin` file in the `firmware/` folder, then:

```powershell
# Erase chip
esptool --chip esp32 --port COM7 erase_flash

# Flash (replace filename with your download)
esptool --chip esp32 --port COM7 --baud 460800 write_flash -z 0x1000 firmware\ESP32_GENERIC-SPIRAM-20260406-v1.28.0.bin
```

### 4. Configure the project

Edit `src/config.py`:
- Set `WIFI_SSID` and `WIFI_PASSWORD`
- Set `OPENAI_API_KEY`
- Set feature flags for hardware not yet connected:

```python
ENABLE_MOTORS   = False   # set True when L298N is wired
ENABLE_SERVOS   = False   # set True when servos are wired
ENABLE_DISTANCE = False   # set True when HC-SR04 is wired
```

### 5. Upload source files

```powershell
python tools/upload.py COM7
```

### 6. Run

Open REPL and soft-reboot:

```powershell
mpremote connect COM7 repl
# then press Ctrl+D to reboot
```

Or just reset the board — `main.py` runs automatically on boot.

Open `http://<board-ip>` in a browser to use the web UI (talk, fairy tales, songs, dance, motor control, head control).

Or press the **BOOT button** on the board to talk directly.

---

## Iterating after changes

```powershell
# Upload a single changed file
mpremote connect COM7 fs cp src/audio_in.py :/audio_in.py

# Upload everything
python tools/upload.py COM7

# Reset board
mpremote connect COM7 reset
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Open REPL | `mpremote connect COM7 repl` |
| List files on board | `mpremote connect COM7 fs ls /` |
| Upload one file | `mpremote connect COM7 fs cp src/X.py :/X.py` |
| Upload all | `python tools/upload.py COM7` |
| Reset board | `mpremote connect COM7 reset` |
| Watch serial logs | `mpremote connect COM7` |

---

## State Machine

```
IDLE ──[button]──▶ LISTENING ──[4 s]──▶ THINKING
                                              │
                   IDLE ◀──── SPEAKING ◀──────┘
                   IDLE ◀── AVOIDING (obstacle detected)
```

## Dependencies (MicroPython built-ins — nothing to install on board)

- `machine.I2S` — audio in/out
- `machine.PWM` + `machine.Pin` — servos, motors
- `network` — WiFi
- `urequests` — HTTP API calls
- `ujson` — JSON parsing
- `utime` — timing
