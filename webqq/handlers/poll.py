#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:28:36
#   Desc    :   获取消息
#
import json
import socket
import httplib
from .base import WebQQHandler
from ..webqqevents import RetryEvent, WebQQPollEvent, WebQQMessageEvent
from ..webqqevents import ReconnectEvent

class PollHandler(WebQQHandler ):
    """ 获取消息 """
    def setup(self):
        self.method = "POST"
        if not self.req:
            url = "http://d.web2.qq.com/channel/poll2"
            params = [("r", '{"clientid":"%s", "psessionid":"%s",'
                    '"key":0, "ids":[]}' % (self.webqq.clientid,
                                            self.webqq.psessionid)),
                    ("clientid", self.webqq.clientid),
                    ("psessionid", self.webqq.psessionid)]
            self.req = self.http_sock.make_request(url, params, self.method)
            self.req.add_header("Referer", "http://d.web2.qq.com/proxy.html?v="
                                "20110331002&callback=1&id=2")
        try:
            self.sock, self.data = self.http_sock.make_http_sock_data(self.req)
        except socket.error:
            self.webqq.event(RetryEvent(PollHandler, self.req, self))
            self._writable = False
            self.sock = None
            self.data = None


    def handle_write(self):
        self._writable = False
        try:
            self.sock.sendall(self.data)
        except socket.error:
            self.webqq.event(RetryEvent(PollHandler, self.req, self))
        else:
            self._readable = True

    def handle_read(self):
        try:
            resp = self.http_sock.make_response(self.sock, self.req, self.method)
            tmp = resp.read()
            data = json.loads(tmp)
            if data:
                self._readable = False
                #if data.get("retcode") == 121:
                #    self.webqq.event(ReconnectEvent(self))
                self.webqq.event(WebQQPollEvent(self))
                self.webqq.event(WebQQMessageEvent(data, self))
        except ValueError:
            pass
        except socket.error:
            self.webqq.event(WebQQPollEvent(self))
        except httplib.BadStatusLine:
            pass

    def is_writable(self):
        with self.lock:
            return self.sock and self.data and self._writable

