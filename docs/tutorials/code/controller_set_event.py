# controller_set_event.py

import sys
import zmq
import threading
import math

import mosaik_api_v3


META = {
    'type': 'event-based',
    'set_events': True,
    'models': {
        'Controller': {
            'public': True,
            'params': [],
            'attrs': [],
        },
    },
}


def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread
    return wrapper


class Controller(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(META)
        self.data = {}
        self.time = 0
        self.eid = None
        self.thread = None
        self.initial_timestamp = 0
        self.once = True
        self.context = zmq.Context()

        # Subscribe to external events from the GUI
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect("tcp://localhost:5563")
        self.subscriber.setsockopt(zmq.SUBSCRIBE, b"B")

        # Listener THREAD
        self.thread = listen_to_external_events(self)

    def create(self, num, model):
        if num > 1 or self.eid is not None:
            raise RuntimeError('Can only create one instance of Controller.')

        self.eid = 'Controller_set_event'
        return [{'eid': self.eid, 'type': model}]

    def finalize(self):
        self.thread.join(0)
        sys.exit()

    def step(self, time, inputs, max_advance):
        # Needed in listener thread to determine the current simulation time in wall clock time.
        if self.once:
            self.initial_timestamp = self.mosaik.world.env.now
            self.once = False

        self.time = time
        print(f"In step at time {self.time}")
        print(f"max_advance {max_advance}")

        return None
        

@threaded
def listen_to_external_events(controller):
    while True:
        try:
            # Receive external event message from GUI
            [address, contents] = controller.subscriber.recv_multipart(zmq.NOBLOCK)
            print(f"[{address}] {contents}")

            current_timestamp = controller.mosaik.world.env.now
            real_time = math.ceil(current_timestamp - controller.initial_timestamp)
            event_time = real_time + 1
            print(f"Current simulation time: {real_time}")

            if controller.time < event_time < controller.mosaik.world.until:
                print(f"Set external Event at time {event_time}")
                # Set external event in mosaik via asynchronous call
                controller.mosaik.set_event(event_time)

        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                # state changed since poll event
                pass
            else:
                raise


def main():
    return mosaik_api_v3.start_simulation(Controller())


if __name__ == "__main__":
    main()
