#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/04 09:58:26
#   Desc    :   Http Socket 实现
#
import ssl
import socket
import urllib
import urllib2
import httplib
import urlparse
import tempfile
import cookielib
from util import Form

class HTTPSock(object):
    def __init__(self):
        cookiefile = tempfile.mktemp()
        self.cookiejar = cookielib.MozillaCookieJar(cookiefile)

    def make_request(self, url, form, method = "GET"):
        request = urllib2.Request(url)
        if isinstance(form, Form):
            request.add_header("Content-Type", form.get_content_type())
            request.add_header("Content-Length", len(str(form)))
            request.add_data(str(form))
        elif isinstance(form, (dict, list, tuple)):
            params = urllib.urlencode(form)
            if method == "GET":
                url = "{0}?{1}".format(url, params)
                request = urllib2.Request(url)
            else:
                request = urllib2.Request(url, params)
                request.add_header("Content-Type", "application/x-www-form-urlencoded")

        self.cookiejar.add_cookie_header(request)
        request.headers.update(request.unredirected_hdrs)
        return request

    def make_response(self, sock, req, method):
        r = httplib.HTTPResponse(sock, 0, strict = 0, method = method, buffering=True)
        r.begin()

        r.recv = r.read
        fp = socket._fileobject(r, close=True)

        resp = urllib.addinfourl(fp, r.msg, req.get_full_url())
        resp.code = r.status
        resp.msg = r.reason
        self.cookiejar.extract_cookies(resp, req)
        self.cookiejar.save()
        return resp


    def make_http_sock_data(self, request):
        url = request.get_full_url()
        headers = request.headers
        data = request.get_data()
        parse = urlparse.urlparse(url)
        host, port = urllib.splitport(parse.netloc)
        typ = parse.scheme
        port = port if port else getattr(httplib, typ.upper() + "_PORT")
        data =  self.get_http_source(parse, data, headers)
        if hasattr(self, "do_" + typ):
            return getattr(self, "do_"+typ)(host, port), data

    def do_http(self, host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, int(port)))
        sock.setblocking(0)
        return sock

    def do_https(self, host, port, keyfile = None, certfile = None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, int(port)))
        sock = ssl.wrap_socket(sock, keyfile, certfile)
        sock.setblocking(0)
        return sock

    def get_http_source(self, parse, data, headers):
        path = parse.path
        query = parse.query
        path = path + "?" + query if query else path
        path = path if path else "/"
        method = "POST" if data else "GET"
        datas = ["{0} {1} HTTP/1.1".format(method, path)]
        headers["Host"] = parse.netloc
        headers["Connection"] = "Keep-Alive"
        headers["Accept"] = "*/*"
        headers["Accept-Charset"] = "UTF-8,*;q=0.5"
        headers["Accept-Encoding"] = "gzip,deflate,sdch"
        headers["Accept-Language"] = "zh-CN,zh;q=0.8"
        headers["User-Agent"] =  "Mozilla/5.0 (X11; Linux x86_64)"\
                        "AppleWebKit/537.11 (KHTML, like Gecko)"\
                        " Chrome/23.0.1271.97 Safari/537.11a"
        last = []
        for key, value in headers.items():
            if key.lower() == "content-type":
                last.append((key.title(), value))
            else:
                datas.append("{0}: {1}".format(key.title(), value))
        if data:
            last.append(("Content-Lenght",   len(data)))
        for key, value in last:
            datas.append("{0}: {1}".format(key.title(), value))

        result = "\r\n".join(datas) + "\r\n\r\n"
        if data:
            result += data
        return result

    @property
    def cookie(self):
        return self.cookiejar._cookies
