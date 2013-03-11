#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/01 11:28:40
#   Desc    :   cold
import Queue

from pyxmpp2.jid import JID
from pyxmpp2.client import Client
from pyxmpp2.message import Message
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.streamevents import DisconnectedEvent,ConnectedEvent
from pyxmpp2.interfaces import XMPPFeatureHandler
from pyxmpp2.interfaces import presence_stanza_handler, message_stanza_handler
from pyxmpp2.ext.version import VersionProvider
from pyxmpp2.roster import RosterReceivedEvent

from webqq import WebQQ
from lib.utils import get_logger
from lib.libepoll import EpollMainLoop
from message_dispatch import MessageDispatch
from settings import XMPP_ACCOUNT, XMPP_PASSWD, QQ, BRIDGES, QQ_PWD

__version__ = '0.0.1 alpha'

USER = XMPP_ACCOUNT
PASSWORD = XMPP_PASSWD

class QXBot(EventHandler, XMPPFeatureHandler):
    def __init__(self):
        my_jid = JID(USER+'/Bot')
        self.my_jid = my_jid
        settings = XMPPSettings({
                            "software_name": "qxbot",
                            "software_version": __version__,
                            "software_os": "Linux",
                            "tls_verify_peer": False,
                            "starttls": True,
                            "ipv6":False,
                            "poll_interval": 10,
                            })

        settings["password"] = PASSWORD
        version_provider = VersionProvider(settings)
        event_queue = settings["event_queue"]
        self.connected = False
        #self.mainloop = TornadoMainLoop(settings)
        self.mainloop = EpollMainLoop(settings)
        self.client = Client(my_jid, [self, version_provider],
                             settings, self.mainloop)
        self.logger = get_logger()
        self.webqq = WebQQ(QQ, QQ_PWD, event_queue, self)
        self.msg_dispatch = MessageDispatch(self, self.webqq, BRIDGES)
        self.xmpp_msg_queue = Queue.Queue()

    def run(self, timeout = None):
        self.client.connect()
        self.client.run(timeout)

    def disconnect(self):
        self.client.disconnect()
        while True:
            try:
                self.run(2)
            except:
                pass
            else:
                break

    @presence_stanza_handler("subscribe")
    def handle_presence_subscribe(self, stanza):
        self.logger.info(u"{0} join us".format(stanza.from_jid))
        return stanza.make_accept_response()

    @presence_stanza_handler("subscribed")
    def handle_presence_subscribed(self, stanza):
        self.logger.info(u"{0!r} accepted our subscription request"
                                                    .format(stanza.from_jid))
        return stanza.make_accept_response()

    @presence_stanza_handler("unsubscribe")
    def handle_presence_unsubscribe(self, stanza):
        self.logger.info(u"{0} canceled presence subscription"
                                                    .format(stanza.from_jid))
        return stanza.make_accept_response()

    @presence_stanza_handler("unsubscribed")
    def handle_presence_unsubscribed(self, stanza):
        self.logger.info(u"{0!r} acknowledged our subscrption cancelation"
                                                    .format(stanza.from_jid))

    @presence_stanza_handler(None)
    def handle_presence_available(self, stanza):
        self.logger.info(r"{0} has been online".format(stanza.from_jid))

    @presence_stanza_handler("unavailable")
    def handle_presence_unavailable(self, stanza):
        self.logger.info(r"{0} has been offline".format(stanza.from_jid))

    @message_stanza_handler()
    def handle_message(self, stanza):
        if self.webqq.connected:
            self.msg_dispatch.dispatch_xmpp(stanza)
        else:
            self.xmpp_msg_queue.put(stanza)

    @event_handler(DisconnectedEvent)
    def handle_disconnected(self, event):
        return QUIT

    @event_handler(ConnectedEvent)
    def handle_connected(self, event):
        pass

    @event_handler(RosterReceivedEvent)
    def handle_roster_received(self, event):
        """ 此处代表xmpp已经连接
        开始连接QQ, 先将检查是否需要验证码的handler加入到mainloop
        """
        self.webqq.run()
        self.connected = True

    @property
    def roster(self):
        return self.client.roster

    @property
    def stream(self):
        return self.client.stream

    @event_handler()
    def handle_all(self, event):
        self.logger.info(u"-- {0}".format(event))

    def make_message(self, to, typ, body):
        """ 构造消息
            `to` - 接收人 JID
            `typ` - 消息类型
            `body` - 消息主体
        """
        if typ not in ['normal', 'chat', 'groupchat', 'headline']:
            typ = 'chat'
        m = Message(from_jid = self.my_jid, to_jid = to, stanza_type = typ,
                    body = body)
        return m

    def send_msg(self, to, body):
        if not isinstance(to, JID):
            to = JID(to)
        msg = self.make_message(to, 'chat', body)
        self.stream.send(msg)


def main():
        xmpp = QXBot()
        xmpp.run()

if __name__ == "__main__":
    main()
