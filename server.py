from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
import eventlet
import sqlite3
import os

eventlet.monkey_patch()

app = Flask(__name__, static_folder="static")
app.config["SECRET_KEY"] = "lumix"

socketio = SocketIO(app, cors_allowed_origins="*")

DB = "chat.db"

# ---------- DB ----------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT,
            name TEXT,
            text TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- ROUTE ----------
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# ---------- JOIN ROOM ----------
@socketio.on("join")
def on_join(data):
    room = data["room"]
    join_room(room)

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT name, text FROM messages WHERE room=?", (room,))
    history = [{"name": n, "text": t} for n, t in c.fetchall()]
    conn.close()

    emit("history", history)

# ---------- MESSAGE ----------
@socketio.on("message")
def handle_message(data):
    room = data["room"]
    name = data["name"]
    text = data["text"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO messages (room, name, text) VALUES (?, ?, ?)",
              (room, name, text))
    conn.commit()
    conn.close()

    emit("message", data, room=room)

# ---------- RUN ----------
if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=10000,
        allow_unsafe_werkzeug=True
    )