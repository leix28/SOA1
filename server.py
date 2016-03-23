# encoding: utf-8

CLIENT_ID = '2869478286'
CLIENT_SECRET = '6ee8bcede254b9966ee84c5144022cdb'
TENCENT_SECRETID = 'AKIDqIVL3LqtftH97cnkzbdFHw2VY3SLPRbQ'
TENCENT_SECRETKEY = 'ZSG9wtIInoVIke4P3DPh8lwOuKvI7Ftf'
SESSION_KEY = 'Baf-GYU-YU1-40A'
URL = 'app.citr.me/'
DATABASE = 'data.db'

'''
TABLE weibo
(
    id text (userid)
    wid text (postid)
    data text (weibo content)
    time text (weibo time)
)
TABLE user
(
    id text (userid)
    data text (feeling)
    nick text (nick name)
)
'''

from flask import Flask, render_template, redirect, request, session, escape, g
import hmac, hashlib, binascii
import time
import requests
import json
import sqlite3

app = Flask(__name__)
app.secret_key = SESSION_KEY

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def genTencentSign(params, requestHost='wenzhi.api.qcloud.com', requestUri='/v2/index.php', method = 'POST'):
    list = {}
    for param_key in params:
        if method == 'post' and str(params[param_key])[0:1] == "@":
            continue
        list[param_key] = params[param_key]
    srcStr = method.upper() + requestHost + requestUri + '?' + "&".join(k.replace("_",".") + "=" + str(list[k]) for k in sorted(list.keys()))
    hashed = hmac.new(TENCENT_SECRETKEY, srcStr, hashlib.sha1)
    return binascii.b2a_base64(hashed.digest())[:-1]

@app.route('/error')
def err():
    return 'Failed.'

@app.route('/')
def index():
    if 'expire' in session and session['expire'] < time.time():
        return redirect('/proc')
    return render_template('index.html')

@app.route('/login')
def login():
    return redirect('https://api.weibo.com/oauth2/authorize?client_id=%s&response_type=code&redirect_uri=%s' % (CLIENT_ID, URL + 'auth'))

@app.route('/auth')
def auth():
    args = request.args
    if 'code' in args:
        user =  requests.post('https://api.weibo.com/oauth2/access_token?client_id=%s&client_secret=%s&grant_type=authorization_code&redirect_uri=%s&code=%s' % (CLIENT_ID, CLIENT_SECRET, URL + 'auth', args.get('code'))).content
        user = json.loads(user)
        session['uid'] = user['uid']
        session['token'] = user['access_token']
        session['expire'] = int(time.time()) + int(user['expires_in']) - 60
        return redirect('/proc')
    return redirect('/')

@app.route('/proc')
def proc():
    # if 'last' in session and session['last'] + 300 <= time.time():
    #     return redirect('/show')
    # session['last'] = time.time()

    data = requests.get('https://api.weibo.com/2/statuses/user_timeline.json?access_token=%s'%session['token']).content
    decoded = json.loads(data)
    db = get_db()

    cattxt = u'中立'
    for item in decoded['statuses']:
        cattxt += item['text']
        idx = str(item['id'])
        cur = db.execute('SELECT COUNT(*) FROM weibo WHERE wid = ?', (idx, ))
        cnt = cur.fetchone()
        if (cnt[0] != 0):
            continue
        cur = db.execute('INSERT INTO weibo VALUES (?, ?, ?, ?)', (session['uid'], idx, item['text'], item['created_at']))

    data = requests.get('https://api.weibo.com/2/users/show.json?access_token=%s&uid=%s'%(session['token'], session['uid'])).content
    nick = json.loads(data)['screen_name']

    param = {
        'Action':'TextSentiment',
        'Nonce':0,
        'Region':'sgp',
        'SecretId':TENCENT_SECRETID,
        'Timestamp':int(time.time()),
        'content':cattxt.encode('utf8')
    }
    param['Signature'] = genTencentSign(param)
    data = requests.post('https://wenzhi.api.qcloud.com/v2/index.php', data=param)

    cur = db.execute('DELETE FROM user where id = ?', (session['uid'], ))
    cur = db.execute('INSERT INTO user VALUES (?, ?, ?)', (session['uid'], data.content, nick))
    db.commit()
    cur.close()
    return redirect('/show')

@app.route('/show')
def show():
    db = get_db()
    cur = db.execute('SELECT * from user where id = ?', (session['uid'], ))
    user = cur.fetchone()
    cur = db.execute('SELECT data from weibo where id = ?', (session['uid'], ))
    rv = cur.fetchall()
    cur.close()
    idx = []
    rv = map(lambda x: x[0], rv)
    posneg = json.loads(user[1])
    pos = "%.1f" % (float(posneg['positive']) * 100)
    neg = "%.1f" % (float(posneg['negative']) * 100)
    for i in xrange(len(rv)):
        idx.append(i % 2)
    return render_template('show.html', pos=pos, neg=neg, nick=user[2], items = zip(idx, rv))

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/users')
def getusers():
    db = get_db()
    cur = db.execute('SELECT (id) from user')
    user = cur.fetchall()
    cur.close()
    user = map(lambda x: x[0], user)
    data = {'users':user}
    return json.dumps(data)

@app.route('/posts/<uid>')
def getposts(uid):
    db = get_db()
    cur = db.execute('SELECT (data) from weibo where id = ?', (uid, ))
    weibo = cur.fetchall()
    cur.close()
    weibo = map(lambda x: x[0], weibo)
    data = {'uid':uid,'posts':weibo}
    return json.dumps(data)

@app.route('/emotion/<uid>')
def getemotion(uid):
    db = get_db()
    cur = db.execute('SELECT (data) from user where id = ?', (uid, ))
    user = cur.fetchone()
    cur.close()

    if (user == None):
        return json.dumps({"ERROR":"UID invalid"})

    posneg = json.loads(user[0])
    pos = "%.1f" % (float(posneg['positive']) * 100)
    neg = "%.1f" % (float(posneg['negative']) * 100)

    return json.dumps({'uid':uid, 'positive':pos, 'negative':neg})


if __name__ == '__main__':

    app.run(host="0.0.0.0", port=80)
