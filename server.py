#!/usr/bin/python
# -*- coding: utf-8 -*-
import cgi
import os
import datetime
import uuid
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


def get_date_path():
    date_path = datetime.datetime.now().strftime("%Y/%m%d")
    return date_path


def get_uuid_file():
    uuid_str = str(uuid.uuid1()).replace('-', '')
    return uuid_str


def get_file_ext(path):
    return os.path.splitext(path)[1]


FILE_PATH = '/Volumes/HDD/workshop/old/ar.upload.ming/files/'

BASE_URL = 'http://ar.upload.ming/files/'


class UploadServer(BaseHTTPRequestHandler):

    def output(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def error(self, code):
        self.send_response(code)
        self.end_headers()

    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
                     })
        # 临时文件路径
        attachment_file_path = form.getvalue('ATTACHMENT_path')
        # 原文件名
        attachment_file_name = form.getvalue('ATTACHMENT_name')
        # 文件大小
        attachment_file_size = form.getvalue('ATTACHMENT_size')
        # 文件md5
        attachment_file_md5 = form.getvalue('ATTACHMENT_md5')
        # 获取文件扩展名
        file_ext = get_file_ext(attachment_file_name)
        tmp_file_exists = os.path.exists(attachment_file_path)
        if not tmp_file_exists:
            self.error(404)
            return

        # 获取时间路径
        date_path = get_date_path()
        # 获取随机文件名
        rnd_file = get_uuid_file() + str(file_ext)
        target_path = os.path.join(FILE_PATH, date_path)
        # 先判断文件夹是否存在,不存在就创建
        is_exists = os.path.exists(target_path)
        if not is_exists:
            os.makedirs(target_path)
        target_file = os.path.join(target_path, rnd_file)
        try:
            # 移动文件
            os.rename(attachment_file_path, target_file)
            # 生成URL
            file_url = target_file.replace(FILE_PATH, BASE_URL)
            self.output({
                'url': file_url,
                'size': attachment_file_size,
                'name': attachment_file_name,
                'md5': attachment_file_md5
            })
        except FileNotFoundError:
            self.error(400)
            return


httpd = HTTPServer(('127.0.0.1', 8000), UploadServer)
print("Server started on 127.0.0.1,port 8000.....")
httpd.serve_forever()
