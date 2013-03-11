#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:04:50
#   Desc    :   WebQQ Base Handler
#
import threading
from ..http_socket import HTTPSock
from pyxmpp2.mainloop.interfaces import IOHandler, HandlerReady


class WebQQHandler(IOHandler):
    http_sock = HTTPSock()
    def __init__(self, webqq, req = None, *args, **kwargs):
        self.req = req
        self._readable = False
        self._writable = True
        self.webqq = webqq
        self.lock = threading.RLock()
        self._cond = threading.Condition(self.lock)
        self.setup(*args, **kwargs)

    def fileno(self):
        with self.lock:
            if self.sock is not None:
                return self.sock.fileno()

        return None

    def is_readable(self):
        return self.sock is not None and self._readable

    def wait_for_readability(self):
        with self.lock:
            while True:
                if self.sock is None or not self._readable:
                    return False
                else:
                    return True
            self._cond.wait()


    def is_writable(self):
        with self.lock:
            return self.sock and self.data and self._writable

    def wait_for_writability(self):
        with self.lock:
            while True:
                if self.sock and self.data and self._writable:
                    return True
                else:
                    return False
            self._cond.wait()

    def prepare(self):
        return HandlerReady()

    def handle_read(self):
        pass

    def handle_hup(self):
        with self.lock:
            pass

    def handle_write(self):
        pass

    def handle_err(self):
        with self.lock:
            self.sock.close()

    def handle_nval(self):
        if self.sock is None:
            return

    def close(self):
        self.sock.close()
