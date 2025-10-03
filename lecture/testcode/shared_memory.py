import time
import numpy as np
from multiprocessing import Process, Queue, shared_memory


class Proc1:
    def __init__(self, q_):
        self.q = q_
        self.Start()

    def Start(self):
        while True:
            arry = np.random.rand(5, 10)
            shm = shared_memory.SharedMemory(create=True, size=arry.nbytes)
            a = np.ndarray(arry.shape, dtype=arry.dtype, buffer=shm.buf)
            a[:] = arry[:]
            print('Proc1')
            print(a)
            data = (shm.name, arry.shape, arry.dtype)
            self.q.put(data)
            time.sleep(2)


class Proc2:
    def __init__(self, q_):
        self.q = q_
        self.Start()

    def Start(self):
        while True:
            data = self.q.get()
            name, shape, dtype = data
            existing_shm = shared_memory.SharedMemory(name=name)
            arry = np.ndarray(shape, dtype=dtype, buffer=existing_shm.buf)
            print('Proc2')
            print(arry)


if __name__ == '__main__':
    q = Queue()
    Process(target=Proc1, args=(q,)).start()
    Process(target=Proc2, args=(q,)).start()
