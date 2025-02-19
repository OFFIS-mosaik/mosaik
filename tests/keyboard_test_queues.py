import asyncio
import threading
import time
from pynput import keyboard
import queue
from functools import partial


async def count(
    my_first_very_own_queue: queue.Queue[
        tuple[asyncio.Event, asyncio.AbstractEventLoop]
    ],
):
    c = 0
    event = asyncio.Event()
    loop = asyncio.get_running_loop()
    my_first_very_own_queue.put((event, loop))
    while True:
        print(f"{c = }")
        if not event.is_set():
            print("[sim_process] Simulation paused... waiting.")
            await event.wait()  # Wait here until the event is set again
        print("[sim_process] Simulation resumed.")
        time.sleep(1)
        c += 1


def on_press(key, event, loop):
    try:
        if key.char == "p":
            print("[keyboard] Pausing simulation...)")
            event.clear()  # Pause
            print("[keyboard] Paused. )")
        elif key.char == "r":
            print(f"[keyboard] Resuming simulation... (Before: {event.is_set() = })")
            loop.call_soon_threadsafe(event.set)  # Resume
            print(f"[keyboard] Resumed. (After: {event.is_set() = })")
    except AttributeError:
        pass


def main():
    my_very_own_queue: queue.Queue[tuple[asyncio.Event, asyncio.AbstractEventLoop]] = (
        queue.Queue()
    )

    mosaik_thread = threading.Thread(
        target=asyncio.run,
        args=(count(my_very_own_queue),),
        daemon=False,
    )
    mosaik_thread.start()

    (event, loop) = my_very_own_queue.get()

    on_press_with_args = partial(on_press, event=event, loop=loop)

    listener = keyboard.Listener(on_press=on_press_with_args)
    listener.start()

    listener.join()
    mosaik_thread.join()


if __name__ == "__main__":
    main()
