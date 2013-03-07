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

from utils import get_logger, EpollMainLoop

from settings import XMPP_ACCOUNT, XMPP_PASSWD, QQ, QQ_PWD, BRIDGES

from webqq import (CheckHandler, WebQQ, BeforeLoginHandler, CheckedEvent,
                   WebQQLoginedEvent, BeforeLoginEvent, LoginHandler,
                   HeartbeatHandler, PollHandler, WebQQHeartbeatEvent,
                   WebQQMessageEvent, WebQQPollEvent, RetryEvent,
                   RemoveEvent, GroupMsgHandler, GroupListHandler,
                   GroupListEvent, WebQQRosterUpdatedEvent,
                   GroupMembersHandler, GroupMembersEvent)

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
        checkhandler = CheckHandler(self.webqq)
        self.mainloop.add_handler(checkhandler)
        self.connected = True

    @event_handler(CheckedEvent)
    def handle_webqq_checked(self, event):
        bloginhandler = BeforeLoginHandler(self.webqq, password = QQ_PWD)
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
        self.mainloop.add_handler(GroupListHandler(self.webqq))

    @event_handler(GroupListEvent)
    def handle_webqq_group_list(self, event):
        self.mainloop.remove_handler(event.handler)
        data = event.data
        group_map = {}
        if data.get("retcode") == 0:
            group_list = data.get("result", {}).get("gnamelist", [])
            for group in group_list:
                gcode = group.get("code")
                group_map[gcode] = group

        self.webqq.group_map = group_map
        i = 1
        for gcode in group_map:
            if i == len(group_map):
                self.mainloop.add_handler(
                    GroupMembersHandler(self.webqq, gcode = gcode, done = True))
            else:
                self.mainloop.add_handler(
                    GroupMembersHandler(self.webqq, gcode = gcode, done = False))

            i += 1

    @event_handler(GroupMembersEvent)
    def handle_group_members(self, event):
        self.mainloop.remove_handler(event.handler)
        members = event.data.get("result", {}).get("minfo", [])
        self.webqq.group_m_map[event.gcode] = {}
        for m in members:
            uin = m.get("uin")
            self.webqq.group_m_map[event.gcode][uin] = m
        cards = event.data.get("result", {}).get("cards", [])
        for card in cards:
            uin = card.get("muin")
            group_name = card.get("card")
            self.webqq.group_m_map[event.gcode][uin]["nick"] = group_name

        self.mainloop.add_handler(GroupListHandler(self.webqq, delay = 120))

    @event_handler(WebQQRosterUpdatedEvent)
    def handle_webqq_roster(self, event):
        self.mainloop.remove_handler(event.handler)
        self.msg_dispatch.get_map()
        if not self.webqq.polled:
            self.webqq.polled = True
            self.mainloop.add_handler(PollHandler(self.webqq))
        if not self.webqq.heartbeated:
            self.webqq.heartbeated = True
            hb = HeartbeatHandler(self.webqq)
            self.mainloop.add_handler(hb)
        while True:
            try:
                stanza = self.xmpp_msg_queue.get_nowait()
                self.msg_dispatch.dispatch_xmpp(stanza)
            except Queue.Empty:
                break
        self.webqq.connected = True

    @event_handler(WebQQHeartbeatEvent)
    def handle_webqq_hb(self, event):
        self.mainloop.remove_handler(event.handler)
        self.mainloop.add_handler(HeartbeatHandler(self.webqq, delay = 60))

    @event_handler(WebQQPollEvent)
    def handle_webqq_poll(self, event):
        self.mainloop.remove_handler(event.handler)
        self.mainloop.add_handler(PollHandler(self.webqq, delay = 3))

    @event_handler(WebQQMessageEvent)
    def handle_webqq_msg(self, event):
        self.msg_dispatch.dispatch_qq(event.message)

    @event_handler(RetryEvent)
    def handle_retry(self, event):
        self.mainloop.remove_handler(event.handler)
        handler = event.cls(self.webqq, event.req, *event.args, **event.kwargs)
        self.mainloop.add_handler(handler)

    @event_handler(RemoveEvent)
    def handle_remove(self, event):
        self.mainloop.remove_handler(event.handler)

    def send_qq_group_msg(self, group_uin, content):
        handler = GroupMsgHandler(self.webqq, group_uin = group_uin,
                                  content = content)
        self.mainloop.add_handler(handler)

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

if __name__ == "__main__":
        xmpp = QXBot()
        xmpp.run()
