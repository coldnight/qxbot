#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/01 11:46:21
#   Desc    :   主程序
#
import Queue
from xmpp import XMPPBot
from webqq import WebQQ
from message_dispatch import MessageDispatch
from util import ThreadPool, get_logger

from settings import QQ, QQ_PWD, BRIDGES



class QxBot(object):
    def __init__(self):
        self.logger = get_logger()
        self.xmpp_msg_queue = Queue.Queue()
        self.qq_msg_queue = Queue.Queue()
        self.msg_dispatch = MessageDispatch(self, BRIDGES, self.xmpp_msg_queue,
                                                self.qq_msg_queue)
        self.webqq = WebQQ(QQ, self.msg_dispatch)
        self.xmpp = XMPPBot(self.msg_dispatch)
        self.thread_pool = ThreadPool(3)
        self.thread_pool.start()

    def get_group_name(self, gcode):
        """ 根据gcode获取群名 """
        return self.webqq.group_map.get(gcode, {}).get("name")

    def get_group_member_nick(self, gcode, uin):
        return self.webqq.group_m_map.get(gcode, {}).get(uin, {}).get("nick")

    def run(self):
        self.thread_pool.add_job(self.webqq.login, QQ_PWD)
        self.thread_pool.add_job(self.handle_qq)
        self.thread_pool.add_job(self.handle_xmpp)
        self.xmpp.run()

    def handle_xmpp(self):
        while True:
            msg = self.xmpp_msg_queue.get()
            self.logger.info("Send QQ Message %s to XMPP Account %s",
                             msg.get("body"), msg.get("to"))
            self.xmpp.send_msg(**msg)

    def handle_qq(self):
        while True:
            msg = self.qq_msg_queue.get()
            body = msg.get("body")
            if body:
                self.logger.info("Send XMPP Message %s to QQ Account %s",
                                 body, msg.get("to"))
                self.webqq.send_group_msg(msg.get("to"), body)


if __name__ == "__main__":
    qx = QxBot()
    qx.run()
