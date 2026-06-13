import socket
import select
import ujson
import _thread

_HTML_PATH = "/static/index.html"
_status = "Готово"


def set_status(text):
    global _status
    _status = text


class WebServer:
    def __init__(self, motors, on_trigger, on_content, servos=None):
        self._motors     = motors
        self._servos     = servos
        self._on_trigger = on_trigger
        self._on_content = on_content
        self._srv        = None
        # pending action from web UI — picked up by main thread
        self._pending    = None   # None | ("trigger",) | ("content", kind, key)
        self._lock       = _thread.allocate_lock()

    def start(self):
        self._srv = socket.socket()
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.setblocking(False)
        self._srv.bind(("0.0.0.0", 80))
        self._srv.listen(2)
        print("[WEB] listening on port 80")
        _thread.start_new_thread(self._loop, ())

    def ready(self):
        set_status("Готово")

    def pop_pending(self):
        """Main thread calls this to pick up a queued action."""
        with self._lock:
            p = self._pending
            self._pending = None
            return p

    def _set_pending(self, action):
        with self._lock:
            if self._pending is None:
                self._pending = action

    def _loop(self):
        while True:
            try:
                r, _, _ = select.select([self._srv], [], [], 0.05)
                if r:
                    conn, _ = self._srv.accept()
                    conn.setblocking(True)
                    self._handle(conn)
            except Exception as e:
                print("[WEB] loop error:", e)

    def _handle(self, conn):
        try:
            f = conn.makefile("rb")
            line = f.readline().decode().strip()
            while True:
                h = f.readline()
                if not h or h == b"\r\n":
                    break

            parts = line.split()
            path = parts[1] if len(parts) > 1 else "/"
            print("[WEB]", path)

            if path == "/" or path == "/index.html":
                self._serve_file(conn, _HTML_PATH, "text/html; charset=utf-8")

            elif path == "/status":
                self._json(conn, {"status": _status})

            elif path == "/listen":
                self._json(conn, {"ok": True})
                self._set_pending(("trigger",))

            elif path.startswith("/tale"):
                key = self._param(path, "key")
                self._json(conn, {"ok": True})
                self._set_pending(("content", "tale", key))

            elif path.startswith("/song"):
                key = self._param(path, "key")
                self._json(conn, {"ok": True})
                self._set_pending(("content", "song", key))

            elif path == "/stopdance":
                self._json(conn, {"ok": True})
                self._set_pending(("stopdance",))

            elif path == "/dance.mp3":
                self._serve_file(conn, "/static/dance.mp3", "audio/mpeg")

            elif path == "/dance":
                self._json(conn, {"ok": True})
                self._set_pending(("dance",))

            elif path == "/disco":
                self._json(conn, {"ok": True})
                self._set_pending(("disco",))

            elif path.startswith("/head"):
                if self._servos:
                    import config
                    d = self._param(path, "dir")
                    c = config.SERVO_NECK_CENTER
                    if d == "left":     self._servos.neck.write(c - 40)
                    elif d == "right":  self._servos.neck.write(c + 40)
                    elif d == "center": self._servos.neck.write(c)
                self._json(conn, {"ok": True})

            elif path.startswith("/motor"):
                action = self._param(path, "action")
                if self._motors:
                    if action == "forward":
                        self._motors.forward()
                        if self._servos: self._servos.start_driving()
                    elif action == "backward": self._motors.backward()
                    elif action == "left":     self._motors.turn_left()
                    elif action == "right":    self._motors.turn_right()
                    elif action == "stop":
                        self._motors.stop()
                        if self._servos: self._servos.stop_driving()
                self._json(conn, {"ok": True})

            else:
                conn.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")

        except Exception as e:
            print("[WEB] handle error:", e)
        finally:
            try:
                conn.close()
            except:
                pass

    def _json(self, conn, obj):
        body = ujson.dumps(obj).encode()
        conn.write(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n"
            + body
        )

    def _serve_file(self, conn, path, ctype):
        try:
            with open(path, "rb") as f:
                body = f.read()
            conn.write(
                ("HTTP/1.1 200 OK\r\nContent-Type: " + ctype +
                 "\r\nContent-Length: " + str(len(body)) +
                 "\r\nConnection: close\r\n\r\n").encode()
                + body
            )
        except OSError:
            conn.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")

    def _param(self, path, key):
        if "?" not in path:
            return ""
        query = path.split("?", 1)[1]
        for part in query.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                if k == key:
                    return v
        return ""
