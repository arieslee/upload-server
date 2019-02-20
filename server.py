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

'''
脚本运行说明：
screen -S uploadServer
nohup python3 ./server.py >/dev/null 2>&1 &
注意print有输出缓冲，使用-u参数，使得python不启用缓冲，这样就可以同步看到输出结果了。python -u ./server.py
关闭终端后再进入可以这样：
screen -list
找到相关的screen id
screen -r screenId
'''

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
BASE_URL = 'http://ar.upload.ming/files'  # 必须与商城common/config/params.php中的remoteUploadUrl一致

# FILE_PATH = '/data/wwwroot/upload/files/'
# BASE_URL = 'http://upload.ar.wqcms.com/files/'
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
    cgi_form = None
    post_uid = None
    post_token = None
    post_date = None
    post_notify_url = None

    def output(self, data, code):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def error(self, data, debug_info=None):
        if DEBUG_MODE and debug_info is not None:
            data += '[%s]' % (debug_info,)
        self.output(data, 400)

    def success(self, data, debug_info=None):
        if DEBUG_MODE and debug_info is not None:
            data += '[%s]' % (debug_info,)
        self.output(data, 200)

    @staticmethod
    def logger(msg):
        if not DEBUG_MODE:
            return False

        if isinstance(msg, tuple):
            msg = tuple(msg).__str__()
        elif isinstance(msg, list):
            msg = "".join(list(msg))
        elif isinstance(msg, dict):
            msg = json.dumps(msg)

        date_file = datetime.datetime.now().strftime("%Y%m%d") + '.log'
        log_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'logs')
        if not os.path.exists(log_file_path):
            os.makedirs(log_file_path)
        file = os.path.join(log_file_path, date_file)
        if not msg:
            msg = ''
        with open(file, 'a+') as f:
            date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msg = '[%s]%s' % (date_time, msg)
            f.write(msg + '\n')

    def request_logger(self, action, params):
        log_msg = '[%s]UID：%s,TOKEN：%s,DATE：%s,NOTIFY_URL：%s,PARAMS：%s' % (
        action, self.post_uid, self.post_token, self.post_date, self.post_notify_url, params,)
        self.logger(log_msg)

    def request_end_logger(self, action, data):
        log_msg = '[%s complete]UID：%s,TOKEN：%s,DATE：%s,NOTIFY_URL：%s,RESPONSE：%s' % (
            action, self.post_uid, self.post_token, self.post_date, self.post_notify_url, data,)
        self.logger(log_msg)

    def on_remove_file(self):
        local_file_path = self.cgi_form.getvalue('post_data')
        # 记录请求日志
        self.request_logger('remove_file', local_file_path)
        target_path = os.path.join(FILE_PATH, local_file_path)
        file_exists = os.path.exists(target_path)
        success_data = {
            'code': 200,
            'error': 0,
            'message': 'success',
            'success': 1,
        }
        if not file_exists:
            success_data['message'] = target_path + ' file not exists'
            self.success(success_data)
            self.request_end_logger('remove_file', success_data)
            return
        try:
            # 删除文件
            os.remove(target_path)
            self.success(success_data)
            self.request_end_logger('remove_file', success_data)
        except BaseException as e:
            self.logger(e.args)
            self.error('文件删除失败', e.args[1])
            return

    def on_upload_file(self):
        # 临时文件路径
        attachment_file_path = self.cgi_form.getvalue('ATTACHMENT_path')
        # 原文件名
        attachment_file_name = self.cgi_form.getvalue('ATTACHMENT_name')
        # 文件大小
        attachment_file_size = self.cgi_form.getvalue('ATTACHMENT_size')
        # 文件md5
        attachment_file_md5 = self.cgi_form.getvalue('ATTACHMENT_md5')
        # 记录请求日志
        self.request_logger('upload', attachment_file_name)
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
        post_file_name = self.cgi_form.getvalue('file_name')
        if post_file_name:
            rnd_file = post_file_name
        else:
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
                'uid': self.post_uid,
                'token': self.post_token,
                'request_date': self.post_date,
            }
            if self.post_notify_url:
                notify_result = notify_api(self.post_notify_url, data)
                data['IS_IMAGE'] = notify_result['IS_IMAGE']
                data['REMOTE_URL'] = notify_result['REMOTE_URL']
                data['url'] = notify_result['REMOTE_URL']

            self.success(data)
            self.request_end_logger('upload', data)

        except BaseException as e:
            self.logger(e.args)
            self.error('文件上传失败', e.args[0])
            return

    def on_zip_file(self):
        get_zip_files = self.cgi_form.getvalue('post_data')
        # 记录请求日志
        self.request_logger('zip_file', get_zip_files)
        zip_array = get_zip_files.strip(',').split(',')
        rnd_file = get_uuid_file() + '.zip'
        # 获取时间路径
        date_path = get_date_path()
        target_path = os.path.join(FILE_PATH, date_path)
        if not os.path.exists(target_path):
            os.makedirs(target_path)

        target_file = os.path.join(target_path, rnd_file)
        try:
            zip_file = zipfile.ZipFile(target_file, 'w', zipfile.ZIP_DEFLATED)
            for zf in zip_array:
                if not zf:
                    continue
                real_file = os.path.join(FILE_PATH, zf)
                is_exists = os.path.exists(real_file)
                if not is_exists:
                    continue
                basename = os.path.basename(zf)
                zip_file.write(real_file, basename)

            # 生成URL
            file_url = target_file.replace(FILE_PATH, BASE_URL)
            data = {
                'REMOTE_URL': file_url,
                'success': 1,
                'uid': self.post_uid,
                'token': self.post_token,
                'request_date': self.post_date,
            }

            if self.post_notify_url:
                notify_api(self.post_notify_url, data)

            self.success(data)
            self.request_end_logger('zip_file', data)

        except BaseException as e:
            self.logger(e.args)
            self.error('文件压缩失败', e.args[1])
            return

    def do_POST(self):
        self.cgi_form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
                     })

        action = self.cgi_form.getvalue('action')
        if not action:
            action = 'upload'

        # UID
        self.post_uid = self.get_params('UPLOAD-SERVER-USER')
        # TOKEN
        self.post_token = self.get_params('UPLOAD-SERVER-TOKEN')
        # REQUEST DATE
        self.post_date = self.get_params('UPLOAD-SERVER-DATE')
        # REQUEST NOTIFY URL
        self.post_notify_url = self.get_params('UPLOAD-SERVER-NOTIFY-URL')

        if 'upload' == action:
            self.on_upload_file()
        elif 'delete' == action:
            self.on_remove_file()
        elif 'download_zip' == action:
            self.on_zip_file()

    def get_params(self, key):
        if key in self.headers:
            return self.headers[key]
        return self.cgi_form.getvalue(key)


httpd = HTTPServer(('127.0.0.1', 8000), UploadServer)
print("Server started on 127.0.0.1,port 8000.....")
httpd.serve_forever()
