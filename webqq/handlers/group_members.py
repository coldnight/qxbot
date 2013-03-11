#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:36:57
#   Desc    :   组成员
#
import time
import json
import socket
from .base import WebQQHandler
from ..webqqevents import RetryEvent, WebQQRosterUpdatedEvent, GroupMembersEvent

class GroupMembersHandler(WebQQHandler):
    def setup(self, gcode, done = False):
        self.done = done
        self.gcode = gcode
        self.method = "GET"

        if not self.req:
            url = "http://s.web2.qq.com/api/get_group_info_ext2"
            params = [("gcode", gcode),("vfwebqq", self.webqq.vfwebqq),
                    ("t", int(time.time()))]
            self.req = self.http_sock.make_request(url, params)
            self.req.add_header("Referer", "http://d.web2.qq.com/proxy."
                                    "html?v=20110331002&callback=1&id=3")
        try:
            self.sock, self.data = self.http_sock.make_http_sock_data(self.req)
        except:
            self.webqq.event(RetryEvent(GroupMembersHandler, self.req, self,
                                       self.gcode, self.done))
            self._writable = False
            self.sock = None
            self.data = None

    def handle_write(self):
        self._writable = False
        try:
            self.sock.sendall(self.data)
        except socket.error:
            self.webqq.event(RetryEvent(GroupMembersHandler, self.req,
                                        self, self.gcode, self.done))
        else:
            self._readable = True


    def handle_read(self):
        self._readable = False

        try:
            resp = self.http_sock.make_response(self.sock, self.req, self.method)
            self.sock.setblocking(4)   # 有chunked数据 阻塞一下
            tmp = resp.read()
            self.sock.setblocking(0)
            data = json.loads(tmp)
        except ValueError:
            self.webqq.event(RetryEvent(GroupMembersHandler, self.req,
                                        self, self.gcode, self.done))
        else:
            self.webqq.event(GroupMembersEvent(self, data, self.gcode))
            if self.done:
                self.webqq.event(WebQQRosterUpdatedEvent(self))
