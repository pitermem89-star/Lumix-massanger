from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route("/")
def home():
    return render_template("index.html")


@socketio.on("join")
def join(data):
    join_room(data["room"])
    emit("system", f"{data['user']} зашёл в чат", room=data["room"])


@socketio.on("message")
def message(data):
    emit("message", data, room=data["room"])


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000, allow_unsafe_werkzeug=True)
