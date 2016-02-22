#!/usr/binenv python
#coding: utf-8

import httplib, urllib, base64
import os
import json

class LangModel(object):
    def __init__(self, model):
        self.model = model

    def get_request_header(self):
        key = os.getenv('WEBLM_KEY')
        if not key:
            raise Exception("Key not found. Set it in env: WEBLM_KEY")
        headers = {
            'Content-Type': 'application/json',
            'Ocp-Apim-Subscription-Key': key,
        }
        return headers

    def get_params(self):
        params = urllib.urlencode({
            'model': self.model
        })
        return params

    def get_body(self, phrases):
        b = {'queries' : phrases}
        print json.dumps(b)
        return json.dumps(b)

    def parse_result(self, result):
        jresult = json.loads(result)
        return dict([(each['words'], each['probability']) for each in jresult['results']])

    def get_jp(self, phrases):
        conn = httplib.HTTPSConnection('api.projectoxford.ai')
        conn.request("POST", "/text/weblm/v1.0/calculateJointProbability?%s" % self.get_params(), \
            self.get_body(phrases), self.get_request_header())
        response = conn.getresponse()
        data = response.read()
        ret = self.parse_result(data)
        return ret

if __name__ == '__main__':
    phrases = ['Artificial Universe', 'unstoppable']
    lm = LangModel('body')
    print lm.get_jp(phrases)
