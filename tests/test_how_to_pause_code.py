import asyncio
import queue
import threading
import unittest
from functools import partial
from types import SimpleNamespace

# Import the functions from your module.
# For example, if your file is named `pause_resume.py`:
from test_pause_resume import start_mosaik, on_press

# Create a fake key object with a 'char' attribute
class FakeKey:
    def __init__(self, char):
        self.char = char

class TestPauseResume(unittest.TestCase):
    def setUp(self):
        # Create a queue to receive the (event, loop) tuple from the simulation thread.
        self.pause_queue = queue.Queue()
        # Start the mosaik simulation in a separate thread.
        self.mosaik_thread = threading.Thread(
            target=asyncio.run,
            args=(start_mosaik(self.pause_queue),),
            daemon=True,
        )
        self.mosaik_thread.start()
        # Wait for the simulation to put the (event, loop) tuple into the queue.
        self.event, self.loop = self.pause_queue.get(timeout=10)

    def tearDown(self):
        # Wait for the simulation thread to finish.
        self.mosaik_thread.join(timeout=10)

    def test_pause_and_resume(self):
        # The event should be set (i.e. running) initially.
        self.assertTrue(self.event.is_set(), msg="Event should be initially set (running)")

        # Create partial function with our event and loop.
        on_press_with_args = partial(on_press, event=self.event, loop=self.loop)

        # Simulate pressing the pause key "p"
        fake_pause_key = FakeKey("p")
        on_press_with_args(fake_pause_key)
        # Allow some time for the event to process (if needed)
        asyncio.run_coroutine_threadsafe(asyncio.sleep(0.1), self.loop).result()
        self.assertFalse(self.event.is_set(), msg="Event should be cleared (paused) after 'p' is pressed")

        # Simulate pressing the resume key "r"
        fake_resume_key = FakeKey("r")
        on_press_with_args(fake_resume_key)
        asyncio.run_coroutine_threadsafe(asyncio.sleep(0.1), self.loop).result()
        self.assertTrue(self.event.is_set(), msg="Event should be set (resumed) after 'r' is pressed")


if __name__ == "__main__":
    unittest.main()
