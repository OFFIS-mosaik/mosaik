import asyncio
import queue
import runpy
import threading
from functools import partial


# A simple fake key class to mimic pynput's key object.
class FakeKey:
    def __init__(self, char: str):
        self.char = char


def test_pause_resume():
    pause_queue: queue.Queue[tuple[asyncio.Event, asyncio.AbstractEventLoop]] = (
        queue.Queue()
    )
    script_path = "docs/how-tos/code/pause_resume_feature.py"
    result = runpy.run_path(script_path)
    start_mosaik = result["start_mosaik"]
    on_press = result["on_press"]

    # Start the mosaik simulation in a separate thread.
    mosaik_thread = threading.Thread(
        target=asyncio.run,
        args=(start_mosaik(pause_queue),),
        daemon=True,
    )
    mosaik_thread.start()
    try:
        event, loop = pause_queue.get(timeout=10)
    except Exception as e:
        assert False, f"Timed out waiting for simulation to start: {e}"
    asyncio.run_coroutine_threadsafe(asyncio.sleep(0.0), loop).result()
    assert not event.is_set(), "Expected simulation to be paused initially"
    on_press_with_args = partial(on_press, event=event, loop=loop)

    # Simulate pressing "r" to resume the simulation.
    fake_pause_key = FakeKey("r")
    on_press_with_args(fake_pause_key)
    asyncio.run_coroutine_threadsafe(asyncio.sleep(0.0), loop).result()
    assert event.is_set(), "Expected event to be cleared (paused) after pressing 'r'"

    # Simulate pressing "p" to pause the simulation.
    fake_resume_key = FakeKey("p")
    on_press_with_args(fake_resume_key)
    asyncio.run_coroutine_threadsafe(asyncio.sleep(0.0), loop).result()
    assert not event.is_set(), "Expected event to be set (resumed) after pressing 'p'"

    # Simulate pressing "r" to resume the simulation instead.
    fake_pause_key = FakeKey("r")
    on_press_with_args(fake_pause_key)
    asyncio.run_coroutine_threadsafe(asyncio.sleep(0.0), loop).result()
    assert event.is_set(), "Expected event to be cleared (paused) after pressing 'r'"

    mosaik_thread.join(timeout=10)
    assert not mosaik_thread.is_alive()
