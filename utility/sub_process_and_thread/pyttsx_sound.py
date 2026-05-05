
import pyttsx3
from PyQt5.QtCore import QThread


class PyttsxSound(QThread):
    def __init__(self, soundQ):
        super().__init__()
        self.soundQ = soundQ
        self.text2speak = pyttsx3.init()
        self.text2speak.setProperty('rate', 170)
        self.text2speak.setProperty('volume', 1.0)

    def run(self):
        while True:
            data = self.soundQ.get()
            self.text2speak.say(data)
            self.text2speak.runAndWait()