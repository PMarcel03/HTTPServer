# HTTP Server Python
import socket
import os
import sys
import errno
import json
import threading

# Import Router
from router import get_router

class http_server_program:
    """
    This class implements a basic HTTP web server. It serves files from the HTML directory
    """

    # TCP Socket Listener
    def __init__(self, host='0.0.0.0', port=8888, web_root=None):
        """
        Initializes the server's state and creates the listening socket.
        """
        self.host = host
        self.port = port
        
        if web_root is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.web_root = os.path.join(script_dir, 'HTML')
        else:
            self.web_root = web_root

        # Create, configure, and bind the server socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))

        # Return Headers Set By Web Framework/Web App (Unused Code: For Flask/WSGI compatibility)
        # self.headers_set = []

        # Set Server name and port for Environ dictionary
        self.server_name = self.host
        self.server_port = self.port
        self.custom_router = get_router()


    # TCP Socket Listener
    def serve_forever(self):
        """
            Concurrent server loop that uses threads to handle requests
            """
        self.socket.listen(1024)
        print(f'Serving HTTP on {self.host}:{self.port} ...')
        print(f'Main Thread: {threading.current_thread().name}')
        print(f'Web Root Directory: {os.path.abspath(self.web_root)}')
        print(f'HTTP/1.0 Compliant Server')
        print(f'Supported Methods: GET, HEAD, POST, PUT, DELETE, PATCH, OPTIONS')
        print(f'Using threading for concurrent requests')

        while True:
            try:
                client_connection, client_address = self.socket.accept()
                print(f"Accepted Connection From: {client_address}")
            except IOError as e:
                code, msg = e.args
                if code == errno.EINTR:
                    continue
                else:
                    raise

            # Create a thread to handle this client
            client_thread = threading.Thread(
                target=self.handle_client,
                args=(client_connection,),
                daemon=True
            )
            client_thread.start()

    def handle_client(self, connection):
        """Handle a single client connection in a separate thread"""
        try:
            self.handle_request(connection)
        finally:
            connection.close()

    def read_request_body(self, connection):
        """
        Read the complete request body based on Content-Length header
        Required for POST/PUT/DELETE requests with JSON bodies
        """
        if self.content_length <= 0:
            return ""
        
        #Start with any body data already recieved in inital recv
        body_data = getattr(self, 'initial_body_data', b"")
        remaining = self.content_length - len(body_data)

        # Read the body in chunks
        while remaining > 0:
            chunk = connection.recv(min(4096, remaining))
            if not chunk:
                break
            body_data += chunk
            remaining -= len(chunk)

        return body_data.decode('utf-8')

    def extract_json_body(self, body_data):
        """
        Extract and parse JSON from request body for POST/PUT methods
        returns parsed JSON object or none
        """
        if not body_data or not body_data.strip():
            return None
        try:
            return json.loads(body_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in request body: {str(e)}")

    def serve_html_file(self, file_path):
        """
        Serve a raw HTML file directly to the client.
        """
        full_path = os.path.join(self.web_root, file_path.lstrip('/'))

        # Security Check - ensures path is in web root
        if not os.path.abspath(full_path).startswith(os.path.abspath(self.web_root)):
            return self.format_json_error("403 Forbidden", "Access Denied")

        try:
            if os.path.isfile(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Use the new utility method
                return self.create_response(html_content, 'text/html')

            else:
                return self.format_json_error("404 Not Found", f"File Not found: {file_path}")
        except Exception as e:
            return self.format_json_error("500 Internal Server Error", f"Error reading file: {str(e)}")

    def format_json_response(self, data, status="200 OK"):
        """
        Format any data as a proper JSON HTTP response
        """
        json_body = json.dumps(data, indent=2, ensure_ascii=False)
        return self.create_response(json_body, 'application/json', status)

    def format_json_error(self, status, message):
        """
        Format error responses as JSON
        """
        error_data = {
            "success": False,
            "error": {
                "status": status,
                "message": message
            },
            "timestamp": self.get_timestamp()
        }

        return self.format_json_response(error_data, status)

    def get_timestamp(self):
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()

   

    def handle_request(self, connection):
        try:
            self.client_connection = connection
            #Read inital data - may contain headers + partial/full body
            request_data = connection.recv(8192)

            if not request_data.strip():
                print("Empty request received")
                return
            
            #Split headers and body at \r\n\r\n
            if b"\r\n\r\n" in request_data:
                header_data, body_data = request_data.split(b"\r\n\r\n", 1)
                request_text = header_data.decode('utf-8')
                #Store any body data we already recieved
                self.initial_body_data = body_data
            else:
                request_text = request_data.decode('utf-8')
                self.initial_body_data = b""

            self.parse_request(request_text)

            if self.request_version == 'HTTP/1.0' and 'host' not in self.headers:
                error_response = self.format_json_error("400 Bad Request", "HTTP/1.0 requires Host header")
                self.send_error_response(connection, error_response)
                return

            # Read JSON body for specific methods
            self.json_body = None
            if self.request_method in ['POST', 'PUT', 'PATCH', 'DELETE'] and self.content_length > 0:
                body_data = self.read_request_body(connection)
                try:
                    self.json_body = self.extract_json_body(body_data)
                except ValueError as e:
                    error_response = self.format_json_error("400 Bad Request", str(e))
                    self.send_error_response(connection, error_response)
                    return

            # Use a single variable to store the final response to be sent
            response_data = None

            # Check custom router first
            handler, variables = self.custom_router.dispatch(self.path, self.request_method)

            #Handle OPTIONS requests (HTTP/1.0 method discovery)
            if self.request_method == 'OPTIONS':
                #Check if it's an API Route
                handler, variables = self.custom_router.dispatch(self.path, 'GET')
                if handler:
                    #Find all methods for this route
                    allowed_methods = []
                    for route in self.custom_router.routes:
                        is_match, _ = self.custom_router._match_and_extract(self.path, route['pattern'])
                        if is_match:
                            allowed_methods.extend(route['methods'])
                    allowed_methods = list(set(allowed_methods + ['OPTIONS']))

                headers = [
                    ('Allow', ', '.join(sorted(allowed_methods))),
                    ('Content-Length', '0'),
                    ('Connection', 'close')
                ]

                response_data = {
                    'status': '200 OK',
                    'headers': headers,
                    'body': ''
                }
            else:
                #Static files or not found
                headers = [
                    ('Allow', 'GET, HEAD, OPTIONS'),
                    ('Content-Length', '0'),
                    ('Connection', 'close')
                ]
                response_data = {
                    'status': '200 OK',
                    'headers': headers,
                    'body': ''
                }

            if handler:
                # Custom router found a route; call its handler
                try:
                    #Pass method info and JSON body to handler
                    variables['_method'] = self.request_method
                    if 'json_body' in handler.__code__.co_varnames:
                        content, content_type, status = handler(variables, json_body=self.json_body)
                    else:
                        content, content_type, status = handler(variables)
                    
                    # Use the create_response utility to build the final response
                    response_data = self.create_response(content, content_type, status)

                except Exception as e:
                    response_data = self.format_json_error("500 Internal Server Error", f"Handler error: {str(e)}")

            # After checking the router, check for static files, etc.
            elif self.request_method in ['GET', 'HEAD']:
                # Handle static file requests, including HTML
                if self.path == '/':
                    response_data = self.serve_html_file('/index.html')
                elif '.' in self.path:
                    response_data = self.serve_html_file(self.path)
                else:
                    response_data = self.format_json_error("404 Not Found", f"No route found for {self.path}")
                #For HEAD requests, remove the body but keep headers
                if self.request_method == 'HEAD':
                    response_data['body'] = ''

            #Method not allowed for non-GET on static paths
            elif '.' in self.path or self.path =='/':
                error_data = {
                    "success": False,
                    "error": {
                        "status": "405 Method Not Allowed",
                        "message": f"Method {self.request_method} not allowed for static files" 
                    },
                    "timestamp": self.get_timestamp()
                }
                #HTTP/1.0 requires Allow header for 405 responses
                headers = [
                    ('Content-Type', 'application/json; charset=utf-8'),
                    ('Content-Length', str(len(json.dumps(error_data).encode('utf-8')))),
                    ('Allow', 'GET, HEAD'),
                    ('Connection', 'close')
                ]
                response_data = {
                    'status': '405 Method Not Allowed',
                    'headers': headers,
                    'body': json.dumps(error_data, indent=2)
                }
   

            else:
                # Fallback to Flask WSGI application (Unused code: For Flask/WSGI compatibility)
                # env = self.get_environ()
                # result = self.application(env, self.start_response)
                # self.finish_response(result)
                # return
                
                #No route found - return 404
                response_data = self.format_json_error("404 Not Found", f"No route found for {self.path}")

            # Send the unified response if a custom handler was found
            if response_data:
                self.send_response(connection, response_data)
               

        except ValueError as e:
            #Handle 501 Not Implemented vs 400 Bad Request
            error_msg = str(e)
            if "Method not implemented" in error_msg:
                error_response = self.format_json_error("501 Not Implemented", error_msg)
            else:
                error_response = self.format_json_error("400 Bad Request", error_msg)
            self.send_error_response(connection, error_response)

        except Exception as e:
            print(f"Server error: {e}")
            error_response = self.format_json_error("500 Internal Server Error", "Internal server error occurred")
            self.send_error_response(connection, error_response)

    def send_response(self, connection, response_data):
        """Unified response sending with proper HTTP version"""
        # Use request version if available, default to HTTP/1.0
        http_version = getattr(self, 'request_version', 'HTTP/1.0')
        if http_version not in ['HTTP/1.0', 'HTTP/1.0']:
            http_version = 'HTTP/1.0'
            
        response = f"{http_version} {response_data['status']}\r\n"
        for header in response_data['headers']:
            response += f"{header[0]}: {header[1]}\r\n"
        response += f"\r\n{response_data['body']}"
        connection.sendall(response.encode('utf-8'))


    def send_error_response(self, connection, response_data):
        """Send a JSON formatted error response"""
        try:
            #Use request version if avaliable
            http_version = getattr(self, 'request_version', 'HTTP/1.0')
            if http_version not in ['HTTP/1.0', 'HTTP/1.0']:
                http_version = 'HTTP/1.0'


            status = response_data['status']
            headers = response_data['headers']
            body = response_data['body']

            response = f"{http_version} {status}\r\n"
            for header in headers:
                response += f"{header[0]}: {header[1]}\r\n"
            response += f"\r\n{body}"

            connection.sendall(response.encode('utf-8'))
        except (socket.error, BrokenPipeError) as e:
            print(f"Failed to send error response {e}")

    def parse_request(self, text):
        """HTTP/1.0 Compliant request parsing with proper header handling"""
        if not text or not text.strip():
            raise ValueError("Empty request")

        lines = text.splitlines()
        if not lines:
            raise ValueError("No request line found")
        
        #Request parse line
        request_line = lines[0].rstrip('\r\n')
        parts = request_line.split()

        if len(parts) < 2:
            raise ValueError(f"Invalid request line: {request_line}")
        elif len(parts) == 2:
            #HTTP/0.9 style request (Method and path only)
            self.request_method, full_path = parts
            self.request_version = 'HTTP/1.0'
        else:
            self.request_method, full_path, self.request_version = parts[0], parts[1], parts[2]

        #Validate HTTP version
        if self.request_version not in ['HTTP/1.0', 'HTTP/1.0']:
            raise ValueError(f"unsupported HTTP version: {self.request_version}")
        
        #Validate HTTP method (Only support standard methods)
        valid_methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
        if self.request_method not in valid_methods:
            raise ValueError(f"Method not implemented: {self.request_method}")
        
        #Handle absolute URIs (HTTP/1.0 allows http://host/path format)
        if full_path.startswith('http://') or full_path.startswith('https://'):
            from urllib.parse import urlparse
            parsed = urlparse(full_path)
            full_path = parsed.path or '/'
            if parsed.query:
                full_path += '?' + parsed.query

        #Parse path and query string
        if '?' in full_path:
            self.path, self.query_string = full_path.split('?', 1)
        else:
            self.path = full_path
            self.query_string = ''

        #Parse headers
        self.headers = {}
        for line in lines[1:]:
            line = line.strip()
            if line and ':' in line:
                name, value = line.split(':', 1)
                self.headers[name.strip().lower()] = value.strip()
            elif not line:
                break

        self.content_length = int(self.headers.get('content-length', '0'))

#=============================================================================================================
# WSGI/FLASK COMPATIBILITY LAYER (UNUSED)                                                                   ||
# These methods were implemented to support Flask integration                                               ||
# but the final implementation uses a custom router instead.                                                ||
# Kept for reference and potential future WSGI support.                                                     ||
#=============================================================================================================
    # def get_environ(self):
    #     env = {}
    #     env['wsgi.version'] = (1, 0)
    #     env['wsgi.url_scheme'] = 'http'
    #     env['wsgi.input'] = io.StringIO(self.request_data)
    #     env['wsgi.errors'] = sys.stderr
    #     env['wsgi.multithread'] = False
    #     env['wsgi.multiprocess'] = True
    #     env['wsgi.run_once'] = False
    #     env['REQUEST_METHOD'] = self.request_method
    #     env['PATH_INFO'] = urllib.parse.unquote(self.path)
    #     env['QUERY_STRING'] = self.query_string
    #     env['SERVER_NAME'] = self.server_name
    #     env['SERVER_PORT'] = str(self.server_port)
    #     env['SERVER_PROTOCOL'] = self.request_version

    #     if self.content_length > 0:
    #         env['CONTENT_LENGTH'] = str(self.content_length)
    #     if 'content-type' in self.headers:
    #         env['CONTENT_TYPE'] = self.headers['content-type']

    #     #Add all HTTP headers to environ
    #     for name, value in self.headers.items():
    #         cgi_name = 'HTTP_' + name.upper().replace('-', '_')
    #         env[cgi_name] = value

    #     return env
    
    # def start_response(self, status, response_headers, exc_info=None):
    #     from datetime import datetime
    #     current_date = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')

    #     server_headers = [
    #         ('Date', current_date),
    #         ('Server', 'CustomHTTPServer/1.1'),
    #         ('Connection', 'close')
    #     ]

    #     self.headers_set = [status, response_headers + server_headers]
    #     return self.finish_response
    # 
    # #Send the complete HTTP response to client
    # def finish_response(self, result):
    #     try:
    #         status, response_headers = self.headers_set
    #         response = f'HTTP/1.0 {status}\r\n'

    #         for header in response_headers:
    #             response += '{0}: {1}\r\n'.format(*header)
    #         response += '\r\n'

    #         self.client_connection.sendall(response.encode('utf-8'))

    #         for data in result:
    #             if isinstance(data, str):
    #                 data = data.encode('utf-8')
    #             self.client_connection.sendall(data)

    #     except (socket.error, BrokenPipeError) as e:
    #         print(f"Error sending response due to a broken pipe or socket error {os.getpid()}: {e}")
#=============================================================================================================

       #Create HTTP/1.0 compliant response with proper headers
    def create_response(self, content, content_type, status='200 OK'):
        from datetime import datetime, timezone
        #RFC 1123 date format required by HTTP/1.0
        current_date = datetime.now(timezone.utc).strftime('%a %d %b %Y %H:%M:%S GMT')

        headers = [
            ('Date', current_date),
            ('Server', 'CustomHTTPServer/1.1'),
            ('Content-Type', f'{content_type}; charset=utf-8'),
            ('Content-Length', str(len(content.encode('utf-8')))),
            ('Connection', 'close') #HTTP/1.0 connection handling
        ]
        return {
            'status': status,
            'headers': headers,
            'body': content
        }

def make_server(server_address):
    #Factory function to create server instance
    host, port = server_address
    server = http_server_program(host, port)
    return server


SERVER_ADDRESS = (HOST, PORT) = '', 8888

if __name__ == '__main__':
    httpd = make_server(SERVER_ADDRESS)
    print(f'WSGIServer: Serving HTTP on port {PORT}... \n')

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n🛑 Server stopped by user (Ctrl +C)')
    except OSError as e:
        if e.errno == 48 or e.errno == 98: #Address already in use (MacOS/Linux)
            print(f'\n❌ Error: Port {PORT} is already in use')
            print(f'  Try a different pot or kill the process using: lsof -ti{PORT} | xargs kill')
        elif e.errno == 13: #Permission denied
            print(f'\n❌ Error: Permission denied on port {PORT}')
            print(f'    Ports below 1024 require root privileges (Try sudo or use port > 1024)')
        else:
            print(f'\n❌ Network error: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'\n ❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print('Shutting down server...')
        if 'httpd' in locals():
            httpd.socket.close()