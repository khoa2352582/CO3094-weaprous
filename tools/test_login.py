#!/usr/bin/env python3
"""Quick test script: POST /login then GET / to verify cookie-based auth."""
import urllib.request
import urllib.parse
import http.cookiejar

TRACKER = False
HOST = 'http://localhost:9000'

def main():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    data = urllib.parse.urlencode({'username':'admin','password':'password'}).encode('utf-8')
    req = urllib.request.Request(HOST + '/login', data=data, headers={
        'Content-Type':'application/x-www-form-urlencoded'
    })
    try:
        resp = opener.open(req, timeout=5)
        print('Login response:', resp.status)
        body = resp.read().decode('utf-8', errors='ignore')
        print(body[:200])
    except Exception as e:
        print('Login request failed:', e)
        return

    # now request index with stored cookies
    try:
        resp = opener.open(HOST + '/', timeout=5)
        print('GET / response:', resp.status)
        body = resp.read().decode('utf-8', errors='ignore')
        print(body[:400])
    except Exception as e:
        print('GET / failed:', e)

if __name__ == '__main__':
    main()
