#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:31:30
#   Desc    :   组消息
#
import json
import socket
from .base import WebQQHandler
from ..webqqevents import RetryEvent, RemoveEvent

class GroupMsgHandler(WebQQHandler):
    def setup(self, group_uin = None, content = None):
        self.group_uin = group_uin
        self.content = content
        self.method = "POST"
        if not self.req:
            assert group_uin
            assert content
            gid = self.webqq.group_map.get(group_uin).get("gid")
            content = [content, ["font",
                    {"name":"宋体", "size":10, "style":[0,0,0],
                        "color":"000000"}]]
            r = {"group_uin": gid, "content": json.dumps(content),
                "msg_id": self.webqq.msg_id, "clientid": self.webqq.clientid,
                "psessionid": self.webqq.psessionid}
            self.webqq.msg_id += 1
            url = "http://d.web2.qq.com/channel/send_qun_msg2"
            params = [("r", json.dumps(r)), ("sessionid", self.webqq.psessionid),
                    ("clientid", self.webqq.clientid)]
            url = "http://d.web2.qq.com/channel/send_qun_msg2"
            self.req = self.http_sock.make_request(url, params, self.method)
            self.req.add_header("Referer", "http://d.web2.qq.com/proxy.html")

        try:
            self.sock, self.data = self.http_sock.make_http_sock_data(self.req)
        except socket.error:
            self.webqq.event(RetryEvent(GroupMsgHandler, self.req, self,
                                       self.group_uin, self.content))
            self._writable = False
            self.sock = None
            self.data = None

    def handle_write(self):
        self._writable = False
        if self.content != self.webqq.last_msg.get(self.group_uin)  :
            self.webqq.last_msg[self.group_uin] = self.content
            try:
                self.sock.sendall(self.data)
            except socket.error:
                self.webqq.event(RetryEvent(GroupMsgHandler, self.req, self,
                                           self.group_uin, self.content))
            else:
                self.webqq.event(RemoveEvent(self))
