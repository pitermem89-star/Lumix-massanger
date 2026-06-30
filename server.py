import eventlet
eventlet.monkey_patch()

from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__, static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route("/")
def home():
    return send_from_directory("static", "index.html")


@socketio.on("message")
def handle_message(data):
    room = data.get("room")
    emit("message", data, room=room)


@socketio.on("join")
def join(data):
    join_room(data["room"])


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
