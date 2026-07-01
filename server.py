from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit, join_room
import eventlet
import sqlite3
import uuid

eventlet.monkey_patch()

app = Flask(__name__, static_folder="static")
app.config["SECRET_KEY"] = "lumix_v7"

socketio = SocketIO(app, cors_allowed_origins="*")

DB = "chat.db"

users = {}        # token -> name
online = set()    # names


# ---------- DB ----------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT,
            sender TEXT,
            receiver TEXT,
            text TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            name TEXT PRIMARY KEY,
            password TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ---------- AUTH ----------
@socketio.on("register")
def register(data):
    name = data["name"]
    password = data["password"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT name FROM users WHERE name=?", (name,))
    if c.fetchone():
        emit("auth", {"ok": False, "msg": "exists"})
        return

    c.execute("INSERT INTO users VALUES (?,?)", (name, password))
    conn.commit()
    conn.close()

    token = str(uuid.uuid4())
    users[token] = name
    online.add(name)

    emit("auth", {"ok": True, "token": token, "name": name})


@socketio.on("login")
def login(data):
    name = data["name"]
    password = data["password"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT password FROM users WHERE name=?", (name,))
    row = c.fetchone()
    conn.close()

    if not row or row[0] != password:
        emit("auth", {"ok": False})
        return

    token = str(uuid.uuid4())
    users[token] = name
    online.add(name)

    emit("auth", {"ok": True, "token": token, "name": name})


# ---------- JOIN ROOM ----------
@socketio.on("join")
def join(data):
    room = data["room"]
    join_room(room)

    emit("online", list(online), broadcast=True)

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT sender, text FROM messages WHERE room=? AND receiver IS NULL", (room,))
    history = [{"name": s, "text": t} for s, t in c.fetchall()]
    conn.close()

    emit("history", history)


# ---------- MESSAGE ----------
@socketio.on("message")
def message(data):
    room = data["room"]
    name = data["name"]
    text = data["text"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO messages VALUES (NULL,?,?,?,?)",
              (room, name, None, text))
    conn.commit()
    conn.close()

    emit("message", data, room=room)


# ---------- DM ----------
@socketio.on("dm")
def dm(data):
    sender = data["from"]
    receiver = data["to"]
    text = data["text"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO messages VALUES (NULL,?,?,?,?)",
              ("dm", sender, receiver, text))
    conn.commit()
    conn.close()

    emit("dm", data, broadcast=True)


# ---------- DISCONNECT ----------
@socketio.on("disconnect")
def disconnect():
    # упрощённо (в реальном Discord — привязка к token)
    pass


if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=10000,
        allow_unsafe_werkzeug=True
    )