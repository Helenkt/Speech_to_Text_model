"""Nonblocking process lock. All workers must share the same local work_dir."""
import errno
import os


class BusyError(RuntimeError):
    pass


class WorkerLock:
    def __init__(self,path):
        self.path=path
        self.stream=None

    def __enter__(self):
        self.stream=open(self.path,'a+b')
        try:
            self.stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as error:
            self.stream.close(); self.stream=None
            if error.errno in {errno.EACCES,errno.EAGAIN,errno.EDEADLK} or getattr(error,'winerror',None) in {33,36}:
                raise BusyError('Another SDK worker is using this work_dir') from error
            raise
        return self

    def __exit__(self,*args):
        try:
            self.stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_UN)
        finally:
            self.stream.close()
