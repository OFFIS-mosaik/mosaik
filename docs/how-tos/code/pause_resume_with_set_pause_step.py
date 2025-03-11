import asyncio
import queue
import threading
from functools import partial

from loguru import logger
from pynput import keyboard

import mosaik
import mosaik.basic_simulators
import mosaik.util
from mosaik.async_scenario import AsyncModelFactory, AsyncWorld
from mosaik.progress import ProgressProxy
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

    END = 1000 # 1000 seconds
    pause_step = 15
    loop = asyncio.get_running_loop()
    async with mosaik.AsyncWorld(SIM_CONFIG, cache=False) as world:
        pause_queue.put((world.running, loop))
        output_dict: AsyncModelFactory = await world.start("OutputSim")
        output_model = await output_dict.Dict.create(2)
        # get progress
        progress = output_dict.get_progress()
        # End: get progress
        input = await world.start("InputSim", step_size=1)
        input_model_const = await input.A.create(1)

        world.connect(
            input_model_const[0],
            output_model[0],
            ("val_out", "value"),
        )

        world.connect(
            input_model_const[0],
            output_model[0],
            "val_out_2",
        )

        world.connect(
            input_model_const[0],
            output_model[1],
            ("val_out", "value"),
        )

        await asyncio.gather(
            world.run(until=END), pause_sim(pause_step, world, progress)
        )


# pause_sim_method
async def pause_sim(pause_step: int, world: AsyncWorld, progress: ProgressProxy):
    await progress.has_reached(pause_step)
    logger.info(
        "The simulation has reached the pre-defined pause "
        f"step {pause_step} and is now paused."
    )
    world.running.clear()
    return


# End: pause_sim_method


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
    mosaik_thread.join()
    listener.stop()

    print("Stopping listener and mosaik thread...")


main()
