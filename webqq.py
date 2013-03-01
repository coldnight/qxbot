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
import random
import tempfile
import threading
from hashlib import md5
from util import HttpHelper, get_logger, upload_file

from settings import QQ, QQ_PWD

class WebQQ(object):
    """ WebQQ
    :param :qid QQ号"""
    def __init__(self, qid, message_dispatch):
        self.logger = get_logger()
        self._qid = qid
        self._aid = 1003903
        self._helper = HttpHelper()
        self.clientid = random.randrange(11111111, 99999999)
        self.msg_id = random.randrange(1111111, 99999999)
        self.group_map = {}      # 群映射
        self.group_m_map = {}    # 群到群成员的映射
        self.uin_qid_map = {}    # uin 到 qq号的映射
        self._check_code = None
        self.logined = False
        self.skey = None
        self.ptwebqq = None
        self.require_check = False
        self.msg_dispatch = message_dispatch
        self.QUIT = False

    def check(self):
        """ 检查是否需要验证码
        接口返回:
            ptui_checkVC('0','!PTH','\x00\x00\x00\x00\x64\x74\x8b\x05');
            第一个参数表示状态码, 0 不需要验证, 第二个为验证码, 第三个为uin
        """
        url = "http://check.ptlogin2.qq.com/check"
        params = {"uin":self._qid, "appid":self._aid,
                  "r" : random.random()}
        self._helper.change(url, params)
        res= self._helper.open()
        result = res.read()
        self.logger.debug(result)
        return result

    def ptui_checkVC(self, r, vcode, uin):
        """ 处理检查的回调 返回三个值 """
        if int(r) == 0:
            self.logger.info("Check Ok")
        else:
            self.logger.warn("Check Error")
            vcode = self.get_check_img(vcode)
            self.require_check = True
        return r, vcode, uin

    def get_check_img(self, vcode):
        """ 获取验证图片 """
        url = "https://ssl.captcha.qq.com/getimage"
        params = [("aid", self._aid), ("r", random.random()),
                  ("uin", self._qid)]
        helper = HttpHelper(url, params)
        res = helper.open()
        path = tempfile.mktemp()
        fp = open(path, 'wb')
        fp.write(res.read())
        fp.close()
        res = upload_file("check.jpg", path)
        print res.geturl()
        check_code = raw_input("打开上面连接输出图片上的验证码: ")
        return check_code

    def handle_pwd(self, password):
        """ 根据检查返回结果,调用回调生成密码和保存验证码 """
        r, self._vcode, huin = eval("self." + self.check().rstrip(";"))
        pwd = md5(md5(password).digest() + huin).hexdigest().upper()
        return md5(pwd + self._vcode).hexdigest().upper()

    def ptuiCB(self, scode, r, url, status, msg, nickname = None):
        """ 模拟JS登录之前的回调, 保存昵称 """
        if int(scode) == 0:
            self.logger.info("Get ptwebqq Ok")
            self.skey = self._helper.cookie['.qq.com']['/']['skey'].value
            self.ptwebqq = self._helper.cookie['.qq.com']['/']['ptwebqq'].value
            self.logined = True
        else:
            self.logger.warn("Get ptwebqq Error")
        if nickname:
            self.nickname = nickname

    def before_login(self, pwd):
        """ 登录之前的操作
        :接口返回
            ptuiCB('0','0','http://www.qq.com','0','登录成功!', 'qxbot');
        先检查是否需要验证码,不需要验证码则首先执行一次登录
        然后获取Cookie里的ptwebqq,skey保存在实例里,供后面的接口调用
        """
        password = self.handle_pwd(pwd)
        t = 1 if self.require_check else 1
        params = [("u",self._qid), ("p",password),
                  ("verifycode", self._vcode), ("webqq_type",10),
                  ("remember_uin", 1),("login2qq",1),
                  ("aid", self._aid), ("u1", "http://www.qq.com"), ("h", 1),
                  ("ptredirect", 0), ("ptlang", 2052), ("from_ui", 1),
                  ("pttype", 1), ("dumy", ""), ("fp", "loginerroralert"),
                  ("mibao_css","m_webqq"), ("t",t),
                  ("g",1), ("js_type",0), ("js_ver", 10021)]
        url = "https://ssl.ptlogin2.qq.com/login"
        self._helper.change(url, params)
        self._helper.add_header("Referer",
                                "https://ui.ptlogin2.qq.com/cgi-bin/login?"
                                "target=self&style=5&mibao_css=m_webqq&app"
                                "id=1003903&enable_qlogin=0&no_verifyimg=1"
                                "&s_url=http%3A%2F%2Fweb.qq.com%2Floginpro"
                                "xy.html&f_url=log")
        res = self._helper.open()
        output = res.read()
        eval("self."+output.strip().rstrip(";"))
        self.logger.debug(output)

    def login(self, pwd):
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

        self.before_login(pwd)
        url = "http://d.web2.qq.com/channel/login2"
        params = [("r", '{"status":"online","ptwebqq":"%s","passwd_sig":"",'
                   '"clientid":"%d", "psessionid":null}'\
                   % (self.ptwebqq, self.clientid)),
                  ("clientid", self.clientid),
                  ("psessionid", "null")
                  ]
        self._helper.change(url, params, "POST")
        self._helper.add_header("Referer", "http://d.web2.qq.com/proxy.html?"
                                "v=20110331002&callback=1&id=3")
        res = self._helper.open()
        data = json.loads(res.read())
        self.vfwebqq = data.get("result", {}).get("vfwebqq")
        self.psessionid = data.get("result", {}).get("psessionid")
        self.logger.debug(data)
        if data.get("retcode") == 0:
            self.logger.info("Login success")
        else:
            self.logger.warn("Login Error")

        self.mainloop()

    def mainloop(self):
        """ 主循环 """
        if self.logined:
            heartbeat = threading.Thread(name="heartbeat", target=self.heartbeat)
            heartbeat.setDaemon(True)
            heartbeat.start()
            self.get_group_members()
            self.poll()

    def poll(self):
        """ 获取消息 """
        url = "http://d.web2.qq.com/channel/poll2"
        params = [("r", '{"clientid":"%s", "psessionid":"%s",'
                   '"key":0, "ids":[]}' % (self.clientid,
                                           self.psessionid)),
                  ("clientid", self.clientid),
                  ("psessionid", self.psessionid)]
        helper = HttpHelper(url, params, "POST")
        helper.add_header("Origin", "http://d.web2.qq.com")
        helper.add_header("Referer", "http://d.web2.qq.com/proxy.html?v="
                          "20110331002&callback=1&id=3")
        self.logger.info("Start Poll")
        while True:
            res = helper.open()
            data = res.read()
            if data:
                messages = json.loads(data)
                self.logger.debug("Receiver Message %r", messages)
                self.msg_dispatch.dispatch_qq(messages)
            self.logger.debug("Poll Done")

        self.QUIT = True

    def heartbeat(self):
        """ 心跳 """
        url = "http://web.qq.com/web2/get_msg_tip"
        i = 1
        helper = HttpHelper()
        while not self.QUIT:
            params = [("uin", ""), ("tp", 1), ("id", 0), ("retype", 1),
                      ("rc", i), ("lv", 2), ("t", int(time.time() * 1000))]
            helper.change(url, params)
            helper.open()
            self.logger.info("Heartbeat")
            i += 1
            time.sleep(60)

    def get_group_map(self):
        """ 获取群映射列表 """
        self.logger.info("Get Group List")
        url = "http://s.web2.qq.com/api/get_group_name_list_mask2"
        params = [("r", '{"vfwebqq":"%s"}' % self.vfwebqq),]
        self._helper.change(url, params, "POST")
        self._helper.add_header("Origin", "http://s.web2.qq.com")
        self._helper.add_header("Referer", "http://s.web2.qq.com/proxy.ht"
                                "ml?v=20110412001&callback=1&id=1")

        res = self._helper.open()
        data = json.loads(res.read())
        group_map = {}
        if data.get("retcode") == 0:
            group_list = data.get("result", {}).get("gnamelist", [])
            for group in group_list:
                gcode = group.get("code")
                group_map[gcode] = group

        self.group_map = group_map
        return group_map

    def get_group_members(self):
        """ 根据群code获取群列表 """
        group_map = self.get_group_map()
        self.logger.info("Fetch group members")
        group_m_map = {}
        for gcode in group_map:
            url = "http://s.web2.qq.com/api/get_group_info_ext2"
            params = [("gcode", gcode),("vfwebqq", self.vfwebqq),
                    ("t", int(time.time()))]
            self._helper.change(url, params)
            self._helper.add_header("Referer", "http://d.web2.qq.com/proxy."
                                    "html?v=20110331002&callback=1&id=3")
            res = self._helper.open()
            info = json.loads(res.read())
            members = info.get("result", {}).get("minfo", [])
            group_m_map[gcode] = {}
            for m in members:
                uin = m.get("uin")
                group_m_map[gcode][uin] = m

        self.group_m_map = group_m_map
        self.msg_dispatch.get_map()
        return group_m_map

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

    def send_group_msg(self, group_uin, content):
        gid = self.group_map.get(group_uin).get("gid")
        content = [content,["font",
                   {"name":"宋体", "size":10, "style":[0,0,0],
                    "color":"000000"}]]
        r = {"group_uin": gid, "content": json.dumps(content),
             "msg_id": self.msg_id, "clientid": self.clientid,
             "psessionid": self.psessionid}
        self.msg_id += 1
        url = "http://d.web2.qq.com/channel/send_qun_msg2"
        params = [("r", json.dumps(r)), ("sessionid", self.psessionid),
                  ("clientid", self.clientid)]
        helper = HttpHelper(url, params, "POST")
        helper.add_header("Referer", "http://d.web2.qq.com/proxy.html")
        helper.open()


if __name__ == "__main__":
    webqq = WebQQ(QQ)
    webqq.login(QQ_PWD)
