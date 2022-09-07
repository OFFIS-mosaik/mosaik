import tkinter as tk
import zmq


class Tkinter():
    def __init__(self):
        self.button = None
        self.window = tk.Tk()
        self.context = zmq.Context()

        # For external events
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind("tcp://*:5563")

    def print_stuff(self):
        self.publisher.send_multipart([b"B", b"Push button was clicked!"])

    def create(self):
        # Open window having dimension 100x100
        self.window.geometry('150x100')
        self.window.title('External Events')

        self.button = tk.Button(self.window, text="Set External Event", command=self.print_stuff)
        self.button.pack(side=tk.LEFT)

    def show(self):
        print('Show Tkinter window')
        self.window.mainloop()


def main():
    sim = Tkinter()
    sim.create()
    sim.show()


if __name__ == "__main__":
    main()