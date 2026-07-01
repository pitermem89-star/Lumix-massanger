from flask import Flask, render_template
from flask_socketio import SocketIO
import time

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

messages = []

@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("message")
def handle_message(data):
    msg = {
        "text": data["text"],
        "user": data["user"],
        "time": time.strftime("%H:%M")
    }
    messages.append(msg)
    socketio.emit("message", msg)


# ❌ ВАЖНО: НЕ запускаем socketio.run() в Render