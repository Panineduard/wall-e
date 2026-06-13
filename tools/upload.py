"""Upload src/ and static/ to the board via mpremote."""
import subprocess
import sys
import os
import time

ROOT = os.path.join(os.path.dirname(__file__), "..")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def mkdir(port, path):
    run(["mpremote", "connect", port, "fs", "mkdir", path])


def upload_file(port, local, remote, retries=5):
    for attempt in range(retries):
        result = run(["mpremote", "connect", port, "fs", "cp", local, remote])
        if result.returncode == 0:
            return True
        if attempt < retries - 1:
            time.sleep(1)
    print(f"  ERROR: {result.stderr.strip()[:120]}")
    return False


def upload_dir(port, local_dir, remote_dir, exts):
    if not os.path.isdir(local_dir):
        return 0, 0
    mkdir(port, remote_dir)
    files = [f for f in os.listdir(local_dir) if any(f.endswith(e) for e in exts)]
    ok = 0
    for fname in files:
        local = os.path.join(local_dir, fname)
        remote = remote_dir + "/" + fname
        print(f"  {remote} ...", end=" ", flush=True)
        if upload_file(port, local, ":" + remote):
            print("OK")
            ok += 1
        else:
            print("FAILED")
    return ok, len(files)


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/upload.py COM<N>")
        sys.exit(1)

    port = sys.argv[1]
    total_ok = total_all = 0

    # src/ → board root
    src_dir = os.path.join(ROOT, "src")
    files = [f for f in os.listdir(src_dir) if f.endswith(".py")]
    for fname in files:
        local = os.path.join(src_dir, fname)
        print(f"  /{fname} ...", end=" ", flush=True)
        if upload_file(port, local, f":/{fname}"):
            print("OK"); total_ok += 1
        else:
            print("FAILED")
        total_all += 1

    # static/ → /static/
    ok, n = upload_dir(port, os.path.join(ROOT, "static"), "/static", [".html", ".css", ".js", ".mp3"])
    total_ok += ok; total_all += n

    # content/tales/ → /tales/
    ok, n = upload_dir(port, os.path.join(ROOT, "content", "tales"), "/tales", [".txt"])
    total_ok += ok; total_all += n

    # content/songs/ → /songs/
    ok, n = upload_dir(port, os.path.join(ROOT, "content", "songs"), "/songs", [".txt"])
    total_ok += ok; total_all += n

    print(f"\nDone. {total_ok}/{total_all} files uploaded.")


if __name__ == "__main__":
    main()
