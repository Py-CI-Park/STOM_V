
import sys
from threading import Thread, Event


class QueueDrainer(Thread):
    """windowQ 메시지를 stderr로 출력하는 headless consumer.

    GUI의 windowQ consumer (ui_update_textedit.py)를 대체.
    상태 메시지는 stderr로 출력하여 stdout의 JSON 결과와 분리.
    """

    def __init__(self, queue, verbose=True):
        super().__init__(daemon=True)
        self.queue = queue
        self.verbose = verbose
        self.stop_event = Event()
        self.last_message = None

    def run(self):
        while not self.stop_event.is_set():
            try:
                data = self.queue.get(timeout=0.5)
            except Exception:
                continue

            if data is None:
                break

            if isinstance(data, tuple) and len(data) >= 2:
                ui_id, message = data[0], data[1]
                self.last_message = message
                if self.verbose:
                    print(f'[STOM] {message}', file=sys.stderr)
            elif isinstance(data, str):
                self.last_message = data
                if self.verbose:
                    print(f'[STOM] {data}', file=sys.stderr)

    def stop(self):
        self.stop_event.set()
