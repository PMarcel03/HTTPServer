import re
import json
from datetime import datetime

class Router:
    """Simple URL Routing System"""

    def __init__(self):
        self.routes = []

    def route(self, pattern, methods=['GET']):
              """Decorator to register routers"""
              def decorator(handler):
                    self.routes.append({
                          'pattern': pattern,
                          'handler': handler,
                          'methods': methods
                    })
                    return handler
              return decorator
    
    def dispatch(self, path, method ='GET'):
          #Routing Logic
          for route in self.routes:
                #Check if HTTP method matches and then attempt to match the path
                if method in route['methods']:
                      is_match, variables = self._match_and_extract(path, route['pattern'])
                      if is_match:
                            return route['handler'], variables
          # This return statement was moved outside the loop to check all routes
          return None, {}
            
          
    def _match_and_extract(self, path, pattern):
          """Uses regular expressions to match the path and extract variables."""
          #Converts a route pattern like '/users/<user_id>' into a regex pattern
          #This regex matches a group of characters that are not a '/'
          regex_pattern = re.sub(r'<\w+>', r'([^/]+)', pattern) + '$'

          #Use a regex match to find the path and extract variables in one go
          match = re.match(regex_pattern, path)

          if match:
                variables = {}
                #Find the names of the variables from the pattern string
                var_names = re.findall(r'<(\w+)>', pattern)

                #Populate the variables dictionary with captured groups
                for i, var_name in enumerate(var_names):
                      variables[var_name] = match.group(i + 1)

                return True, variables
          return False, {}
    
#Create the router instance
router = Router()

#============================================================
#MESSAGE BOARD - IN-MEMORY STORAGE (For testing)
#============================================================
messages = [
      { 
            "id": 1,
            "text": "Hello, this is the first message",
            "Author": "System",
            "timestamp": datetime.now().isoformat()
      },
      {
            "id": 2,
            "text": "Welcome to the message board API",
            "Author": "System",
            "timestamp": datetime.now().isoformat()
      }
]
next_message_id = 3
#============================================================
#MESSAGE BOARD - API ROUTES
#============================================================
@router.route('/api/messages', methods=['GET','HEAD','POST','OPTIONS'])
def api_messages(variables, json_body=None):
      """
      GET: Retrieve all messages
      POST: Create a new message
      """
      global next_message_id

      method = variables.get('_method', 'GET')

      #GET - List all messages
      if method in ['GET', 'HEAD']:
            response_data = {
                  "success": True,
                  "count": len(messages),
                  "messages": messages
            }
            return json.dumps(response_data, indent=2), 'application/json', '200 OK'
      #POST - Create a new message
      if method == 'POST':
            if not json_body:
                  error = {
                        "success": False,
                        "error": "Request Body is required"
                  }
                  return json.dumps(error, indent=2), 'application/json', '400 Bad Request'
            
            #Validate required fields
            if 'text' not in json_body or not json_body['text'].strip():
                  error = {
                        "success": False,
                        "error": "Message 'Text' field is required and cannot be empty"
                  }
                  return json.dumps(error, indent=2), 'application/json', '400 Bad Request'
            
            #Create a new message
            new_message = {
                  "id": next_message_id,
                  "text": json_body['text'].strip(),
                  "author": json_body.get('author', 'Anonymous'),
                  "timestamp": datetime.now().isoformat()
            }
            messages.append(new_message)
            next_message_id += 1

            response_data = {
                  "success": True,
                  "message": "Message created successfully",
                  "data": new_message
            }
            return json.dumps(response_data, indent=2), 'application/json', '201 Created'
@router.route('/api/messages/<message_id>', methods=['GET', 'HEAD', 'PUT', 'DELETE', 'OPTIONS'])
def api_message_detail(variables, json_body=None):
      """
      GET: Retrieve a specific message
      PUT: Update a message
      DELETE: Delete a message
      """
      global messages

      method = variables.get('_method', 'GET')

      #Validate message_id
      try:
            message_id = int(variables.get('message_id'))
      except (ValueError, TypeError):
            error = {
                  "success": True,
                  "error": "Invalid message ID - must be an integer"
            }
            return json.dumps(error, indent=2), 'application/json', '400 Bad Request'
      #Find the message
      message = next((m for m in messages if m['id'] == message_id), None)

      #GET - Retrieve a single message
      if method in ['GET', 'HEAD']:
            if not message:
                  error ={
                        "success": False,
                        "error": f"Message with ID {message_id} not found"
                  }
                  return json.dumps(error, indent=2), 'application/json', '404 Not Found'
            response_data = {
                  "success": True,
                  "data": message
            }
            return json.dumps(error, indent=2), 'application/json', '200 OK'
      
      #DELETE - Delete a single message
      if method == 'DELETE':
            if not message:
                  error = {
                        "success": False,
                        "error": f"Message with ID {message_id} not found"
                  }
                  return json.dumps(error, indent=2), 'application/json', '404 Not Found'
            messages = [m for m in messages if m['id'] !=message_id]

            response_data = {
                  "success": True,
                  "message": f"Message {message_id} has been deleted successfully"
            }
            return json.dumps(response_data, indent=2), 'application/json', '200 OK'
      
      #PUT - Update a message
      if method == 'PUT':
            if not message:
                  error = {
                        "success": False,
                        "error": f"Message with {message_id} not found"
                  }
                  return json.dumps(error, indent=2), 'application/json', '404 Not Found'
            
            #Update fields if provided
            if 'text' in json_body:
                  if not json_body['text'].strip():
                        error = {
                              "success": False,
                              "error": "Message text cannot be empty"
                        }
                        return json.dumps(error, indent=2), 'application/json', '400 Bad Request'
                  message['text'] = json_body['text'].strip()

                  if 'author' in json_body:
                        message['author'] = json_body['author']

                  #Update timestamp
                  message['timestamp'] = datetime.now().isoformat()

                  response_data = {
                        "success": True,
                        "message": "Message updated successfully",
                        "data": message
                  }
                  return json.dumps(response_data, indent=2), 'application/json', '200 OK'
            
#============================================================
#MESSAGE BOARD - Search Messages
#============================================================
@router.route('/api/messages/search/<query>')
def api_message_search(variables):
      """Search messages by text content"""
      query = variables.get('query', '').lower()

      if not query: 
            error = {
                  "success": False,
                  "error": "Search query cannot be empty"
            }
            return json.dumps(error, indent=2), 'application/json', '400 Bad Request'
      
      #Filter messages containing the query
      results = [m for m in messages if query in m['text'].lower()]

      response_data = {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
      }
      return json.dumps(response_data, indent=2), 'application/json', '200 OK'
#Function to get the configured router (For Webserver.py to import)
def get_router():
      """Return the configured router instance"""
      return router