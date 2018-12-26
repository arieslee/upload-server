#!/usr/bin/python
# -*- coding: utf-8 -*-
import cgi
import os
import datetime
import uuid
import json
#pip install requests
import requests
#pip install retry
from retry import retry
from http.server import BaseHTTPRequestHandler, HTTPServer


def get_date_path():
    date_path = datetime.datetime.now().strftime("%Y/%m%d")
    return date_path


def get_uuid_file():
    uuid_str = str(uuid.uuid1()).replace('-', '')
    return uuid_str


def get_file_ext(path):
    return os.path.splitext(path)[1]


FILE_PATH = '/Volumes/HDD/workshop/old/ar.upload.ming/files'

BASE_URL = 'http://ar.upload.ming/files'  # 必须与商城common/config/params.php中的remoteUploadUrl一致
# 重试的次数
RETRY_TIMES = 5
# 重试的时间间隔，成倍增长
RETRY_BACK_OFF = 2
# 重试的间隔
RETRY_DELAY = 2


@retry(FileNotFoundError, tries=RETRY_TIMES, backoff=RETRY_BACK_OFF, delay=RETRY_DELAY)
def notify_api(attachment_notify_url, data):
    res = requests.post(attachment_notify_url, data=data)
    if res.status_code == 200:
        notify_json = res.json()['data']['message']
        return notify_json
    else:
        raise FileNotFoundError('文件上传失败')


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
        # UID
        attachment_uid = form.getvalue('ATTACHMENT_uid')
        # TOKEN
        attachment_token = form.getvalue('ATTACHMENT_token')
        # REQUEST DATE
        attachment_date = form.getvalue('ATTACHMENT_date')
        # REQUEST NOTIFY URL
        attachment_notify_url = form.getvalue('ATTACHMENT_notify_url')
        # 获取文件扩展名
        file_ext = get_file_ext(attachment_file_name)
        if not file_ext:
            file_ext = '.jpg'

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
            data = {
                'url': file_url,
                'size': attachment_file_size,
                'name': attachment_file_name,
                'md5': attachment_file_md5,
                'uid': attachment_uid,
                'token': attachment_token,
                'request_date': attachment_date,
            }
            if attachment_notify_url:
                notify_api(attachment_notify_url, data)

            else:
                self.output(data)

        except FileNotFoundError:
            self.error(400)
            return


httpd = HTTPServer(('127.0.0.1', 8000), UploadServer)
print("Server started on 127.0.0.1,port 8000.....")
httpd.serve_forever()
