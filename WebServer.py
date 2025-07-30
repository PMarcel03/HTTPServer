#HTTP Server Python
import socket
import os

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
            client_connection, client_address = self.socket.accept()
            print (f"Accepted Connection From: {client_address}")

            #Handle the client's request
            self.handle_request(client_connection)

        

    #HTTP Handler
    def handle_request(self, connection):
        """
        Receives, Parses and responses to a single client's HTTP request
        """
        #Get the client request
        request_data = connection.recv(1024).decode('utf-8')
        print ("---Request Start---")
        print (request_data.strip())
        print ("---Request End---")

        #Parse HTTP headers to get the requested filename
        headers = request_data.split('\r\n')
        filename = headers[0].split()[1]

        #Get the content of the file
        if filename == '/':
            filename = '/index.html'
        
        #Construct Full File Path
        filepath = os.path.join(self.web_root, filename.lstrip('/'))

        #Check for path traversal attempts
        if not os.path.abspath(filepath).startswith(os.path.abspath(self.web_root)):
            raise FileNotFoundError("Path Traversal Attempt")

        #Read the file and prepare response
        try:
            with open(filepath, 'r') as f:
                content = f.read()

            http_response = 'HTTP/1.1 200 ok\r\n\r\n' + content
        except FileNotFoundError:
            http_response = 'HTTP/1.1 404 NOT FOUND\r\n\r\nFile Not Found'
        except IOError:
            http_response = 'HTTP/1.1 500 Internal Server Error\r\n\r\n Could not read file'
            
        #Send HTTP Response
        connection.sendall(http_response.encode('utf-8'))
        connection.close()

if __name__ == '__main__':
    #create an instance of the server and run it
    server = http_server_program()
    server.serve_forever()