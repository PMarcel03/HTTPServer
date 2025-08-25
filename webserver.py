#HTTP Server Python
import socket
import os
import io
import sys
import urllib.parse 
import errno
import signal


#Import Flask App
from app import app as flask_app
#Import Router
from router import get_router


class http_server_program:
    """
    This class implements a basic HTTP web server. It serves files from the HTML directory
    """

    #TCP Socket Listener
    def __init__(self, host='0.0.0.0', port=8888, web_root='HTML'):
        """
        Initializes the server's state and creates the listening socket.
        """
        self.host = host
        self.port = port
        self.web_root = web_root
        
        # Create, configure, and bind the server socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))

        #Return Headers Set By Web Framework/Web App
        self.headers_set = []

        #Set Server name and port for Environ dictionary
        self.server_name = self.host
        self.server_port = self.port
        self.custom_router = get_router()

    def set_app(self,application):
        self.application= application

    def grim_reaper(self, signum, frame):
        """
        Signal handler to clean up zombie child processes
        uses waitpid with WNOHANG to handle multiple simultaneous child exits
        """
        while True:
            try:
                pid , status = os.waitpid(
                    -1, #Wait for any child process
                    os.WNOHANG #Don't block, return immediately if no zombies
                )
            except OSError:
                #No more child processes to wait for
                return
            if pid == 0: #No more zombies to clean up
                return

   #TCP Socket Listener
    def serve_forever(self):
        """
        Concurrent server loop that forks child processes to handle requests
        """

        self.socket.listen(1024)
        print(f'Serving HTTP on {self.host}:{self.port} ...')
        print(f'Parent PID: {os.getpid()}')
        print (f'Web Root Directory: {os.path.abspath(self.web_root)}')

        #Set up signal handler for cleaning up zombie processes
        signal.signal(signal.SIGCHLD, self.grim_reaper)

        while True:
            try:
                #Wait for client connections
                client_connection, client_address = self.socket.accept()
                print (f"Accepted Connection From: {client_address}")
            
            except IOError as e:
                code, msg = e.args
                #Restart accept() if it was interrupted by a signal
                if code == errno.EINTR:
                    continue
                else:
                    raise

            #Fork a child process to handle this client
            pid = os.fork()

            if pid == 0: #Child process
                #Child doesn't need listening socket
                self.socket.close()

                #Handle the client's request
                self.handle_request(client_connection)

                #Close client connection and exit
                client_connection.close()
                os._exit(0) #Child exits here

            else: #Parent Process
                #Parent doesn't need client connection
                #Child process will handle it
                client_connection.close()
                #Loop back to accept() for next client

            

    def handle_request(self, connection):
        """
        Receives, Parses and responds to a single client's HTTP request
        This runs in a child process for each request
        """
        try:
            # Store connection as instance variable (like your original code)
            self.client_connection = connection
            
            # Get the client request - read more data if needed
            request_data = connection.recv(4096).decode('utf-8')
            self.request_data = request_data
            
            print(f"Child PID {os.getpid()} handling request:")
            print("---Request Start---")
            print(request_data.strip()[:200] + "..." if len(request_data.strip()) > 200 else request_data.strip())
            print("---Request End---")

            if not request_data.strip():
                print("Empty request received")
                return

            self.parse_request(request_data)

            #Check with custom router first
            handler, variables = self.custom_router.dispatch(self.path, self.request_method)

            if handler:
                #Custom Router found a route, call its handler
                response_data = handler(variables)
                self.start_response(response_data['status'],response_data['headers'])
                self.finish_response([response_data['body']])
            else:
                #No Match with custom router, so let Flask app handle it
                # Construct environment dictionary using request data
                env = self.get_environ()
                # Call Application (Flask)
                result = self.application(env, self.start_response)
                self.finish_response(result)

            
        except ValueError as e:
            print(f"Parsing error in child process {os.getpid()}: {e}")
            self.send_error_response(connection, "400 Bad Request", str(e))
        except Exception as e:
            print(f"Error in child process {os.getpid()}: {e}")
            self.send_error_response(connection, "500 Internal Server Error", "Internal Server Error")

    def send_error_response(self, connection, status, message):
        """Send a simple error response"""
        try:
            error_response = f"HTTP/1.1 {status}\r\nContent-Type: text/plain\r\nContent-Length: {len(message)}\r\n\r\n{message}"
            connection.sendall(error_response.encode('utf-8'))
        except (socket.error, BrokenPipeError) as e:
            print(f"Failed to send error response due to a broken pipe or socket error: {e}")

    def parse_request(self, text):
        """Enhanced HTTP parsing with headers and query string support"""
        if not text or not text.strip():
            raise ValueError("Empty request")
            
        lines = text.splitlines()
        if not lines:
            raise ValueError("No request line found")
        
        # Parse request line (first line)
        request_line = lines[0].rstrip('\r\n')
        parts = request_line.split()
        
        if len(parts) < 2:
            raise ValueError(f"Invalid request line: {request_line}")
        elif len(parts) == 2:
            # Handle case where HTTP version might be missing
            self.request_method, full_path = parts
            self.request_version = 'HTTP/1.0'  # Default version
        else:
            # Normal case with method, path, and version
            self.request_method, full_path, self.request_version = parts[0], parts[1], parts[2]
        
        # Parse path and query string
        if '?' in full_path:
            self.path, self.query_string = full_path.split('?', 1)
        else:
            self.path = full_path
            self.query_string = ''
        
        # Parse HTTP headers
        self.headers = {}
        for line in lines[1:]:
            line = line.strip()
            if line and ':' in line:
                name, value = line.split(':', 1)
                self.headers[name.strip().lower()] = value.strip()
            elif not line:  # Empty line indicates end of headers
                break
        
        # Get content length for POST requests
        self.content_length = int(self.headers.get('content-length', '0'))
            
    def get_environ(self):
        env = {}
        #Required WSGI Variables
        env['wsgi.version'] = (1, 0)
        env['wsgi.url_scheme'] = 'http'
        env['wsgi.input'] = io.StringIO(self.request_data)
        env['wsgi.errors'] = sys.stderr
        env['wsgi.multithread'] = False
        env['wsgi.multiprocess'] = False
        env['wsgi.run_once'] = False
        #Required CGI Variables
        env['REQUEST_METHOD'] = self.request_method #GET
        env['PATH_INFO'] = urllib.parse.unquote(self.path) #/hello (URL Decoded)
        env['QUERY_STRING'] = self.query_string #Add query string
        env['SERVER_NAME'] = self.server_name #LocalHost
        env['SERVER_PORT'] = str(self.server_port) #8888
        
        #Add content-related variables
        if self.content_length > 0:
            env['CONTENT_LENGTH'] = str(self.content_length)
        if 'content-type' in self.headers:
            env['CONTENT_TYPE'] = self.headers['content-type']

        #Add HTTP headers to enviroment
        for name, value in self.headers.items():
            cgi_name = 'HTTP_' + name.upper().replace('-','_')
            env[cgi_name] = value


        return env
    
    def start_response(self,status,response_headers, exc_info=None):
        #Add Necessary Server Headers
        server_headers = [
            ('Date', 'Mon, 06 August 10:45:01 NZST'),
            ('Server','WSGIServer 0.2')
        ]
        self.headers_set = [status, response_headers + server_headers]
        #To Adhere to WSGI Standards we must return a 'Write' callable this will be ignored for now
        return self.finish_response 


    def finish_response(self, result):
        """Send the complete HTTP response"""
        try:
            status, response_headers = self.headers_set
            response = f'HTTP/1.1 {status}\r\n'
            
            for header in response_headers:
                response += '{0}: {1}\r\n'.format(*header)
            response += '\r\n'
            
            # Send headers
            self.client_connection.sendall(response.encode('utf-8'))
            
            # Send response body
            for data in result:
                if isinstance(data, str):
                    data = data.encode('utf-8')
                self.client_connection.sendall(data)
                
        except (socket.error, BrokenPipeError) as e:
            #Handle broken pipe errors more gracefully
            print(f"Error sending response due to a broken pipe or socket error {os.getpid()}: {e}")

def make_server(server_address, application):
    host, port = server_address
    server = http_server_program(host, port)
    server.set_app(application)
    return server


SERVER_ADDRESS = (HOST, PORT) = '', 8888

if __name__ == '__main__':
 #Create and start server
 httpd = make_server(SERVER_ADDRESS, flask_app)
 print(f'WSGIServer: Serving HTTP on port {PORT}... \n')

 try:
    httpd.serve_forever()
 except:
     print('\nServer Stopped')