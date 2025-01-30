import threading
from time import sleep
from typing import Optional

import mosaik_api_v3
from mosaik_api_v3 import InputData, OutputData, OutputRequest, Time

META: mosaik_api_v3.Meta = {
    "api_version": "3.0",
    "type": "time-based",
    "models": {},
}


class Sim(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(META)

    def step(self, time: Time, inputs: InputData, max_advance: Time) -> Optional[Time]:
        threading.Thread(target=delayed_greet).start()
        return time + 1

    def get_data(self, outputs: OutputRequest) -> OutputData:
        return {}


def delayed_greet():
    print("Start delayed_greet")
    sleep(2)
    print("Hello from delayed_greet")


if __name__ == "__main__":
    mosaik_api_v3.start_simulation(Sim())
