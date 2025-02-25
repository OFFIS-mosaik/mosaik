import asyncio
import queue
import threading
from functools import partial

# Import the functions from the correct module path.
from mosaik.docs.how_tos.code.pause_resume_feature import start_mosaik, on_press


# A simple fake key class to mimic pynput's key object.
class FakeKey:
    def __init__(self, char: str):
        self.char = char


def test_pause_resume():
    # Create a queue to receive the (event, loop) tuple from start_mosaik.
    pause_queue: queue.Queue[tuple[asyncio.Event, asyncio.AbstractEventLoop]] = queue.Queue()

    # Start the mosaik simulation in a separate thread.
    mosaik_thread = threading.Thread(
        target=asyncio.run,
        args=(start_mosaik(pause_queue),),
        daemon=True,
    )
    mosaik_thread.start()

    # Wait for the simulation to provide the event and loop.
    try:
        event, loop = pause_queue.get(timeout=10)
    except Exception as e:
        assert False, f"Timed out waiting for simulation to start: {e}"

    # Allow a short delay to ensure the simulation is fully started.
    asyncio.run_coroutine_threadsafe(asyncio.sleep(0.1), loop).result()

    # Initially, the simulation should be running so the event should be set.
    assert event.is_set(), "Expected event to be set (running) initially"

    # Prepare the on_press function with our event and loop.
    on_press_with_args = partial(on_press, event=event, loop=loop)

    # Simulate pressing "p" to pause the simulation.
    fake_pause_key = FakeKey("p")
    on_press_with_args(fake_pause_key)
    asyncio.run_coroutine_threadsafe(asyncio.sleep(0.1), loop).result()

    # After pressing "p", the event should be cleared (paused).
    assert not event.is_set(), "Expected event to be cleared (paused) after pressing 'p'"

    # Simulate pressing "r" to resume the simulation.
    fake_resume_key = FakeKey("r")
    on_press_with_args(fake_resume_key)
    asyncio.run_coroutine_threadsafe(asyncio.sleep(0.1), loop).result()

    # After pressing "r", the event should be set (resumed).
    assert event.is_set(), "Expected event to be set (resumed) after pressing 'r'"

    # Optionally, wait for the simulation thread to finish.
    mosaik_thread.join(timeout=10)

test_pause_resume()