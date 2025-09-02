from flask import Flask, jsonify

app = Flask(__name__)

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