import asyncio
import threading
import time
from pynput import keyboard


event: asyncio.Event = None
loop: asyncio.AbstractEventLoop = None

async def count(count_ready: threading.Event):
    c = 0
    global event, loop
    event = asyncio.Event()
    loop = asyncio.get_running_loop()
    count_ready.set()
    while True:
        print(f"{c = }")
        if not event.is_set():
            print("[sim_process] Simulation paused... waiting.")
            await event.wait()  # Wait here until the event is set again
        print("[sim_process] Simulation resumed.")
        time.sleep(1)
        c += 1

def on_press(key):
    global event, loop
    try:
        if key.char == "p":
            print("[keyboard] Pausing simulation...)")
            event.clear()  # Pause
            print("[keyboard] Paused. )")
        elif key.char == "r":
            print(
                f"[keyboard] Resuming simulation... (Before: {event.is_set() = })"
            )
            loop.call_soon_threadsafe(event.set)  # Resume
            print(
                f"[keyboard] Resumed. (After: {event.is_set() = })"
            )
    except AttributeError:
        pass


count_ready = threading.Event()

mosaik_thread = threading.Thread(
    target=asyncio.run, args=(count(count_ready),), daemon=False  # Do not use daemon thread
)
mosaik_thread.start()

count_ready.wait()
assert event is not None

listener = keyboard.Listener(on_press=on_press)
listener.start()

listener.join()
mosaik_thread.join()
