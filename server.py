import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
import jwt
import datetime

app = Flask(__name__, static_folder="static")
app.config["SECRET_KEY"] = "SUPER_SECRET"

socketio = SocketIO(app, cors_allowed_origins="*")

JWT_SECRET = "JWT_V3_SECRET"

online = {}
messages = {}   # room -> list


# ---------------- AUTH ----------------

def make_token(user):
    return jwt.encode(
        {"user": user, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)},
        JWT_SECRET,
        algorithm="HS256"
    )

def verify(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])["user"]
    except:
        return None


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/login", methods=["POST"])
def login():
    u = request.json["username"]
    return jsonify({"token": make_token(u)})


# ---------------- SOCKET ----------------

@socketio.on("auth")
def auth(data):
    user = verify(data["token"])
    if not user:
        return

    online[request.sid] = user
    emit("online", list(set(online.values())), broadcast=True)


@socketio.on("join")
def join(data):
    join_room(data["room"])


@socketio.on("message")
def message(data):
    user = online.get(request.sid)
    if not user:
        return

    room = data["room"]

    msg = {
        "id": len(messages.get(room, [])) + 1,
        "user": user,
        "text": data["text"],
        "room": room
    }

    messages.setdefault(room, []).append(msg)

    emit("message", msg, room=room)


@socketio.on("delete")
def delete(data):
    room = data["room"]
    msg_id = data["id"]

    messages[room] = [m for m in messages.get(room, []) if m["id"] != msg_id]

    emit("delete", data, room=room)


@socketio.on("edit")
def edit(data):
    room = data["room"]

    for m in messages.get(room, []):
        if m["id"] == data["id"]:
            m["text"] = data["text"]

    emit("edit", data, room=room)


@socketio.on("dm")
def dm(data):
    user = online.get(request.sid)

    emit("dm", {
        "from": user,
        "to": data["to"],
        "text": data["text"]
    }, broadcast=True)


@socketio.on("disconnect")
def disconnect():
    if request.sid in online:
        del online[request.sid]
        emit("online", list(set(online.values())), broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
