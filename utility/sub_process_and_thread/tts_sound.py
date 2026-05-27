
import pythoncom
from PyQt5.QtCore import QThread


class TtsSound(QThread):
    """Windows SAPI를 사용하여 소리를 재생합니다."""
    def __init__(self, soundQ):
        super().__init__()
        self.soundQ = soundQ
        self._tts = None

    def run(self):
        pythoncom.CoInitialize()
        self._tts = self._init_sapi()
        if self._tts is None:
            pythoncom.CoUninitialize()
            return

        while True:
            try:
                data = self.soundQ.get()
                self._tts.Speak(data)
            except Exception:
                pass

    def _init_sapi(self):
        """SAPI COM 객체를 초기화합니다."""
        try:
            import win32com.client
            return win32com.client.Dispatch("SAPI.SpVoice")
        except Exception:
            return None
