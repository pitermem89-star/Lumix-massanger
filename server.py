import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
from flask_sqlalchemy import SQLAlchemy
import hashlib

# ---------------- APP ----------------

app = Flask(__name__, static_folder="static")

app.config["SECRET_KEY"] = "lumix_secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------- DATABASE ----------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(50))
    username = db.Column(db.String(50))
    text = db.Column(db.Text)

with app.app_context():
    db.create_all()

# ---------------- HTTP ----------------

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/register", methods=["POST"])
def register():
    data = request.json

    username = data.get("username")
    password = hashlib.sha256(data.get("password", "").encode()).hexdigest()

    if User.query.filter_by(username=username).first():
        return jsonify({"ok": False, "error": "user exists"}), 400

    user = User(username=username, password=password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"ok": True})


@app.route("/login", methods=["POST"])
def login():
    data = request.json

    username = data.get("username")
    password = hashlib.sha256(data.get("password", "").encode()).hexdigest()

    user = User.query.filter_by(username=username, password=password).first()

    if not user:
        return jsonify({"ok": False}), 400

    return jsonify({"ok": True})


# ---------------- SOCKET ----------------

online_users = {}

@socketio.on("join")
def on_join(data):
    room = data.get("room")
    username = data.get("username")

    join_room(room)

    online_users[request.sid] = username

    emit("online", list(set(online_users.values())), broadcast=True)


@socketio.on("message")
def handle_message(data):
    room = data.get("room")
    username = data.get("username")
    text = data.get("text")

    # save to DB
    msg = Message(room=room, username=username, text=text)
    db.session.add(msg)
    db.session.commit()

    # broadcast
    emit("message", {
        "room": room,
        "username": username,
        "text": text
    }, room=room)


@socketio.on("disconnect")
def on_disconnect():
    if request.sid in online_users:
        del online_users[request.sid]
        emit("online", list(set(online_users.values())), broadcast=True)


# ---------------- START ----------------

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000, debug=False)
