"""Times the real model on an SMS and on WhatsApp chats of growing length, and reports memory.

Run from backend/ with the virtual environment active:
    python scripts/benchmark.py
"""

import ctypes
import os
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

SMS = {"text": "Your account is blocked. Send your PIN and pay the verification fee now.", "source": "sms"}
LINE = (
    "12/03/2024, 14:05 - Ann: Hello, I am calling from the bank about your account, "
    "we need to confirm a few details today please\n"
)


def memory_mb() -> str:
    if os.name != "nt":
        import resource

        return f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.0f} MB (peak)"

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ("peak", "now", "a", "b", "c", "d", "e", "f")
        ]

    kernel = ctypes.WinDLL("kernel32")
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.K32GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    c = Counters()
    c.cb = ctypes.sizeof(c)
    kernel.K32GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return f"{c.now / 2**20:.0f} MB (peak {c.peak / 2**20:.0f} MB)"


def timed(client, **request) -> tuple[float, object]:
    start = time.perf_counter()
    response = client.post("/analyze", **request)
    return time.perf_counter() - start, response


def main() -> None:
    start = time.perf_counter()
    from fastapi.testclient import TestClient

    from app.config import load_settings
    from app.main import create_app

    app = create_app(replace(load_settings(), database_url="sqlite:///:memory:", timeout_seconds=120))
    if app.state.engine.mock:
        sys.exit("The model files are missing, so these would be mock timings. Stopping.")
    client = TestClient(app)
    print(f"Model and spaCy loaded in {time.perf_counter() - start:.1f} s")
    print(f"Memory after loading: {memory_mb()}\n")

    times = [timed(client, json=SMS)[0] for _ in range(10)]
    print(f"{'Single SMS':<28} {statistics.median(times) * 1000:>8.0f} ms  (median of 10)")

    for count in (100, 500, 1000):
        seconds, r = timed(client, json={"text": LINE * count, "source": "whatsapp"})
        body = r.json()
        label = f"WhatsApp chat, {count:,} messages"
        print(f"{label:<28} {seconds:>8.1f} s   {body['verdict']}, {body['pieces_scored']} pieces")

    seconds, r = timed(client, json={"text": LINE * 2001, "source": "whatsapp"})
    print(f"{'2,001 messages':<28} {seconds * 1000:>8.0f} ms  {r.status_code}: {r.json()['detail']}")
    print(f"\nMemory at the end: {memory_mb()}")


if __name__ == "__main__":
    main()
