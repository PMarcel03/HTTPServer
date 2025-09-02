import re
import json

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

#========================================================
# This is where the Routers are Contained
# ========================================================

@router.route('/')
def home(variables):
      # Return content, content-type, and status
      return '''
        <h1>Welcome Home!</h1>
        <ul>
            <li><a href="/users/123">User 123</a></li>
            <li><a href="/users/456">User 456</a></li>
            <li><a href="/about">About</a></li>
        </ul>
        ''', 'text/html', '200 OK'

@router.route('/users/<user_id>')
def user_profile(variables):
      valid_users = ['123', '456']
      user_id = variables.get('user_id')

      if user_id not in valid_users:
            return f'''
            <h1> 404 Not Found</h1>
            <p>The user with ID: {user_id} was not found.</p>
            <p><a href="/">Back to Home</a></p>
            ''', 'text/html', '404 Not Found'
      
      return f'''
            <h1> User Profile {user_id} </h1>
            <p>This is the profile page for user {user_id}</p>
            <p><a href="/">Back to Home</a></p>
            ''', 'text/html', '200 OK'

@router.route('/api/users/<user_id>', methods=['GET', 'POST'])
def api_user(variables, json_body=None):
    user_id = variables.get('user_id', 'unknown')
    response_data = {"user_id": user_id}
    
    if json_body:
        response_data['received_json'] = json_body
    
    return json.dumps(response_data, indent=2), 'application/json', '200 OK'

#Function to get the configured router (For Webserver.py to import)
def get_router():
      """Return the configured router instance"""
      return router