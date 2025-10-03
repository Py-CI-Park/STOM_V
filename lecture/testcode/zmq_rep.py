import zmq
import datetime


class ZmqServer:
    def __init__(self):
        zctx = zmq.Context()
        self.sock = zctx.socket(zmq.REP)
        self.sock.bind('tcp://*:5557')
        self.Start()

    def Start(self):
        while True:
            msg = self.sock.recv_string()
            data = self.sock.recv_pyobj()
            print('rep_recv', msg, data, datetime.datetime.now())
            self.sock.send_string('서버에서 보낸 시리얼키 확인 및 기한')
            print('rep_send', datetime.datetime.now())


ZmqServer()
