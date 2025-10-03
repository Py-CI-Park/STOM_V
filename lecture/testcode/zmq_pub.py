import zmq
import time
import datetime
import numpy as np


class ZmqServer:
    def __init__(self):
        zctx = zmq.Context()
        self.sock = zctx.socket(zmq.PUB)
        self.sock.bind('tcp://*:5556')
        self.Start()

    def Start(self):
        i = 0
        while True:
            i += 1
            time.sleep(1)
            data = np.random.rand(50)
            if i == 1:
                self.sock.send_string('tick', zmq.SNDMORE)
                self.sock.send_pyobj(data)
                print('tick', datetime.datetime.now())
            elif i == 2:
                self.sock.send_string('code', zmq.SNDMORE)
                self.sock.send_pyobj(data)
                print('code', datetime.datetime.now())
            else:
                i = 0
                self.sock.send_string('gsjm', zmq.SNDMORE)
                self.sock.send_pyobj(data)
                print('gsjm', datetime.datetime.now())


ZmqServer()
