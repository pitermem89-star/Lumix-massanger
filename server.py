from flask import Flask, render_template
from flask_socketio import SocketIO, send, emit
import time

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret"

# ВАЖНО: async_mode='threading' — чтобы НЕ использовать eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

messages = []  # память сообщений (простая версия)

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
    emit("message", msg, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)