import mosaik_api_v3

META: mosaik_api_v3.Meta = {
    "api_version": "3.0",
    "type": "hybrid",  # This ensures that we get called at time 0
    "models": {
        "Countdown": {
            "public": True,
            "trigger": ["Set"],
            "non-trigger": [],
            "non-persistent": ["Warning", "ZeroReached"],
            "persistent": [],
        }
    },
}


class CountdownSimulator(mosaik_api_v3.Simulator):
    created = False
    c: int = 10
    output: tuple[mosaik_api_v3.Time, str] | None = None

    def __init__(self):
        super().__init__(META)

    def create(
        self, num: int, model: mosaik_api_v3.ModelName
    ) -> list[mosaik_api_v3.CreateResult]:
        assert model == "Countdown"
        assert num == 1
        assert not self.created
        self.created = True
        return [{"type": "Countdown", "eid": "Countdown"}]

    def step(
        self,
        time: mosaik_api_v3.Time,
        inputs: mosaik_api_v3.InputData,
        max_advance: mosaik_api_v3.Time,
    ) -> mosaik_api_v3.Time | None:
        if input := inputs.get("Countdown"):
            # If we get multiple Set inputs at once, use the smallest.
            self.c = min(input["Set"].values())

        if self.c < 0:
            return None

        max_steps = max_advance - time
        if self.c - max_steps <= 2:
            warning_time = time + (self.c - 2)
            self.output = (warning_time, "Warning")
            self.c = 1
            return warning_time + 1

        if self.c - max_steps <= 0:
            zero_time = time + self.c
            self.output = (zero_time, "ZeroReached")
            self.c = -1
            return zero_time + 1

        self.c -= max_steps + 1
        return max_advance + 1

    def get_data(
        self, outputs: mosaik_api_v3.OutputRequest
    ) -> mosaik_api_v3.OutputData:
        if self.output:
            time, event_type = self.output
            self.output = None
            return {
                "time": time,
                "Countdown": {
                    # `None` as our events carry no further information
                    event_type: None
                },
            }
        else:
            return {}


def test_script():
    sim = CountdownSimulator()

    def test_step(time: int, value: int | None, max_advance: int):
        print(
            f"Stepping at time {time} with input {value} and max_advance {max_advance}"
        )
        input = {"Countdown": {"Set": {"": value}}} if value else {}
        next_step = sim.step(time, input, max_advance)
        print(f"  - requested next step at time {next_step}")
        print(f"  - countdown now is at {sim.c}")
        output = sim.get_data({"Countdown": ["Warning", "ZeroReached"]})
        if output:
            event_time = output["time"]
            event = list(output["Countdown"].keys())[0]
            print(f"  - produced event {event} at time {event_time}")
        else:
            print("  - produced no event")

    test_step(0, None, 4)
    test_step(5, 3, 9)
    test_step(6, None, 9)
    test_step(7, 5, 9)
    test_step(10, None, 14)
    test_step(10, None, 14)


if __name__ == "__main__":
    test_script()
