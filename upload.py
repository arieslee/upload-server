#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests
import datetime
import hashlib

file_dir = '1.png'
file = open(file_dir, 'rb')
files = {'ATTACHMENT': (file_dir, file, 'image/png', {})}
date_str = datetime.datetime.now().strftime('%Y%m%d%H')
auth_key = 'k4Ao7KWVbvg3Z2L6KLwN9OoDjQL5SioJffIPoODATxCynuEVEAt0278kg7r9FHiS'
user_id = 'tester001'
token = 'uid:' + str(user_id) + '&secretkey:' + str(auth_key) + '&datetime:' + str(date_str)
hash_token = hashlib.md5(token.encode(encoding='UTF-8')).hexdigest()
headers = {
    'UPLOAD-SERVER-TOKEN': hash_token,
    'UPLOAD-SERVER-USER': user_id
}
r1 = requests.post('http://ar.upload.ming/upload', files=files, headers=headers)
print(r1.text)
file.close()