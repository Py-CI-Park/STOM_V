import zmq
import datetime


class ZmqClient:
    def __init__(self):
        zctx = zmq.Context()
        self.sock = zctx.socket(zmq.SUB)
        self.sock.connect(f'tcp://localhost:5556')
        self.sock.setsockopt_string(zmq.SUBSCRIBE, '')
        self.Start()

    def Start(self):
        while True:
            msg  = self.sock.recv_string()
            data = self.sock.recv_pyobj()
            print('C3', msg, data, datetime.datetime.now())


ZmqClient()
