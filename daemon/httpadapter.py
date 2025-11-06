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
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>` 
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()

    def handle_client(self, conn, addr, routes):
        """
        Handle an incoming client connection.

        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param conn (socket): The client socket connection.
        :param addr (tuple): The client's address.
        :param routes (dict): The route mapping for dispatching requests.
        """

        # Connection handler.
        self.conn = conn        
        # Connection address.
        self.connaddr = addr
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        # Read request (simple loop to attempt reading header+body)
        data = b''
        try:
            # read first chunk
            chunk = conn.recv(4096)
            data += chunk
            # if headers indicate a body, try to read remaining bytes
            # quick parse to find Content-Length
            hdr_end = data.find(b'\r\n\r\n')
            if hdr_end != -1:
                headers_blob = data[:hdr_end].decode(errors='ignore')
                # attempt to find content-length
                cl = 0
                for line in headers_blob.split('\r\n'):
                    if ':' in line:
                        k, v = line.split(':', 1)
                        if k.strip().lower() == 'content-length':
                            try:
                                cl = int(v.strip())
                            except Exception:
                                cl = 0
                            break
                body_len = len(data) - (hdr_end + 4)
                to_read = cl - body_len
                while to_read > 0:
                    more = conn.recv(4096)
                    if not more:
                        break
                    data += more
                    to_read -= len(more)
        except Exception:
            conn.close()
            return

        try:
            raw = data.decode('utf-8', errors='ignore')
        except Exception:
            raw = ''

        req.prepare(raw, routes)

        method = (req.method or '').upper()
        path = req.path or ''

        # Handle CORS preflight OPTIONS requests early
        if method == 'OPTIONS':
            r = Response()
            r.status_code = 200
            r.reason = 'OK'
            r.headers['Access-Control-Allow-Origin'] = '*'
            r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            conn.sendall(r.build_response_header(req))
            conn.close()
            return

        # # Task 1B: protect index
        if path == '/' or path == '/index.html':
            auth = getattr(req, 'cookies', {}) or {}
            if auth.get('auth') != 'true':
                r = Response()
                conn.sendall(r.build_unauthorized())
                conn.close()
                return

        # Task 1A: POST /login
        if method == 'POST' and path.rstrip('/') == '/login':
            form = getattr(req, 'form', {}) or {}
            username = form.get('username', '')
            password = form.get('password', '')
            r = Response()
            if username == 'admin' and password == 'password':
                r.status_code = 200
                r.reason = 'OK'
                base_dir = r.prepare_content_type(mime_type='text/html')
                c_len, content = r.build_content('/index.html', base_dir)
                r._content = content
                # set cookie
                r.cookies = {'auth': 'true'}
                # allow cross-origin access for tracker clients
                r.headers['Access-Control-Allow-Origin'] = '*'
                hdr = r.build_response_header(req)
                conn.sendall(hdr + r._content)
                conn.close()
                return
            else:
                conn.sendall(r.build_unauthorized())
                conn.close()
                return

        # App hook
        if req.hook:
            try:
                result = req.hook(headers=req.headers, body=getattr(req, 'body', None))
                if isinstance(result, (str, bytes)):
                    if isinstance(result, str):
                        result = result.encode('utf-8')
                    r = Response()
                    r.status_code = 200
                    r.reason = 'OK'
                    r._content = result
                    r.headers['Content-Type'] = 'application/json'
                    # allow CORS for API endpoints
                    r.headers['Access-Control-Allow-Origin'] = '*'
                    r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                    conn.sendall(r.build_response_header(req) + r._content)
                    conn.close()
                    return
            except Exception as e:
                print('[HttpAdapter] hook error: {}'.format(e))

        # Default static handling
        response = resp.build_response(req)
        conn.sendall(response)
        conn.close()

    def extract_cookies(self, req, resp=None):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :param resp: (Response) The res:class:`Response <Response>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        # Request.prepare already parses cookies into req.cookies
        return getattr(req, 'cookies', {})

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object 

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        # Create a minimal Response wrapper
        response = Response()
        response.encoding = 'utf-8'
        response.raw = resp
        response.reason = getattr(resp, 'reason', None) if resp else None
        response.url = getattr(req, 'url', None)
        response.cookies = getattr(req, 'cookies', {})
        response.request = req
        response.connection = self
        return response

    # def get_connection(self, url, proxies=None):
        # """Returns a url connection for the given URL. 

        # :param url: The URL to connect to.
        # :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        # :rtype: int
        # """

        # proxy = select_proxy(url, proxies)

        # if proxy:
            # proxy = prepend_scheme_if_needed(proxy, "http")
            # proxy_url = parse_url(proxy)
            # if not proxy_url.host:
                # raise InvalidProxyURL(
                    # "Please check proxy URL. It is malformed "
                    # "and could be missing the host."
                # )
            # proxy_manager = self.proxy_manager_for(proxy)
            # conn = proxy_manager.connection_from_url(url)
        # else:
            # # Only scheme should be lower case
            # parsed = urlparse(url)
            # url = parsed.geturl()
            # conn = self.poolmanager.connection_from_url(url)

        # return conn


    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.

        
        :param request: :class:`Request <Request>` to add headers to.
        """
        pass

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        username, password = ("user1", "password")

        if username:
            headers["Proxy-Authorization"] = (username, password)

        return headers