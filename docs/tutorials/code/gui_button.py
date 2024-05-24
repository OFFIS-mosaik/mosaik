# gui_button.py

import sys
import zmq
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow


class PushButtonWindow(QMainWindow):
    def __init__(self):
        super(PushButtonWindow,self).__init__()
        self.button = None
        self.context = zmq.Context()

        # For external events
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind("tcp://*:5563")

    def button_clicked(self):
        self.publisher.send_multipart([b"B", b"Push button was clicked!"])

    def create(self):
        self.setWindowTitle("MOSAIK 3.0 - External Events")

        self.button = QtWidgets.QPushButton(self)
        self.button.setText("Click me to set an external event!")
        self.button.clicked.connect(self.button_clicked)

        # Set the central widget of the Window.
        self.setCentralWidget(self.button)


def main():
    app = QApplication(sys.argv)
    window = PushButtonWindow()
    window.create()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
