import zmq
import time
import datetime
import numpy as np


class ZmqClient:
    def __init__(self):
        zctx = zmq.Context()
        self.sock = zctx.socket(zmq.REQ)
        self.sock.connect(f'tcp://localhost:5557')
        self.Start()

    def Start(self):
        while True:
            data = np.random.rand(2)
            self.sock.send_string('req1', zmq.SNDMORE)
            self.sock.send_pyobj(data)
            print('req1_send', data, datetime.datetime.now())
            msg = self.sock.recv_string()
            print('req1_recv', msg, datetime.datetime.now())
            time.sleep(1)


ZmqClient()
