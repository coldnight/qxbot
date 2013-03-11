#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:34:11
#   Desc    :   组列表
#
import json
import socket
from .base import WebQQHandler
from ..webqqevents import RetryEvent, GroupListEvent

class GroupListHandler(WebQQHandler):
    def setup(self, delay = 0):
        self.delay = delay
        self.method = "POST"
        if not self.req:
            url = "http://s.web2.qq.com/api/get_group_name_list_mask2"
            params = [("r", '{"vfwebqq":"%s"}' % self.webqq.vfwebqq),]
            self.req = self.http_sock.make_request(url, params, self.method)
            self.req.add_header("Origin", "http://s.web2.qq.com")
            self.req.add_header("Referer", "http://s.web2.qq.com/proxy.ht"
                                    "ml?v=20110412001&callback=1&id=1")
        try:
            self.sock, self.data = self.http_sock.make_http_sock_data(self.req)
        except socket.error:
            self.webqq.event(RetryEvent(GroupListHandler, self.req, self))
            self.sock = None
            self.data = None
            self._writable = False

    def handle_write(self):
        self._writable = False
        try:
            self.sock.sendall(self.data)
        except socket.error:
            self.webqq.event(RetryEvent(GroupListHandler, self.req, self))
        else:
            self._readable = True

    def handle_read(self):
        self._readable = False

        try:
            resp = self.http_sock.make_response(self.sock, self.req, self.method)
            tmp = resp.read()
            data = json.loads(tmp)
            self.webqq.event(GroupListEvent(self, data), self.delay)
        except ValueError:
            pass
