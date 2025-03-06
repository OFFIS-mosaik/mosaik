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


async def start_mosaik(
    pause_queue: queue.Queue[tuple[asyncio.Event, asyncio.AbstractEventLoop]],
):
    SIM_CONFIG: SimConfig = {
        "OutputSim": {
            "python": "mosaik.basic_simulators:OutputSimulator",
        },
        "InputSim": {
            "python": "tests.simulators.generic_test_simulator:TestSim",
        },
    }
    global END
    END = 300
    event = asyncio.Event()
    loop = asyncio.get_running_loop()
    world = mosaik.AsyncWorld(SIM_CONFIG, pause_step=15000)
    world.running = event
    pause_queue.put((event, loop))
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
            loop.call_soon_threadsafe(event.clear())  # Pause
            logger.info("mosaik simulation has been paused.")
        elif key.char == "r":
            loop.call_soon_threadsafe(event.set)  # Resume
            logger.info("mosaik simulation is resuming.")
    except AttributeError:
        pass


# End: Keyboard input


# Start keyboard listener and mosaik in different threads
def main():
    comm_queue: queue.Queue[tuple[asyncio.Event, asyncio.AbstractEventLoop]] = (
        queue.Queue()
    )

    mosaik_thread = threading.Thread(
        target=asyncio.run,
        args=(start_mosaik(comm_queue),),
        daemon=False,
    )
    mosaik_thread.start()

    (event, loop) = comm_queue.get()

    on_press_with_args = partial(on_press, event=event, loop=loop)

    listener = keyboard.Listener(on_press=on_press_with_args)
    listener.start()

    listener.join()
    mosaik_thread.join()


if __name__ == "__main__":
    main()
# End: Start keyboard listener and mosaik in different threads
