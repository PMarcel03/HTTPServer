from flask import Flask, jsonify

app = Flask(__name__)

#This code is commended out so it's not directly handled by the Flask app
# #New route for the root URL
# @app.route('/', methods=['GET'])
# def index():
#     return "<h1>Welcome to your API-Driven web Server!</h1><p>Navigate to /messages to see API data</p>"

#This will be the API end point
@app.route('/messages', methods=['GET'])
def get_messages():
    messages = [
        {"id": 1, "text": "Hello, this is the first message!"},
        {"id": 2, "text": "Welcome to the message board API."}
    ]

    
    return jsonify(messages)
if __name__ == '__main__':
    pass 