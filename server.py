#!/usr/bin/python
# -*- coding: utf-8 -*-
import cgi
import os
import datetime
import uuid
import json
import zipfile
# pip install requests
import requests
# pip install retry
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


DEBUG_MODE = True
FILE_PATH = '/Volumes/HDD/workshop/old/ar.upload.ming/files'
LOG_FILE_PATH = '/Volumes/HDD/workshop/old/ar.upload.ming/logs'
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
    postForm = None

    def output(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def error(self, code):
        self.send_response(code)
        self.end_headers()

    def logger(self, msg):
        if not DEBUG_MODE:
            return False
        date_file = datetime.datetime.now().strftime("%Y%m%d") + '.log'
        file = os.path.join(LOG_FILE_PATH, date_file)
        if not msg:
            msg = ''
        with open(file, 'a+') as f:
            f.write(msg + '\n')

    def remove_file(self):
        local_file_path = UploadServer.postForm.getvalue('post_data')
        target_path = os.path.join(FILE_PATH, local_file_path)
        file_exists = os.path.exists(target_path)
        success_data = {
            'code': 200,
            'error': 0,
            'message': 'success',
            'success': 1,
        }
        if not file_exists:
            self.output(success_data)
            return
        try:
            # 删除文件
            os.remove(target_path)
            self.output(success_data)

        except FileNotFoundError:
            self.error(400)
            return

    def upload_file(self):
        # 临时文件路径
        attachment_file_path = UploadServer.postForm.getvalue('ATTACHMENT_path')
        # 原文件名
        attachment_file_name = UploadServer.postForm.getvalue('ATTACHMENT_name')
        # 文件大小
        attachment_file_size = UploadServer.postForm.getvalue('ATTACHMENT_size')
        # 文件md5
        attachment_file_md5 = UploadServer.postForm.getvalue('ATTACHMENT_md5')
        # UID
        attachment_uid = self.get_params('UPLOAD-SERVER-USER')
        # TOKEN
        attachment_token = self.get_params('UPLOAD-SERVER-TOKEN')
        # REQUEST DATE
        attachment_date = self.get_params('UPLOAD-SERVER-DATE')
        # REQUEST NOTIFY URL
        attachment_notify_url = self.get_params('UPLOAD-SERVER-NOTIFY-URL')
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
                notify_result = notify_api(attachment_notify_url, data)
                data['IS_IMAGE'] = notify_result['IS_IMAGE']
                data['REMOTE_URL'] = notify_result['REMOTE_URL']
                data['url'] = notify_result['REMOTE_URL']

            self.output(data)

        except FileNotFoundError:
            self.error(400)
            return

    def on_zip_file(self):
        get_zip_files = UploadServer.postForm.getvalue('post_data')
        zip_array = get_zip_files.strip(',').split(',')
        rnd_file = get_uuid_file() + '.zip'
        # 获取时间路径
        date_path = get_date_path()
        target_path = os.path.join(FILE_PATH, date_path)
        target_file = os.path.join(target_path, rnd_file)
        try:
            zip_file = zipfile.ZipFile(target_file, 'w', zipfile.ZIP_DEFLATED)
            for zf in zip_array:
                if not zf:
                    continue
                real_file = os.path.join(FILE_PATH, zf)
                is_exists = os.path.exists(real_file)
                self.logger(real_file)
                if not is_exists:
                    continue
                basename = os.path.basename(zf)
                zip_file.write(real_file, basename)

            # REQUEST NOTIFY URL
            attachment_notify_url = self.get_params('UPLOAD-SERVER-NOTIFY-URL')
            # 生成URL
            file_url = target_file.replace(FILE_PATH, BASE_URL)
            data = {
                'REMOTE_URL': file_url
            }
            if attachment_notify_url:
                notify_api(attachment_notify_url, data)

            self.output(data)

        except FileNotFoundError:
            self.error(400)
            return

    def do_POST(self):
        UploadServer.postForm = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
                     })

        action = UploadServer.postForm.getvalue('action')
        if not action:
            action = 'upload'

        if 'upload' == action:
            self.upload_file()
        elif 'delete' == action:
            self.remove_file()
        elif 'download_zip' == action:
            self.on_zip_file()

    def get_params(self, key):
        if key in self.headers:
            return self.headers[key]
        return UploadServer.postForm.getvalue(key)


httpd = HTTPServer(('127.0.0.1', 8000), UploadServer)
print("Server started on 127.0.0.1,port 8000.....")
httpd.serve_forever()
