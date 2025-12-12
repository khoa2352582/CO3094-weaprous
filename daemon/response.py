
import datetime
import os
import mimetypes
from .dictionary import CaseInsensitiveDict
from datetime import timezone
import pathlib

# Make BASE_DIR the project root (parent of daemon/). This ensures we
# resolve static/www paths to absolute locations so file lookups work
# regardless of current working directory.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) + os.sep

class Response():   
    """
    :attrs status_code (int): HTTP status code (e.g., 200, 404).
    :attrs headers (dict): dictionary of response headers.
    :attrs url (str): url of the response.
    :attrsencoding (str): encoding used for decoding response content.
    :attrs history (list): list of previous Response objects (for redirects).
    :attrs reason (str): textual reason for the status code (e.g., "OK", "Not Found").
    :attrs cookies (CaseInsensitiveDict): response cookies.
    :attrs elapsed (datetime.timedelta): time taken to complete the request.
    :attrs request (PreparedRequest): the original request object.
    """

    __attrs__ = [
        "_content",
        "_header",
        "status_code",
        "method",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
        "body",
        "reason",
    ]


    def __init__(self, request=None):
        self._content = False
        self._content_consumed = False
        self._next = None

        #: Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code = None

        #: Case-insensitive Dictionary of Response Headers.
        #: For example, ``headers['content-type']`` will return the
        #: value of a ``'Content-Type'`` response header.
        self.headers = {}

        #: URL location of Response.
        self.url = None

        #: Encoding to decode with when accessing response text.
        self.encoding = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request.
        self.history = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason = None

        #: A of Cookies the response headers.
        self.cookies = CaseInsensitiveDict()

        #: The amount of time elapsed between sending the request
        self.elapsed = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request = None


    def get_mime_type(self, path):
        #rtype: MIME type string (e.g., 'text/html', 'image/png').
        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return 'application/octet-stream'
        return mime_type or 'application/octet-stream'


    def prepare_content_type(self, mime_type='text/html'):
        base_dir = ""
        main_type, sub_type = mime_type.split('/', 1)
        print("[Response] processing MIME main_type={} sub_type={}".format(main_type,sub_type))
        if main_type == 'text':
            self.headers['Content-Type']='text/{}'.format(sub_type)
            if sub_type == 'plain' or sub_type == 'css':
                base_dir = os.path.join(BASE_DIR, "static") + os.sep
            elif sub_type == 'html':
                base_dir = os.path.join(BASE_DIR, "www") + os.sep
            else:
                # Fallback for other text types
                base_dir = os.path.join(BASE_DIR, "static") + os.sep
        elif main_type == 'image':
            base_dir = os.path.join(BASE_DIR, "static") + os.sep
            self.headers['Content-Type']='image/{}'.format(sub_type)
        elif main_type == 'application': #application/javascript (.js)
            if sub_type == 'javascript':
                base_dir = os.path.join(BASE_DIR, "static") + os.sep
                self.headers['Content-Type']='application/javascript'
            else:
                base_dir = os.path.join(BASE_DIR, "apps") + os.sep
                self.headers['Content-Type']='application/{}'.format(sub_type)    
        elif main_type == 'video':
            base_dir = os.path.join(BASE_DIR, "static") + os.sep
            self.headers['Content-Type']='video/{}'.format(sub_type)
        else:
            raise ValueError("Invalid MIME type: main_type={} sub_type={}".format(main_type,sub_type))

        return base_dir


    def build_content(self, path, base_dir):
        #path (str) "/index.html" or "/static/images/welcome.png"
        #base_dir (str) "www/" or "static/"
        #rtype (int, byte)
        # Normalize and construct an absolute filepath. Accept incoming
        # `path` values that may already include a leading folder like
        # "static/". We treat base_dir as absolute (it is built from
        # BASE_DIR above) and join it with a cleaned relative path.
        clean_path = path.lstrip('/\\')

        # If the client requested a path that already starts with the base
        # directory name (for example path '/static/images/x.png' and
        # base_dir ends with '.../static/'), strip the leading folder so we
        # don't end up duplicating it.
        # Normalize separators and case for comparison (Windows case-insensitive)
        clean_path_normalized = clean_path.replace('/', os.sep).lstrip(os.sep)
        base_dir_norm = os.path.normpath(base_dir)
        base_dir_name = base_dir_norm.rstrip(os.sep).split(os.sep)[-1] if base_dir_norm else ''

        # Case-insensitive comparison on platforms that need it
        if base_dir_name:
            if os.path.normcase(clean_path_normalized).startswith(os.path.normcase(base_dir_name + os.sep)):
                rel = clean_path_normalized[len(base_dir_name) + 1:]
            elif os.path.normcase(clean_path_normalized) == os.path.normcase(base_dir_name):
                rel = ""
            else:
                rel = clean_path_normalized
        else:
            rel = clean_path_normalized

        filepath = os.path.normpath(os.path.join(base_dir, rel))

        print("[Response] DEBUG: path='{}' base_dir='{}' filepath='{}'".format(path, base_dir, filepath))
        print("[Response] serving the object at location {}".format(filepath))

        try:
            with open(filepath, 'rb') as f:  # read binary
                content = f.read()
            return len(content), content
        except (IOError, FileNotFoundError):
            print("[Response] Error: File not found at {}".format(filepath))
            return 0, b""


    def build_response_header(self, request):
        """
        :request (Request) 
        :rtypes (bytes) -  encoded HTTP response header.
        """
        reqhdr = request.headers
        rsphdr = self.headers

        headers = {
                # "Accept": "{}".format(reqhdr.get("Accept", "application/json")),
                # "Accept-Language": "{}".format(reqhdr.get("Accept-Language", "en-US,en;q=0.9")),
                # "Authorization": "{}".format(reqhdr.get("Authorization", "Basic <credentials>")),
                "Cache-Control": "no-cache",
                "Content-Type": "{}".format(self.headers['Content-Type']),
                "Content-Length": "{}".format(len(self._content)),
#                "Cookie": "{}".format(reqhdr.get("Cookie", "sessionid=xyz789")), #dummy cooki
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
                "Date": "{}".format(datetime.datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")),                "Max-Forward": "10",
                "Pragma": "no-cache",
                # "Proxy-Authorization": "Basic dXNlcjpwYXNz", 
                # "Warning": "199 Miscellaneous warning",
                # "User-Agent": "{}".format(reqhdr.get("User-Agent", "Chrome/123.0.0.0")),
                "Connection": "close",
            }
        headers.update(rsphdr)
        status_line = "HTTP/1.1 {} {}\r\n".format(self.status_code, self.reason) #HTTP/1.1 200 OK
        # Header text alignment
        header_lines = []
        for key, value in headers.items():
            header_lines.append("{}: {}\r\n".format(key, value))
        
        # ============================================
        # TEAM IMPLEMENTATION: Set-Cookie Header Support
        # Add Set-Cookie headers for session management
        # ============================================
        try:
            if isinstance(self.cookies, dict):
                for k, v in self.cookies.items():
                    # Set-Cookie format with security flags
                    header_lines.append('Set-Cookie: {}={}; Path=/\r\n'.format(k, v))
        except Exception:
            pass

        
        all_headers_string = "".join(header_lines)
        
        fmt_header = status_line + all_headers_string + "\r\n"
        return fmt_header.encode('utf-8')

    # ============================================
    # TEAM IMPLEMENTATION: HTTP Error Responses
    # ============================================
    
    def build_notfound(self):
        """
        Constructs a standard 404 Not Found HTTP response.
        
        :rtype bytes: Encoded 404 response.
        """
        return (
                "HTTP/1.1 404 Not Found\r\n"
                "Accept-Ranges: bytes\r\n"
                "Content-Type: text/html\r\n"
                "Content-Length: 13\r\n"
                "Cache-Control: max-age=86000\r\n"
                "Connection: close\r\n"
                "\r\n"
                "404 Not Found"
            ).encode('utf-8')
        
    def build_unauthorized(self):
        """
        Constructs a standard 401 Unauthorized HTTP response.
        Used for authentication failures (Task 1A, 1B).
        
        :rtype bytes: Encoded 401 response.
        """
        return (
                "HTTP/1.1 401 Unauthorized\r\n"
                "Content-Type: text/html\r\n"
                "Content-Length: 16\r\n"
                "Connection: close\r\n"
                "\r\n"
                "401 Unauthorized"
            ).encode('utf-8')


    ########################################### Main function #################################
    def build_response(self, request):
        path = request.path

        mime_type = self.get_mime_type(path)
        print("[Response] {} path {} mime_type {}".format(request.method, request.path, mime_type))

        base_dir = ""

        if path.endswith('.html') or mime_type == 'text/html':
            base_dir = self.prepare_content_type(mime_type = 'text/html')
        elif mime_type == 'text/css':
            base_dir = self.prepare_content_type(mime_type = 'text/css')
        elif mime_type == 'application/javascript':
            base_dir = self.prepare_content_type(mime_type = 'application/javascript')
        elif mime_type and mime_type.startswith('image/'):
            # Handle image files (png, jpg, ico, etc.)
            base_dir = self.prepare_content_type(mime_type = mime_type)
        else:
            return self.build_notfound()

        c_len, self._content = self.build_content(path, base_dir)

        # If content length is zero assume file not found and return 404
        if c_len == 0:
            return self.build_notfound()

        self._header = self.build_response_header(request)
        return self._header + self._content