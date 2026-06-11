
import os
import winsound
import tempfile
from supertonic import TTS
from PyQt5.QtCore import QThread


class SupertonicTTS(QThread):
    """supertonic TTS를 사용하여 소리를 재생합니다."""
    def __init__(self, soundQ, voice_name='F1'):
        super().__init__()
        self.soundQ = soundQ
        self.tts = TTS(auto_download=True)
        self.style = self.tts.get_voice_style(voice_name=voice_name)

    def run(self):
        """soundQ큐를 감시합니다.
        텍스트: 소리재생, 딕셔너리: 보이스네임 설정 변경"""
        while True:
            data = self.soundQ.get()
            if data.__class__ == str:
                if data in ('F1', 'F2', 'F3', 'F4', 'F5', 'M1', 'M2', 'M3', 'M4', 'M5'):
                    text = 'supertonic TTS의 목소리 테스트 중입니다.'
                    style = self.tts.get_voice_style(voice_name=data)
                    wav, _ = self.tts.synthesize(text, voice_style=style, total_steps=5, lang="ko")
                else:
                    wav, _ = self.tts.synthesize(data, voice_style=self.style, total_steps=5, lang="ko")
                self._play_sound(wav)
            elif data.__class__ == dict:
                voice_name = data['보이스네임']
                self.style = self.tts.get_voice_style(voice_name=voice_name)

    def _play_sound(self, wav):
        """wav를 임시파일로 저장하고 winsound로 재생합니다."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_filename = temp_file.name
        self.tts.save_audio(wav, temp_filename)
        try:
            winsound.PlaySound(temp_filename, winsound.SND_FILENAME)
        finally:
            os.unlink(temp_filename)
