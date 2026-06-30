import asyncio
import websockets
import os
import json
import sqlite3

PORT = int(os.environ.get("PORT", 8000))
CLIENTS = {} # {websocket: {"username": ..., "user_id": ...}}

def init_db():
    conn = sqlite3.connect("lumix.db")
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        display_name TEXT,
        username TEXT UNIQUE,
        password TEXT
    )''')
    # Таблица сообщений
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        room TEXT,
        text TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

async def broadcast_to_room(room, data):
    payload = json.dumps(data)
    for ws, info in CLIENTS.items():
        # Если это ЛС (формат "p2p:id1:id2"), проверяем, что юзер является участником
        if room.startswith("p2p:"):
            parts = room.split(":")
            if str(info.get("user_id")) in parts:
                await ws.send(payload)
        # Если обычная комната
        else:
            await ws.send(payload)

async def handle_client(websocket):
    CLIENTS[websocket] = {}
    conn = sqlite3.connect("lumix.db")
    cursor = conn.cursor()
    
    try:
        async for raw_message in websocket:
            data = json.loads(raw_message)
            action = data.get("action")

            if action == "register":
                d_name = data.get("display_name")
                u_name = data.get("username").replace("@", "").strip().lower()
                pwd = data.get("password")
                try:
                    cursor.execute("INSERT INTO users (display_name, username, password) VALUES (?, ?, ?)", (d_name, u_name, pwd))
                    conn.commit()
                    user_id = cursor.lastrowid
                    CLIENTS[websocket] = {"username": u_name, "display_name": d_name, "user_id": user_id}
                    await websocket.send(json.dumps({"action": "auth_success", "user_id": user_id, "username": u_name, "display_name": d_name}))
                except sqlite3.IntegrityError:
                    await websocket.send(json.dumps({"action": "error", "message": "Этот @юзернейм уже занят!"}))

            elif action == "login":
                u_name = data.get("username").replace("@", "").strip().lower()
                pwd = data.get("password")
                cursor.execute("SELECT id, display_name FROM users WHERE username = ? AND password = ?", (u_name, pwd))
                user = cursor.fetchone()
                if user:
                    CLIENTS[websocket] = {"username": u_name, "display_name": user[1], "user_id": user[0]}
                    await websocket.send(json.dumps({"action": "auth_success", "user_id": user[0], "username": u_name, "display_name": user[1]}))
                else:
                    await websocket.send(json.dumps({"action": "error", "message": "Неверный юзернейм или пароль!"}))

            elif action == "get_rooms_and_users":
                # Отправляем список всех пользователей для ЛС
                cursor.execute("SELECT id, display_name, username FROM users")
                all_users = [{"id": r[0], "display_name": r[1], "username": r[2]} for r in cursor.fetchall()]
                await websocket.send(json.dumps({"action": "users_list", "users": all_users}))

            elif action == "load_room":
                room = data.get("room")
                cursor.execute('''SELECT messages.id, users.display_name, users.username, messages.text, messages.sender_id 
                                  FROM messages JOIN users ON messages.sender_id = users.id 
                                  WHERE room = ? ORDER BY timestamp ASC''', (room,))
                history = [{"id": r[0], "author": r[1], "username": r[2], "text": r[3], "sender_id": r[4]} for r in cursor.fetchall()]
                await websocket.send(json.dumps({"action": "history", "room": room, "messages": history}))

            elif action == "msg":
                room = data.get("room")
                text = data.get("text")
                sender_id = CLIENTS[websocket].get("user_id")
                if sender_id:
                    cursor.execute("INSERT INTO messages (sender_id, room, text) VALUES (?, ?, ?)", (sender_id, room, text))
                    conn.commit()
                    msg_id = cursor.lastrowid
                    await broadcast_to_room(room, {
                        "action": "new_msg", "room": room, "id": msg_id,
                        "author": CLIENTS[websocket]["display_name"], "username": CLIENTS[websocket]["username"],
                        "text": text, "sender_id": sender_id
                    })

            elif action == "delete_msg":
                msg_id = data.get("id")
                room = data.get("room")
                sender_id = CLIENTS[websocket].get("user_id")
                # Удалять может только автор
                cursor.execute("SELECT sender_id FROM messages WHERE id = ?", (msg_id,))
                row = cursor.fetchone()
                if row and row[0] == sender_id:
                    cursor.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
                    conn.commit()
                    await broadcast_to_room(room, {"action": "msg_deleted", "room": room, "id": msg_id})

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        del CLIENTS[websocket]
        conn.close()

async def main():
    async with websockets.serve(handle_client, "0.0.0.0", PORT):
        print(f"Сервер Lumix БД запущен на порту {PORT}...")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
