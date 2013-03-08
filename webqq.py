#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/02/28 11:23:49
#   Desc    :   Web QQ API
#
import time
import json
import socket
import random
import httplib
import tempfile
import threading
from hashlib import md5
from functools import partial

from pyxmpp2.mainloop.interfaces import IOHandler, HandlerReady, Event

from utils import HttpHelper, get_logger, upload_file
from http_socket import HTTPSock


http_sock = HTTPSock()

class WebQQEvent(Event):
    webqq = None
    handler = None

class CheckedEvent(WebQQEvent):
    def __init__(self, check_data, handler):
        self.check_data = check_data
        self.handler = handler

    def __unicode__(self):
        return u"WebQQ Checked: {0}".format(self.check_data)


class BeforeLoginEvent(WebQQEvent):
    def __init__(self, back_data, handler):
        self.back_data = back_data
        self.handler = handler

    def __unicode__(self):
        return u"WebQQ Before Login: {0}".format(self.back_data)


class WebQQLoginedEvent(WebQQEvent):
    def __init__(self, handler):
        self.handler = handler

    def __unicode__(self):
        return u"WebQQ Logined"


class WebQQHeartbeatEvent(WebQQEvent):
    def __init__(self, handler):
        self.handler = handler

    def __unicode__(self):
        return u"WebQQ Heartbeat"


class WebQQPollEvent(WebQQEvent):
    def __init__(self, handler):
        self.handler = handler

    def __unicode__(self):
        return "WebQQ Poll"


class WebQQMessageEvent(WebQQEvent):
    def __init__(self, msg, handler):
        self.handler = handler
        self.message = msg

    def __unicode__(self):
        return u"WebQQ Got msg: {0}".format(self.message)

class RetryEvent(WebQQEvent):
    def __init__(self, cls, req, handler, err = None, *args, **kwargs):
        self.cls = cls
        self.req = req
        self.handler = handler
        self.args = args
        self.kwargs = kwargs
        self.err = err

    def __unicode__(self):
        return u"{0} Retry with Error {1}".format(self.cls.__name__, self.err)

class RemoveEvent(WebQQEvent):
    def __init__(self, handler):
        self.handler = handler

    def __unicode__(self):
        return u"Remove Handler {0}".format(self.handler.__class__.__name__)


class WebQQHandler(IOHandler):
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

class CheckHandler(WebQQHandler):
    """ 检查是否需要验证码
    url : http://check.ptlogin2.qq.com/check
    接口返回:
        ptui_checkVC('0','!PTH','\x00\x00\x00\x00\x64\x74\x8b\x05');
        第一个参数表示状态码, 0 不需要验证, 第二个为验证码, 第三个为uin
    """
    def setup(self):
        url = "http://check.ptlogin2.qq.com/check"
        params = {"uin":self.webqq.qid, "appid":self.webqq.aid,
                  "r" : random.random()}
        self.method = "GET"
        if not self.req:
            self.req = http_sock.make_request(url, params, self.method)
        self.sock, self.data = http_sock.make_http_sock_data(self.req)

    def handle_read(self):
        self._readable = False
        resp = http_sock.make_response(self.sock, self.req, self.method)
        self.webqq.check_data = resp.read()
        self.webqq.event(CheckedEvent(self.webqq.check_data, self))

    def handle_write(self):
        self.sock.sendall(self.data)
        self._writable = False
        self._readable = True

class BeforeLoginHandler(WebQQHandler):
    """ 登录之前的操作
    :接口返回
        ptuiCB('0','0','http://www.qq.com','0','登录成功!', 'qxbot');
    先检查是否需要验证码,不需要验证码则首先执行一次登录
    然后获取Cookie里的ptwebqq,skey保存在实例里,供后面的接口调用
    """
    def setup(self, password = None):
        self.method = "GET"
        if not self.req:
            assert password
            password = self.webqq.handle_pwd(password)
            params = [("u",self.webqq.qid), ("p",password),
                    ("verifycode", self.webqq.check_code), ("webqq_type",10),
                    ("remember_uin", 1),("login2qq",1),
                    ("aid", self.webqq.aid), ("u1", "http://www.qq.com"),
                    ("h", 1), ("ptredirect", 0), ("ptlang", 2052), ("from_ui", 1),
                    ("pttype", 1), ("dumy", ""), ("fp", "loginerroralert"),
                    ("mibao_css","m_webqq"), ("t",1),
                    ("g",1), ("js_type",0), ("js_ver", 10021)]
            url = "https://ssl.ptlogin2.qq.com/login"
            self.req = http_sock.make_request(url, params, self.method)
            if self.webqq.require_check:
                self.req.add_header("Referer", "https://ui.ptlogin2.qq.com/cgi-"
                                "bin/login?target=self&style=5&mibao_css=m_"
                                "webqq&appid=1003903&enable_qlogin=0&no_ver"
                                "ifyimg=1&s_url=http%3A%2F%2Fweb.qq.com%2Fl"
                                "oginproxy.html&f_url=loginerroralert&stron"
                                "g_login=1&login_state=10&t=20130221001")

        self.sock, self.data = http_sock.make_http_sock_data(self.req)

    def handle_write(self):
        self.sock.sendall(self.data)
        self._readable = True
        self._writable = False

    def handle_read(self):
        self._readable = False
        resp = http_sock.make_response(self.sock, self.req, self.method)
        self.webqq.blogin_data = resp.read().decode("utf-8")
        self.webqq.event(BeforeLoginEvent(self.webqq.blogin_data, self))
        eval("self.webqq."+self.webqq.blogin_data.rstrip().rstrip(";"))


class LoginHandler(WebQQHandler):
    """ 利用前几步生成的数据进行登录
    :接口返回示例
        {u'retcode': 0,
        u'result': {
            'status': 'online', 'index': 1075,
            'psessionid': '', u'user_state': 0, u'f': 0,
            u'uin': 1685359365, u'cip': 3673277226,
            u'vfwebqq': u'', u'port': 43332}}
        保存result中的psessionid和vfwebqq供后面接口调用
    """
    def setup(self):
        self.method = "POST"
        if not self.req:
            url = "http://d.web2.qq.com/channel/login2"
            params = [("r", '{"status":"online","ptwebqq":"%s","passwd_sig":"",'
                    '"clientid":"%d","psessionid":null}'\
                    % (self.webqq.ptwebqq, self.webqq.clientid)),
                    ("clientid", self.webqq.clientid),
                    ("psessionid", "null")
                    ]
            self.req = http_sock.make_request(url, params, self.method)

            self.req.add_header("Referer", "http://d.web2.qq.com/proxy.html?"
                                "v=20110331002&callback=1&id=3")
            self.req.add_header("Origin", "http://d.web2.qq.com")
        self.sock, self.data = http_sock.make_http_sock_data(self.req)

    def handle_write(self):
        self._writable = False
        self.sock.sendall(self.data)
        #body = "\r\n\r\n".join(self.data.split("\r\n\r\n")[1:])
        #self.sock.sendall(body)
        self._readable = True

    def handle_read(self):
        self._readable = False
        resp = http_sock.make_response(self.sock, self.req, self.method)
        tmp = resp.read()
        data = json.loads(tmp)
        self.webqq.vfwebqq = data.get("result", {}).get("vfwebqq")
        self.webqq.psessionid = data.get("result", {}).get("psessionid")
        self.webqq.event(WebQQLoginedEvent(self))


class HeartbeatHandler(WebQQHandler):
    """ 心跳 """
    def setup(self, delay = 0):
        self._readable = False
        self.delay = delay
        self.method = "GET"

        if not self.req:
            url = "http://web.qq.com/web2/get_msg_tip"
            params = [("uin", ""), ("tp", 1), ("id", 0), ("retype", 1),
                        ("rc", self.webqq.rc), ("lv", 2),
                    ("t", int(self.webqq.hb_last_time * 1000))]
            self.req = http_sock.make_request(url, params, self.method)
        try:
            self.sock, self.data = http_sock.make_http_sock_data(self.req)
        except socket.error, err:
            self.webqq.event(RetryEvent(HeartbeatHandler, self.req, self, err))
            self._writable = False
            self.sock = None
            self.data = None

    def handle_write(self):
        self._writable = False
        try:
            self.sock.sendall(self.data)
        except socket.error, err:
            self.webqq.event(RetryEvent(HeartbeatHandler, self.req, self, err))
        self.webqq.event(WebQQHeartbeatEvent(self), self.delay)

    def is_readable(self):
        return False

    def is_writable(self):
        with self.lock:
            return self.sock and self.data and self._writable

class PollHandler(WebQQHandler ):
    """ 获取消息 """
    def setup(self, delay = 0):
        self.delay = delay
        self.method = "POST"
        if not self.req:
            url = "http://d.web2.qq.com/channel/poll2"
            params = [("r", '{"clientid":"%s", "psessionid":"%s",'
                    '"key":0, "ids":[]}' % (self.webqq.clientid,
                                            self.webqq.psessionid)),
                    ("clientid", self.webqq.clientid),
                    ("psessionid", self.webqq.psessionid)]
            self.req = http_sock.make_request(url, params, self.method)
            self.req.add_header("Referer", "http://d.web2.qq.com/proxy.html?v="
                                "20110331002&callback=1&id=2")
        try:
            self.sock, self.data = http_sock.make_http_sock_data(self.req)
        except socket.error:
            self.webqq.event(RetryEvent(PollHandler, self.req, self))
            self._writable = False
            self.sock = None
            self.data = None


    def handle_write(self):
        self._writable = False
        try:
            self.sock.sendall(self.data)
            #self.webqq.event(WebQQPollEvent(self), self.delay)
        except socket.error:
            self.webqq.event(RetryEvent(PollHandler, self.req, self))
        else:
            self._readable = True

    def handle_read(self):
        #self._readable = False
        try:
            resp = http_sock.make_response(self.sock, self.req, self.method)
            tmp = resp.read()
            data = json.loads(tmp)
            if data:
                self._readable = False
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
            self.req = http_sock.make_request(url, params, self.method)
            self.req.add_header("Referer", "http://d.web2.qq.com/proxy.html")

        try:
            self.sock, self.data = http_sock.make_http_sock_data(self.req)
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


class GroupListEvent(WebQQEvent):
    def __init__(self, handler, data):
        self.handler = handler
        self.data = data

    def __unicode__(self):
        return u"WebQQ Update Group List"

class WebQQRosterUpdatedEvent(WebQQEvent):
    def __init__(self, handler):
        self.handler = handler

    def __unicode__(self):
        return u"WebQQ Roster Updated"


class GroupListHandler(WebQQHandler):
    def setup(self, delay = 0):
        self.delay = delay
        self.method = "POST"
        if not self.req:
            url = "http://s.web2.qq.com/api/get_group_name_list_mask2"
            params = [("r", '{"vfwebqq":"%s"}' % self.webqq.vfwebqq),]
            self.req = http_sock.make_request(url, params, self.method)
            self.req.add_header("Origin", "http://s.web2.qq.com")
            self.req.add_header("Referer", "http://s.web2.qq.com/proxy.ht"
                                    "ml?v=20110412001&callback=1&id=1")
        try:
            self.sock, self.data = http_sock.make_http_sock_data(self.req)
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
            resp = http_sock.make_response(self.sock, self.req, self.method)
            tmp = resp.read()
            data = json.loads(tmp)
            self.webqq.event(GroupListEvent(self, data), self.delay)
        except ValueError:
            pass

class GroupMembersEvent(WebQQEvent):
    def __init__(self, handler, data, gcode):
        self.handler = handler
        self.data = data
        self.gcode = gcode

    def __unicode__(self):
        return u"WebQQ fetch group members"


class GroupMembersHandler(WebQQHandler):
    def setup(self, gcode, done = False):
        self.done = done
        self.gcode = gcode
        self.method = "GET"

        if not self.req:
            url = "http://s.web2.qq.com/api/get_group_info_ext2"
            params = [("gcode", gcode),("vfwebqq", self.webqq.vfwebqq),
                    ("t", int(time.time()))]
            self.req = http_sock.make_request(url, params)
            self.req.add_header("Referer", "http://d.web2.qq.com/proxy."
                                    "html?v=20110331002&callback=1&id=3")
        try:
            self.sock, self.data = http_sock.make_http_sock_data(self.req)
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
            resp = http_sock.make_response(self.sock, self.req, self.method)
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


class WebQQ(object):
    """ WebQQ
    :param :qid QQ号
    :param :event_queue pyxmpp2时间队列"""
    def __init__(self, qid, event_queue):
        self.logger = get_logger()
        self.qid = qid
        self.aid = 1003903
        self.clientid = random.randrange(11111111, 99999999)
        self.msg_id = random.randrange(1111111, 99999999)
        self.group_map = {}      # 群映射
        self.group_m_map = {}    # 群到群成员的映射
        self.uin_qid_map = {}    # uin 到 qq号的映射
        self.check_code = None
        self.skey = None
        self.ptwebqq = None
        self.require_check = False
        self.QUIT = False
        self.last_msg = {}
        self.event_queue = event_queue
        self.check_data = None           # CheckHanlder返回的数据
        self.blogin_data = None          # 登录前返回的数据
        self.rc = 1
        self.start_time = time.time()
        self.hb_last_time = self.start_time
        self.poll_last_time = self.start_time
        self._helper = HttpHelper()
        self.connected = False
        self.polled = False
        self.heartbeated = False
        self.group_lst_updated = False

    def event(self, event, delay = 0):
        """ timeout可以延迟将事件放入事件队列 """
        if delay:
            target = partial(self.put_delay_event, self.event_queue, event, delay)
            t = threading.Thread(target = target)
            t.setDaemon(True)
            t.start()
        else:
            self.event_queue.put(event)

    def put_delay_event(self, queue,event, delay):
        """ 应当放入线程中 """
        time.sleep(delay)
        queue.put(event)

    def ptui_checkVC(self, r, vcode, uin):
        """ 处理检查的回调 返回三个值 """
        if int(r) == 0:
            self.logger.info("Check Ok")
            self.check_code = vcode
        else:
            self.logger.warn("Check Error")
            self.check_code = self.get_check_img(vcode)
            self.require_check = True
        return r, self.check_code, uin

    def get_check_img(self, vcode):
        """ 获取验证图片 """
        url = "https://ssl.captcha.qq.com/getimage"
        params = [("aid", self.aid), ("r", random.random()),
                  ("uin", self.qid)]
        helper = HttpHelper(url, params, jar = http_sock.cookiejar)
        res = helper.open()
        path = tempfile.mktemp()
        fp = open(path, 'wb')
        fp.write(res.read())
        fp.close()
        res = upload_file("check.jpg", path)
        print res.geturl()
        check_code = None
        while not check_code:
            check_code = raw_input("打开上面连接输出图片上的验证码: ")
        return check_code.strip()

    def handle_pwd(self, password):
        """ 根据检查返回结果,调用回调生成密码和保存验证码 """
        r, self._vcode, huin = eval("self." + self.check_data.rstrip(";"))
        pwd = md5(md5(password).digest() + huin).hexdigest().upper()
        return md5(pwd + self._vcode).hexdigest().upper()

    def ptuiCB(self, scode, r, url, status, msg, nickname = None):
        """ 模拟JS登录之前的回调, 保存昵称 """
        if int(scode) == 0:
            self.logger.info("Get ptwebqq Ok")
            self.skey = http_sock.cookie['.qq.com']['/']['skey'].value
            self.ptwebqq = http_sock.cookie['.qq.com']['/']['ptwebqq'].value
            self.logined = True
        else:
            self.logger.warn("Get ptwebqq Error")
        if nickname:
            self.nickname = nickname

    def get_qid_with_uin(self, uin):
        """ 根据uin获取QQ号 """
        url = "http://s.web2.qq.com/api/get_friend_uin2"
        params = [("tuin", uin), ("verifysession", ""),("type",4),
                  ("code", ""), ("vfwebqq", self.vfwebqq),
                  ("t", time.time())]
        self._helper.change(url, params)
        self._helper.add_header("Referer", "http://d.web2.qq.com/proxy."
                                "html?v=20110331002&callback=1&id=3")
        res = self._helper.open()
        data = res.read()
        if data:
            info = json.loads(data)
            if info.get("retcode") == 0:
                return info.get("result", {}).get("account")

    def get_group_msg_img(self, uin, info):
        """ 获取消息中的图片 """
        name = info.get("name")
        file_id = info.get("file_id")
        key = info.get("key")
        server = info.get("server")
        ip, port = server.split(":")
        gid = self.group_map.get(uin, {}).get("gid")
        url = "http://web2.qq.com/cgi-bin/get_group_pic"
        params = [("type", 0), ("gid", gid), ("uin", uin),("rip", ip),
                  ("rport", port), ("fid", file_id), ("pic", name),
                  ("vfwebqq", self.vfwebqq), ("t", time.time())]
        helper = HttpHelper(url, params)
        helper.add_header("Referer", "http://web2.qq.com/")
        return helper.open()

    def get_group_name(self, gcode):
        """ 根据gcode获取群名 """
        return self.group_map.get(gcode, {}).get("name")

    def get_group_member_nick(self, gcode, uin):
        return self.group_m_map.get(gcode, {}).get(uin, {}).get("nick")
