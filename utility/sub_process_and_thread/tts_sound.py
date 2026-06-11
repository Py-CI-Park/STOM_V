
import pythoncom
import win32com.client
from PyQt5.QtCore import QThread


class TextToSpeak(QThread):
    """TTS를 사용하여 소리를 재생합니다."""
    def __init__(self, soundQ, dict_set):
        super().__init__()
        self.soundQ = soundQ
        self.dict_set = dict_set
        self.tts = None
        self._init_tts()

    def _init_tts(self):
        try:
            self.tts = win32com.client.Dispatch("SAPI.SpVoice")
            self.tts.Rate = self.dict_set['읽기속도']
        except Exception:
            self.tts = None

    def run(self):
        """soundQ큐를 감시합니다"""
        pythoncom.CoInitialize()
        if self.tts is None:
            pythoncom.CoUninitialize()
            return

        while True:
            try:
                data = self.soundQ.get()
                if data.__class__ == str:
                    self.tts.Speak(data)
                elif data.__class__ == int:
                    tts = win32com.client.Dispatch("SAPI.SpVoice")
                    tts.Rate = data
                    tts.Speak(f'현재 TTS의 읽기속도는 {data}입니다.')
                elif data.__class__ == dict:
                    self.dict_set = data
                    self._init_tts()
            except Exception:
                pass
