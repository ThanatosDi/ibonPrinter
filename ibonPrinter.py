import os

import requests


class IBON(object):

    def __init__(self):
        self.__iboneHostUrl = 'https://printadmin.ibon.com.tw/IbonUpload'
        pass

    def request(self, method, url, data, headers={'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'}, *args, **kwargs):
        with requests.request(method, url, data=data, headers=headers, timeout=10, *args, **kwargs) as request:
            return request.json()

    def result(self, response):
        if response['ResultCode'] == '00':
            return response
        return None

    @property
    def hash(self):
        endpoint = f'{self.__iboneHostUrl}/IbonUpload/FileUpload'
        headers = {
            'Content-Type': "application/json",
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36'
        }
        payload = "{'hash': ''}"
        response = self.request(
            "POST", endpoint, data=payload, headers=headers)
        if self.result(response):
            self._hash = response['Hash']
            return self._hash
        raise self.RequestError("Could not get hash.")

    def get_pincode(self, user, email):
        endpoint = f'{self.__iboneHostUrl}/IbonUpload/IbonFileUpload'
        payload = {
            'hash': self._hash,
            'user': user,
            'email': email
        }
        response = self.request('post', endpoint, data=payload)
        if self.result(response):
            return response
        raise self.RequestError('Could not get pincode.')

    def upload(self, file, user=' ', email=' '):
        endpoint = f'{self.__iboneHostUrl}/IbonUpload/LocalFileUpload'
        file_rb = {'file': (os.path.basename(file), open(file, 'rb'))}
        payload = {
            'fileName': os.path.basename(file),
            'hash': self.hash
        }
        response = self.request('post', endpoint, data=payload, files=file_rb)
        if self.result(response):
            return self.get_pincode(user, email)
        else:
            raise self.RequestError(response['Message'])

    class RequestError(Exception):
        pass
