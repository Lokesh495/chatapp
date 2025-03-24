from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import sqlite3

app = Flask(__name__)
app.secret_key = "secret_key"
socketio = SocketIO(app)

# Store online users in memory
online_users = {}  # {username: sid}


# ---------------------
# ✅ Database Connection
# ---------------------
def get_db_connection():
    conn = sqlite3.connect("instance/chatapp.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------
# ✅ Home Page Route
# ---------------------
@app.route("/")
def home():
    if "username" in session:
        return render_template("index.html", username=session["username"])
    return redirect(url_for("login"))


# ---------------------
# ✅ Login Route
# ---------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["t1"]
        password = request.form["t2"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["username"] = username
            return redirect(url_for("home"))
        else:
            return "Invalid credentials!"

    return render_template("login.html")


# ---------------------
# ✅ Signup Route
# ---------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["t1"]
        password = request.form["t2"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("INSERT INTO user (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("singup.html")


# ---------------------
# ✅ Room Route
# ---------------------
@app.route("/room/<room>")
def room(room):
    if "username" not in session:
        return redirect(url_for("login"))
    
    username = session["username"]
    return render_template("room.html", username=username, room=room)


# ---------------------
# ✅ Create Room Route
# ---------------------
@app.route("/create_room", methods=["POST"])
def create_room():
    if "username" not in session:
        return redirect(url_for("login"))

    room_name = request.form.get("room_name")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rooms (name) VALUES (?)", (room_name,))
    conn.commit()
    conn.close()

    return redirect(url_for("room", room=room_name))


# ---------------------
# ✅ Socket.IO Events
# ---------------------
@socketio.on("connect")
def handle_connect():
    """Add user to online list on connection"""
    username = session.get("username")
    if username:
        online_users[username] = request.sid
        emit("update_user_list", list(online_users.keys()), broadcast=True)


@socketio.on("disconnect")
def handle_disconnect():
    """Remove user from online list on disconnection"""
    username = session.get("username")
    if username and username in online_users:
        del online_users[username]
        emit("update_user_list", list(online_users.keys()), broadcast=True)


@socketio.on("send_invite")
def send_invite(data):
    """Send invite to specific user"""
    invited_user = data["user"]
    room = data["room"]
    if invited_user in online_users:
        emit("receive_invite", {"room": room}, room=online_users[invited_user])


@socketio.on("join")
def on_join(data):
    """Join the chat room"""
    room = data["room"]
    username = session.get("username")
    join_room(room)
    send(f"{username} has joined the room.", room=room)


@socketio.on("leave")
def on_leave(data):
    """Leave the chat room"""
    room = data["room"]
    username = session.get("username")
    leave_room(room)
    send(f"{username} has left the room.", room=room)

@socketio.on("send_message")
def handle_message(data):
    """Handle message sending"""
    room = data["room"]
    username = data["username"]
    message = data["message"]

    # Broadcast the message to all users in the room
    emit("receive_message", {"username": username, "message": message}, room=room)



# ---------------------
# ✅ Logout Route
# ---------------------
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


# ---------------------
# ✅ Run the App
# ---------------------
if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=4000)
