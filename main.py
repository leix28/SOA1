# encoding: utf-8
import hmac, hashlib
import binascii, requests, json, time

TENCENT_SECRETID = 'AKIDqIVL3LqtftH97cnkzbdFHw2VY3SLPRbQ'
TENCENT_SECRETKEY = 'ZSG9wtIInoVIke4P3DPh8lwOuKvI7Ftf'

param = {
    'Action':'TextSentiment',
    'Nonce':0,
    'Region':'sgp',
    'SecretId':TENCENT_SECRETID,
    'Timestamp':int(time.time()),
    'content':'可恶'
}



sign = make('wenzhi.api.qcloud.com', '/v2/index.php', param)
print sign
param['Signature'] = sign
r = requests.get('https://wenzhi.api.qcloud.com/v2/index.php', params=param)
print r.url
data = json.loads(r.content)
print data
print data['message']
