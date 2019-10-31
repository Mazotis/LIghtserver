#!/usr/bin/env python3
'''
    File name: webserver.py
    Author: Maxime Bergeron
    Date last modified: 10/10/2019
    Python Version: 3.5

    The web server interface module for the homeserver
'''

import requests
import socket
import socketserver
import urllib.parse
from core.common import *
from functools import partial
from http.server import SimpleHTTPRequestHandler
from io import BytesIO
from threading import Thread


class WebServerHandler(SimpleHTTPRequestHandler):
    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.dm_host = self.config['SERVER']['HOST']
        self.dm_port = self.config['SERVER'].getint('PORT')
        super().__init__(*args, **kwargs)

    def translate_path(self, path):
        return SimpleHTTPRequestHandler.translate_path(self, './web' + path)

    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'x-www-form-urlencoded')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        postvars = urllib.parse.parse_qs(
            self.rfile.read(content_length), keep_blank_values=1)
        request = bool(postvars[b'request'][0].decode('utf-8'))
        reqtype = int(postvars[b'reqtype'][0].decode('utf-8'))
        self._set_response()
        response = BytesIO()
        if request:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.dm_host, self.dm_port))
            if reqtype == 1:
                try:
                    s.sendall("0008".encode('utf-8'))
                    s.sendall("getstate".encode('utf-8'))
                    data = s.recv(4096)
                    if data:
                        response.write(data)
                finally:
                    s.close()
            if reqtype == 2:
                devid = str(postvars[b'devid'][0].decode('utf-8'))
                value = str(postvars[b'value'][0].decode('utf-8'))
                isintensity = str(postvars[b'isintensity'][0].decode('utf-8'))
                skiptime = postvars[b'skiptime'][0].decode(
                    'utf-8') in ['true', True]
                try:
                    s.sendall("0008".encode('utf-8'))
                    s.sendall("setstate".encode('utf-8'))
                    s.sendall(devid.zfill(3).encode('utf-8'))
                    s.sendall(value.zfill(8).encode('utf-8'))
                    s.sendall(isintensity.encode('utf-8'))
                    if skiptime:
                        s.sendall("1".encode('utf-8'))
                    else:
                        s.sendall("0".encode('utf-8'))
                    data = s.recv(1)
                    if data:
                        response.write(data)
                finally:
                    s.close()
            if reqtype == 3:
                cmode = postvars[b'mode'][0].decode('utf-8') in ['true', True]
                devid = str(postvars[b'devid'][0].decode('utf-8'))
                try:
                    s.sendall("0007".encode('utf-8'))
                    s.sendall("setmode".encode('utf-8'))
                    s.sendall(devid.zfill(3).encode('utf-8'))
                    if cmode:
                        s.sendall("1".encode('utf-8'))
                    else:
                        s.sendall("0".encode('utf-8'))
                    data = s.recv(1)
                    if data:
                        response.write(data)
                finally:
                    s.close()
            if reqtype == 4:
                group = str(postvars[b'group'][0].decode('utf-8'))
                value = str(postvars[b'value'][0].decode('utf-8'))
                skiptime = postvars[b'skiptime'][0].decode(
                    'utf-8') in ['true', True]
                try:
                    s.sendall("0008".encode('utf-8'))
                    s.sendall("setgroup".encode('utf-8'))
                    s.sendall(group.zfill(64).encode('utf-8'))
                    s.sendall(value.zfill(2).encode('utf-8'))
                    if skiptime:
                        s.sendall("1".encode('utf-8'))
                    else:
                        s.sendall("0".encode('utf-8'))
                    data = s.recv(1)
                    if data:
                        response.write(data)
                finally:
                    s.close()
            if reqtype == 5:
                try:
                    s.sendall("0012".encode('utf-8'))
                    s.sendall("getstatepost".encode('utf-8'))
                    data = s.recv(1024)
                    if data:
                        response.write(data)
                finally:
                    s.close()
            if reqtype == 6:
                try:
                    s.sendall("0010".encode('utf-8'))
                    s.sendall("setallmode".encode('utf-8'))
                    data = s.recv(1)
                    if data:
                        response.write(data)
                finally:
                    s.close()
            if reqtype == 7:
                try:
                    module = str(postvars[b'module'][0].decode('utf-8'))
                    s.sendall("0009".encode('utf-8'))
                    s.sendall("getmodule".encode('utf-8'))
                    s.sendall(module.zfill(64).encode('utf-8'))
                    data = s.recv(8184)
                    if data:
                        response.write(data)
                finally:
                    s.close()
            if reqtype == 8:
                try:
                    clientid = str(postvars[b'clientid'][0].decode('utf-8'))
                    s.sendall("0008".encode('utf-8'))
                    s.sendall("dobackup".encode('utf-8'))
                    s.sendall(clientid.zfill(4).encode('utf-8'))
                    data = s.recv(1)
                    if data:
                        response.write(data)
                finally:
                    s.close()
            if reqtype == 9:
                lock = postvars[b'lock'][0].decode('utf-8')
                devid = str(postvars[b'devid'][0].decode('utf-8'))
                try:
                    s.sendall("0007".encode('utf-8'))
                    s.sendall("setlock".encode('utf-8'))
                    s.sendall(devid.zfill(3).encode('utf-8'))
                    s.sendall(lock.zfill(1).encode('utf-8'))
                    data = s.recv(1)
                    if data:
                        response.write(data)
                finally:
                    s.close()
            if reqtype == 10:
                try:
                    s.sendall("0009".encode('utf-8'))
                    s.sendall("getconfig".encode('utf-8'))
                    data = s.recv(8184)
                    if data:
                        response.write(data)
                finally:
                    s.close()
            if reqtype == 11:
                section = str(postvars[b'section'][0].decode('utf-8'))
                configdata = urllib.parse.unquote(
                    postvars[b'configdata'][0].decode('utf-8'))
                try:
                    s.sendall("0009".encode('utf-8'))
                    s.sendall("setconfig".encode('utf-8'))
                    s.sendall(str(len(section)).zfill(4).encode('utf-8'))
                    s.sendall(section.encode('utf-8'))
                    s.sendall(configdata.encode('utf-8'))
                    data = s.recv(1)
                    if data:
                        response.write(data)
                finally:
                    s.close()
            if reqtype == 12:
                try:
                    debuglevel = postvars[b'debuglevel'][0].decode('utf-8')
                    s.sendall("0011".encode('utf-8'))
                    s.sendall("getdebuglog".encode('utf-8'))
                    s.sendall(debuglevel.encode('utf-8'))
                    data = s.recv(8184)
                    if data:
                        response.write(data)
                finally:
                    s.close()
        else:
            response.write("No request".encode("UTF-8"))
        self.wfile.write(response.getvalue())


class webserver(Thread):
    def __init__(self, config, lm):
        Thread.__init__(self)
        self.config = config
        self.port = self.config['SERVER'].getint('WEBSERVER_PORT')
        self.running = True

    def run(self):
        debug.write("Starting control webserver on port {}".format(
            self.port), 0, "WEBSERVER")
        socketserver.TCPServer.allow_reuse_address = True
        _handler = partial(WebServerHandler, self.config)
        httpd = socketserver.TCPServer(("", self.port), _handler)

        try:
            while self.running:
                httpd.handle_request()
        finally:
            httpd.server_close()
            debug.write("Stopped.", 0, "WEBSERVER")
            return

    def stop(self):
        debug.write("Stopping.", 0, "WEBSERVER")
        self.running = False
        # Needs a last call to shut down properly
        try:
            requests.get("http://localhost:{}/".format(self.port))
        except requests.exceptions.ConnectionError:
            pass
