from __future__ import annotations

# Simulation set up
import asyncio
import queue
import threading
from functools import partial

from loguru import logger
from pynput import keyboard

import mosaik
import mosaik.basic_simulators
import mosaik.util
from mosaik.scenario import SimConfig

END = 10000


async def start_mosaik(
    pause_queue: queue.Queue[tuple[asyncio.Event, asyncio.AbstractEventLoop]],
    END: int,
):
    SIM_CONFIG: SimConfig = {
        "OutputSim": {
            "python": "mosaik.basic_simulators:OutputSimulator",
        },
        "InputSim": {
            "python": "tests.simulators.generic_test_simulator:TestSim",
        },
    }

    loop = asyncio.get_running_loop()
    async with mosaik.AsyncWorld(SIM_CONFIG) as world:
        pause_queue.put((world.running, loop))
        # End: Simulation set up

        # Simulator set up
        output_dict = await world.start("OutputSim")
        output_model = await output_dict.Dict.create(2)

        input = await world.start("InputSim", step_size=1)
        input_model_const = await input.A.create(1)

        world.connect(
            input_model_const[0],
            output_model[0],
            ("val_out", "value"),
        )

        world.connect(input_model_const[0], output_model[0], "val_out_2")

        world.connect(
            input_model_const[0],
            output_model[1],
            ("val_out", "value"),
        )

        await world.run(until=END)
        # End: Simulator set up


# Keyboard input
def on_press(key, event, loop):
    try:
        if key.char == "p":
            if event and loop.is_running():
                loop.call_soon_threadsafe(lambda: event.clear())  # Pause
                logger.info("mosaik simulation is paused.")
        elif key.char == "r":
            if event and loop.is_running():
                loop.call_soon_threadsafe(lambda: event.set())  # Resume
                logger.info("mosaik simulation is resumed.")
    except AttributeError:
        # This handles cases where `key` does not have a `char`
        # attribute, which happens for special keys like Shift or Ctrl.
        # Instead of failing, the function just ignores these cases.
        pass


# End: Keyboard input


# Start keyboard listener and mosaik in different threads
def main():
    comm_queue: queue.Queue[tuple[asyncio.Event, asyncio.AbstractEventLoop]] = (
        queue.Queue()
    )

    mosaik_thread = threading.Thread(
        target=asyncio.run,
        args=(start_mosaik(comm_queue, END),),
        daemon=True,
    )
    mosaik_thread.start()

    world_running, loop = comm_queue.get()

    on_press_with_args = partial(on_press, event=world_running, loop=loop)
    listener = keyboard.Listener(on_press=lambda key: on_press_with_args(key))
    listener.start()
    mosaik_thread.join()

    listener.stop()


if __name__ == "__main__":
    main()
# End: Start keyboard listener and mosaik in different threads
