#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/01 11:44:05
#   Desc    :   消息调度
#
import random
import tempfile
from lib.utils import get_logger, upload_file

class MessageDispatch(object):
    """ 消息调度器 """
    def __init__(self, qxbot, webqq, bridges):
        self.logger = get_logger()
        self.qxbot = qxbot
        self.webqq = webqq
        self.uin_qid_map = {}
        self.qid_uin_map = {}
        self.bridges = bridges
        self._maped = False

    def get_map(self):
        uins = [key for key, value in self.webqq.group_map.items()]
        for uin in uins:
            qid = self.get_qid_with_uin(uin)
            self.uin_qid_map[uin] = qid
            self.qid_uin_map[qid] = uin
        self._maped = True

    def get_xmpp_account(self, uin):
        """ 根据uin获取桥接的XMPP帐号 """
        qid = self.get_qid_with_uin(uin)
        xmpps = []
        for q, xmpp in self.bridges:
            if q == qid:
                xmpps.append(xmpp)

        return xmpps

    def get_uin_account(self, xmpp):
        """ 根据xmpp帐号获取桥接的qq号的uin """
        qids = []
        for qid, x in self.bridges:
            if x == xmpp:
                qids.append(self.qid_uin_map.get(qid))

        return qids

    def get_qid_with_uin(self, uin):
        qid = self.uin_qid_map.get(uin)
        if not qid:
            qid = self.webqq.get_qid_with_uin(uin)
            self.uin_qid_map[uin] = qid
        return qid

    def get_group_msg_img(self, uin, info):
        res = self.webqq.get_group_msg_img(uin, info)
        path = tempfile.mktemp()
        fp = open(path, 'wb')
        fp.write(res.read())
        fp.close()
        filename = info.get("name")
        name, typ = filename.split(".")
        name = random.sample(name, 3)
        filename = "{0}.{1}".format("".join(name), typ)
        res = upload_file(filename, path)
        return res.geturl()

    def get_xmpp_face(self, qface_id):
        for q, x in face_map:
            if q == qface_id:
                return x
        return False

    def handle_qq_group_contents(self, gcode, uin, contents):
        result = []
        content = ""
        face = False
        for row in contents:
            if isinstance(row, (str, unicode)):
                content += row.replace(u"【提示：此用户正在使用Q+"
                                       u" Web：http://web.qq.com/】", "")
            else:
                if len(row) == 2:
                    key, value = row
                    if key == "face":
                        f = self.get_xmpp_face(value)
                        if f: content += f
                        else: face = True
                    if key == "cface":
                        url  = self.get_group_msg_img(uin, value)
                        result.append(url)

        gender = self.webqq.group_m_map.get(gcode, {}).get(uin, {}).get("gender")
        gender_desc_map = {"male":u"他", None:u"它", "female":u"她"}
        if not result and not content.strip() and face:
            return u"({0}只是做了一个奇怪的表情, 并没有说什么)"\
                    .format(gender_desc_map.get(gender, u"它"))
        else:
            body = "\n".join(result) + " " + content.strip()
            if face:
                body += u" ({0}还做了个奇怪的表情)"\
                        .format(gender_desc_map.get(gender, u"它"))
            body = body.replace("\r", "\n")
            return body

    def handle_qq_group_msg(self, message):
        """ 处理组消息 """
        value = message.get("value", {})
        gcode = value.get("group_code")
        uin = value.get("send_uin")
        contents = value.get("content", [])
        content = self.handle_qq_group_contents(gcode, uin, contents)
        gname = self.webqq.get_group_name(gcode)
        uname = self.webqq.get_group_member_nick(gcode, uin)
        body = u"<{1}> {2}".format(gname, uname, content)
        tos = self.get_xmpp_account(gcode)
        [self.qxbot.send_msg(to, body) for to in tos]

    def dispatch_qq(self, qq_source):
        if qq_source.get("retcode") == 0:
            messages = qq_source.get("result")
            for m in messages:
                if m.get("poll_type") == "group_message":
                    self.handle_qq_group_msg(m)

    def dispatch_xmpp(self, stanza):
        body = stanza.body
        body = body.replace("\n", "\r")
        body = body.replace("\r\r", "\r")
        frm = stanza.from_jid.bare().as_string()
        tos = self.get_uin_account(frm)
        [self.webqq.send_qq_group_msg(to, body) for to in tos]

face_map = [
    (14, ":)"),
    (1, ":-("),
    (107, ":-("),
    (106, ":-("),
    (2, ":kiss:"),
    (3, ":|"),
    (4, "8-)"),
    (5, ":'-("),
    (6, "\m/"),
    (7, ":-X"),
    (8, ":)zZ"),
    (9, ":'-("),
    (10, ";-)"),
    (11, ">:-("),
    (12, ":P"),
    (13, ":-D"),
    (0, "=-O"),
    (50, ":-("),
    (51, "8-)"),
    (96, "=-O"),
    (97, "=-O"),
    (74, ":-["),
    (111, ":-["),
    (46, ":yes:"),
    (47, ":no:"),
    (105, ":no:"),
    (83, "O:-)"),
    (80, ">:o"),
    (33, "@->--"),
    (34, "@->--"),
    (36, ":heart:"),
    (37, ":brokenheart:"),
    (109, ":kiss:"),
    (588, ":kiss:"),
]
