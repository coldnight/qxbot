#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/01 11:28:40
#   Desc    :   cold

from pyxmpp2.jid import JID
from pyxmpp2.client import Client
from pyxmpp2.message import Message
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.streamevents import DisconnectedEvent,ConnectedEvent
from pyxmpp2.interfaces import XMPPFeatureHandler
from pyxmpp2.interfaces import presence_stanza_handler, message_stanza_handler
from pyxmpp2.ext.version import VersionProvider

from util import get_logger, EpollMainLoop

from settings import XMPP_ACCOUNT, XMPP_PASSWD, QQ, QQ_PWD, BRIDGES

from webqq import (CheckHandler, WebQQ, BeforeLoginHandler, CheckedEvent,
                   WebQQLoginedEvent, BeforeLoginEvent, LoginHandler,
                   HeartbeatHandler, PollHandler, WebQQHeartbeatEvent,
                   WebQQMessageEvent, WebQQPollEvent)

from message_dispatch import MessageDispatch

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
        self.webqq = WebQQ(QQ, event_queue)
        self.connected = False
        #self.mainloop = TornadoMainLoop(settings)
        self.mainloop = EpollMainLoop(settings)
        self.client = Client(my_jid, [self, version_provider],
                             settings, self.mainloop)
        self.logger = get_logger()
        self.msg_dispatch = MessageDispatch(self, self.webqq, BRIDGES)

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
        self.msg_dispatch.dispatch_xmpp(stanza)

    @event_handler(DisconnectedEvent)
    def handle_disconnected(self, event):
        return QUIT

    @event_handler(ConnectedEvent)
    def handle_connected(self, event):
        checkhandler = CheckHandler(self.webqq)
        self.mainloop.add_handler(checkhandler)
        self.connected = True

    @event_handler(CheckedEvent)
    def handle_webqq_checked(self, event):
        bloginhandler = BeforeLoginHandler(self.webqq, QQ_PWD)
        self.mainloop.remove_handler(event.handler)
        self.mainloop.add_handler(bloginhandler)

    @event_handler(BeforeLoginEvent)
    def handle_webqq_blogin(self, event):
        loginhandler = LoginHandler(self.webqq)
        self.mainloop.remove_handler(event.handler)
        self.mainloop.add_handler(loginhandler)

    @event_handler(WebQQLoginedEvent)
    def handle_webqq_logined(self, event):
        self.mainloop.remove_handler(event.handler)
        hb = HeartbeatHandler(self.webqq)
        self.mainloop.add_handler(hb)
        self.mainloop.add_handler(PollHandler(self.webqq))
        self.webqq.get_group_members()

    @event_handler(WebQQHeartbeatEvent)
    def handle_webqq_hb(self, event):
        self.mainloop.remove_handler(event.handler)
        self.mainloop.add_handler(HeartbeatHandler(self.webqq, 60))

    @event_handler(WebQQPollEvent)
    def handle_webqq_poll(self, event):
        self.mainloop.remove_handler(event.handler)
        self.mainloop.add_handler(PollHandler(self.webqq, 3))

    @event_handler(WebQQMessageEvent)
    def handle_webqq_msg(self, event):
        self.msg_dispatch.dispatch_qq(event.message)

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
            typ = 'normal'
        m = Message(from_jid = self.my_jid, to_jid = to, stanza_type = typ,
                    body = body)
        return m

    def send_msg(self, to, body):
        if not isinstance(to, JID):
            to = JID(to)
        msg = self.make_message(to, 'normal', body)
        self.stream.send(msg)

if __name__ == "__main__":
        xmpp = QXBot()
        xmpp.run()
