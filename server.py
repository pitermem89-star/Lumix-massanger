from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
import jwt
import datetime

app = Flask(__name__, static_folder="static")
app.config["SECRET_KEY"] = "secret_key_123"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

JWT_SECRET = "jwt_secret_123"

online_users = {}
messages = {}  # room -> list


# ---------------- AUTH ----------------

def make_token(username):
    return jwt.encode(
        {
            "user": username,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
        },
        JWT_SECRET,
        algorithm="HS256"
    )


def verify_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])["user"]
    except:
        return None


@app.route("/")
def home():
    return send_from_directory("static", "index.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.json["username"]
    return jsonify({"token": make_token(username)})


# ---------------- SOCKET ----------------

@socketio.on("auth")
def auth(data):
    user = verify_token(data["token"])
    if not user:
        return

    online_users[request.sid] = user
    emit("online", list(set(online_users.values())), broadcast=True)


@socketio.on("join")
def join(data):
    join_room(data["room"])


@socketio.on("message")
def handle_message(data):
    user = online_users.get(request.sid)
    if not user:
        return

    room = data["room"]

    msg = {
        "id": int(datetime.datetime.utcnow().timestamp() * 1000),
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

    if room in messages:
        messages[room] = [m for m in messages[room] if m["id"] != msg_id]

    emit("delete", data, room=room)


@socketio.on("disconnect")
def disconnect():
    if request.sid in online_users:
        del online_users[request.sid]
        emit("online", list(set(online_users.values())), broadcast=True)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000, allow_unsafe_werkzeug=True)
