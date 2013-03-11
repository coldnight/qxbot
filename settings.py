#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/01 14:55:34
#   Desc    :   配置文件
#
import os
import sys

sys.path.insert(0,os.path.join(os.path.abspath(os.path.dirname(__file__))))

QQ = 1685359365

QQ_PWD = ""

XMPP_ACCOUNT = "qxbot@vim-cn.com"

XMPP_PASSWD = ""

# 桥接的QQ群和XMPP帐号
BRIDGES = (
    (224241247, "clubot@vim-cn.com"),   # QQ 群 -> XMPP
)
