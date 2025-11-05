#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist 
request settings (cookies, auth, proxies).
"""
from .dictionary import CaseInsensitiveDict
from urllib.parse import parse_qs
import base64

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import deamon.request
      >>> req = request.Request()
      ## Incoming message obtain aka. incoming_msg
      >>> r = req.prepare(incoming_msg)
      >>> r
      <Request>
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        #: HTTP path
        self.path = None        
        # The cookies set used to create Cookie header
        self.cookies = None
        #: request body to send to the server.
        self.body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None

    def extract_request_line(self, request):
        try:
            # Only inspect the request start-line (first line)
            lines = request.splitlines()
            if not lines:
                return None, None, None
            first_line = lines[0]
            parts = first_line.split()
            if len(parts) < 3:
                return None, None, None
            method, path, version = parts[0], parts[1], parts[2]

            if path == '/':
                path = '/index.html'
        except Exception:
            return None, None, None

        return method, path, version
             
    def prepare_headers(self, request):
        """Prepares the given HTTP headers."""
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.lower()] = val
        return headers

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters."""

        # Prepare the request line from the request header
        # split headers and body
        hdr_part = request
        body_part = ''
        if '\r\n\r\n' in request:
            hdr_part, body_part = request.split('\r\n\r\n', 1)

        self.method, self.path, self.version = self.extract_request_line(hdr_part)
        if self.method:
            self.method = self.method.upper()
        print("[Request] {} path {} version {}".format(self.method, self.path, self.version))

    # @bksysnet Preparing the webapp hook with WeApRous instance
    # The default behaviour with HTTP server is empty routed
        
        # Manage webapp hook (WeApRous) if routes provided
        if routes:
            self.routes = routes
            # routes for WeApRous are keyed by (METHOD, path)
            self.hook = routes.get((self.method, self.path))
            # self.hook manipulation goes here if needed

        # prepare headers from header section
        self.headers = self.prepare_headers(hdr_part)

        # parse cookies into dict
        cookie_hdr = self.headers.get('cookie', '')
        cookies = {}
        if cookie_hdr:
            for pair in cookie_hdr.split(';'):
                pair = pair.strip()
                if not pair:
                    continue
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    cookies[k.strip()] = v.strip()
        self.cookies = cookies

        # derive url (Host header + path) if host present
        host = self.headers.get('host')
        if host:
            self.url = '{}{}'.format(host, self.path)
        else:
            self.url = self.path

        # prepare body if present
        if body_part:
            # try to detect content-type
            self.body = body_part
            self.prepare_body(body_part, files=None)

        return

    def prepare_body(self, data, files=None, json=None):
        """
        Prepare the request body. Accepts raw data and parses common formats.
        Currently supports application/x-www-form-urlencoded parsing into self.form.
        """
        # store raw body
        self.body = data

        # try to parse form-encoded body
        form = {}
        try:
            parsed = parse_qs(data, keep_blank_values=True)
            # flatten values
            form = {k: v[0] for k, v in parsed.items()}
        except Exception:
            form = {}

        self.form = form

        # update content-length header
        self.prepare_content_length(self.body)

        # placeholder: auth can be extracted from body if provided
        # self.auth = ...
        return


    def prepare_content_length(self, body):
        """Set Content-Length header based on provided body bytes/string."""
        if self.headers is None:
            self.headers = {}
        try:
            length = len(body.encode('utf-8')) if isinstance(body, str) else len(body)
        except Exception:
            length = 0
        # headers keys stored lowercased by prepare_headers
        self.headers["content-length"] = str(length)
        # placeholder for auth extraction
        # self.auth = ...
        return


    def prepare_auth(self, auth, url=""):
        """
        Prepare and normalize authentication information for the request.

        Accepts:
        - auth tuple (username, password)
        - auth string (e.g., 'Basic base64...')
        - None: will try to read from headers
        """
        if auth is None:
            # try Authorization header
            hdr = self.headers.get('authorization') if self.headers else None
            if hdr:
                if hdr.startswith('Basic '):
                    try:
                        b64 = hdr.split(' ', 1)[1]
                        decoded = base64.b64decode(b64).decode('utf-8')
                        if ':' in decoded:
                            user, pwd = decoded.split(':', 1)
                            self.auth = {'type': 'basic', 'username': user, 'password': pwd}
                            return self.auth
                    except Exception:
                        pass
            self.auth = None
            return None
        # if tuple provided
        if isinstance(auth, (list, tuple)) and len(auth) >= 2:
            user, pwd = auth[0], auth[1]
            self.auth = {'type': 'basic', 'username': user, 'password': pwd}
            return self.auth
        # if string provided and starts with Basic
        if isinstance(auth, str) and auth.startswith('Basic '):
            try:
                b64 = auth.split(' ', 1)[1]
                decoded = base64.b64decode(b64).decode('utf-8')
                if ':' in decoded:
                    user, pwd = decoded.split(':', 1)
                    self.auth = {'type': 'basic', 'username': user, 'password': pwd}
                    return self.auth
            except Exception:
                pass
        # fallback: store raw
        self.auth = auth
        return self.auth

    def prepare_cookies(self, cookies):
        """
        Prepare Cookie header from dict or string and store in self.cookies.
        """
        if isinstance(cookies, dict):
            cookie_str = '; '.join('{}={}'.format(k, v) for k, v in cookies.items())
        else:
            cookie_str = str(cookies)
        if self.headers is None:
            self.headers = {}
        # store lowercased header key to be consistent
        self.headers['cookie'] = cookie_str
        # also populate self.cookies dict
        parsed = {}
        for pair in cookie_str.split(';'):
            pair = pair.strip()
            if not pair:
                continue
            if '=' in pair:
                k, v = pair.split('=', 1)
                parsed[k.strip()] = v.strip()
        self.cookies = parsed
        return
