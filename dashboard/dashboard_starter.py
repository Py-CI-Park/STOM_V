
import os
import subprocess
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from utility.static_method.static import qtest_qwait


# 마켓번호 -> 마켓코드 매핑
MARKET_CODE_MAP = {
    1: 'stock',
    2: 'stock_etf',
    3: 'stock_etn',
    4: 'stock_usa',
    5: 'coin',
    6: 'future',
    7: 'future_nt',
    8: 'future_os',
    9: 'coin_future'
}


class StreamReaderThread(QThread):
    """서브프로세스 출력을 스트리밍하는 QThread"""
    log_received = pyqtSignal(str)

    def __init__(self, pipe, prefix, is_stderr=False):
        super().__init__()
        self.pipe = pipe
        self.prefix = prefix
        self.is_stderr = is_stderr
        self._running = True
        error_keywords = ['error', 'Error', 'ERROR', 'exception', 'Exception', 'EXCEPTION', 'failed', 'Failed', 'FAILED']
        info_keywords = ['INFO', 'info']
        self.error_keywords = error_keywords
        self.info_keywords = info_keywords

    def run(self):
        """파이프에서 출력을 읽어 로그로 전송합니다."""
        for line in iter(self.pipe.readline, b''):
            text = line.decode('utf-8', errors='replace').strip()
            if text:
                if any(keyword in text for keyword in self.info_keywords):
                    continue
                is_error = self.is_stderr or any(keyword in text for keyword in self.error_keywords)
                if is_error:
                    self.log_received.emit(f"웹대시보드 {self.prefix} - {text}")


class DashboardStarter(QObject):
    log_received = pyqtSignal(str)

    def __init__(self, market_gubun=1, frontend_port=3000):
        super().__init__()
        self.market_gubun        = market_gubun
        self.market_code         = MARKET_CODE_MAP.get(market_gubun, 'stock')
        self.frontend_port       = frontend_port
        self.backend_port        = frontend_port + 5000
        self.backend_process     = None
        self.frontend_process    = None
        self.backend_err_thread  = None
        self.frontend_err_thread = None

    def _get_startupinfo(self):
        """Windows에서 콘솔 창을 숨기기 위한 startupinfo를 반환합니다."""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        return startupinfo

    def start(self):
        """백엔드와 프론트엔드 서버를 subprocess로 시작합니다."""
        # 환경변수 설정
        backend_env = os.environ.copy()
        backend_env['STOM_MARKET'] = str(self.market_gubun)
        backend_env['STOM_BACKEND_PORT'] = str(self.backend_port)
        backend_env['STOM_MARKET_CODE'] = self.market_code

        backend_dir = os.path.join("dashboard", "backend")
        self.backend_process = subprocess.Popen(
            ["python", "main.py"],
            cwd=backend_dir,
            env=backend_env,
            stderr=subprocess.PIPE,
            startupinfo=self._get_startupinfo(),
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        self.backend_err_thread = StreamReaderThread(self.backend_process.stderr, "백엔드", True)
        self.backend_err_thread.log_received.connect(self.log_received.emit)
        self.backend_err_thread.start()

        qtest_qwait(2)
        # 프론트엔드 환경변수 설정
        frontend_env = os.environ.copy()
        frontend_env['STOM_FRONTEND_PORT'] = str(self.frontend_port)
        frontend_env['STOM_MARKET_CODE'] = self.market_code

        frontend_dir = os.path.join("dashboard", "frontend")
        self.frontend_process = subprocess.Popen(
            ["node", "node_modules/vite/bin/vite.js", "--host", "0.0.0.0", "--port", str(self.frontend_port)],
            cwd=frontend_dir,
            env=frontend_env,
            stderr=subprocess.PIPE,
            startupinfo=self._get_startupinfo(),
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        self.frontend_err_thread = StreamReaderThread(self.frontend_process.stderr, "프론트엔드", True)
        self.frontend_err_thread.log_received.connect(self.log_received.emit)
        self.frontend_err_thread.start()

    def stop(self):
        """백엔드와 프론트엔드 서버를 종료합니다."""
        self.backend_process.kill()
        self.frontend_process.kill()
