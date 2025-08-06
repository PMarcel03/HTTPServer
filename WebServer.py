#HTTP Server Python
import socket
import os
import io
import sys

#Import Flask App
from app import app as flask_app

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

    def set_app(self,application):
        self.application= application

   #TCP Socket Listener
    def serve_forever(self):
        """
        Starts the main server loop, listening for and handling client connections
        """

        self.socket.listen(2)
        print(f'Serving HTTP on {self.host}:{self.port} ...')
        print (f'Web Root Directory: {os.path.abspath(self.web_root)}')

        while True:
            #Wait for client connections
            self.client_connection, client_address = self.socket.accept()
            print (f"Accepted Connection From: {client_address}")

            #Handle the client's request
            self.handle_request(self.client_connection)



    #HTTP Handler
    def handle_request(self, connection):
        """
        Receives, Parses and responses to a single client's HTTP request
        """
        #Get the client request
        request_data = connection.recv(1024).decode('utf-8')
        self.request_data = request_data
        print ("---Request Start---")
        print (request_data.strip())
        print ("---Request End---")

        self.parse_request(request_data)
        
        #Construct envrioment dictionary using request data
        env = self.get_environ()

        #Call Application
        result = self.application(env, self.start_response)

        #Construct Response
        self.finish_response(result)

    def parse_request(self, text):
        #Parse HTTP headers to get the requested filename
        request_line = text.splitlines()[0]
        request_line = request_line.rstrip('\r\n')
            
        #Break down the request line into components
        (self.request_method, #GET
        self.path, #Hello
        self.request_version #HTTP 1.1
        ) = request_line.split()
            
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
        env['PATH_INFO'] = self.path #/hello
        env['SERVER_NAME'] = self.server_name #LocalHost
        env['SERVER_PORT'] = str(self.server_port) #8888
        return env
    
    def start_response(self,status,response_headers, exc_info=None):
        #Add Necessary Server Headers
        server_headers = [
            ('Date', 'Mon, 06 August 10:45:01 NZST'),
            ('Server','WSGIServer 0.2')
        ]
        self.headers_set = [status, response_headers + server_headers]
        #To Adhere to WSGI Standards we must return a 'Write' callable this will be ignored for now
        #return self.finish_response 


    def finish_response(self, result):
        try:
            status, response_headers = self.headers_set
            response = f'HTTP/1.1 {status}\r\n'
            for header in response_headers:
                response += '{0}: {1}\r\n'.format(*header)
            response += '\r\n'
            for data in result:
                response_bytes = data
                self.client_connection.sendall(response_bytes)
        finally:
            self.client_connection.close()

def make_server(server_address, application):
    host, port = server_address
    server = http_server_program(host, port)
    server.set_app(application)
    return server


SERVER_ADDRESS = (HOST, PORT) = '', 8888

if __name__ == '__main__':
 httpd = make_server(SERVER_ADDRESS, flask_app)
 print(f'WSGIServer: Serving HTTP on port {PORT}... \n')
 httpd.serve_forever()

 