import atexit
from functools import wraps, partial
from random import random

from flask import Flask, request, jsonify
from sqlalchemy.exc import IntegrityError

from Models import User, Session, Relationship
from validate_email import validate_email

from constants import *
from flask_sqlalchemy import SQLAlchemy

from Database import app, db


def get_friends_from_db(user):
    requested_friends = (Relationship.query
                         .filter(Relationship.requesting_user == user)
                         .filter(Relationship.status == CONFIRMED)).all()
    received_friends = (
        Relationship.query
            .filter_by(receiving_user=user)
            .filter_by(status=CONFIRMED)
    ).all()
    return [i.receiving_user for i in requested_friends] \
           + [i.requesting_user for i in received_friends]


def check_user(name, password):
    if validate_email(name):
        user = db.session.query(User).filter(User.email == name).first()
    else:
        user = db.session.query(User).filter(User.name == name).first()
    if user and user.password == password:
        return user
    elif user:
        return "Wrong password", 400
    else:
        return "User not exist", 404


def _login(func, required):
    @wraps(func)
    def new(*args, **kwargs):
        n, p = request.headers.get("name"), request.headers.get("pass")
        if not n or not p:
            if required:
                return "Authorisation required", 400
            else:
                return func(None, *args, **kwargs)
        u = check_user(n, p)
        if isinstance(u, User):
            if u.status == ONLINE:
                return func(u, *args, **kwargs)
            elif required:
                return "User offline", 400
            else:
                return func(None, *args, **kwargs)
        elif required:
            return u
        else:
            return func(None, *args, **kwargs)

    return new


login_required = partial(_login, required=True)
login_not_required = partial(_login, required=False)


@app.route("/users/create_user", methods=['POST'])
def create_user():
    if not validate_email(request.form["email"]):
        return "Email not valid", 400
    u = User()
    if not request.form.get("name"):
        return "Name empty", 400
    elif User.query.filter(User.name == request.form["name"]).first():
        return "user.name", 400
    u.name = request.form["name"]
    if not request.form.get("email"):
        return "Email empty", 400
    elif User.query.filter(User.email == request.form["email"]).first():
        return "user.email", 400
    u.email = request.form["email"]
    if not request.form.get("pass"):
        return "Password empty", 400

    u.password = request.form["pass"]
    u.status = ONLINE
    try:
        db.session.add(u)
        db.session.commit()
        return jsonify({"id": u.id, "name": u.name, "status": ONLINE})
    except IntegrityError as e:
        return "User existed: " + e.args[0].rsplit(".", 1)[-1], 400


@app.route("/log_in", methods=['POST'])
def log_in():
    u = check_user(request.headers["name"], request.headers["pass"])
    if isinstance(u, User):
        if u.status == ONLINE:
            return "User online", 400
        elif u:
            u.status = ONLINE
            db.session.add(u)
            db.session.commit()
            return jsonify({"id": u.id, "name": u.name, "status": ONLINE})
    else:
        return u


@app.route("/log_out", methods=['POST'])
@login_required
def log_out(u):
    u.status = OFFLINE
    # db_session.add(user)
    db.session.commit()
    return ""


@app.route("/sessions/create_session", methods=["POST"])
@login_required
def create_session(u):
    if not request.form.get("name"):
        return "EMPTY NAME", 400
    s = Session(name=request.form["name"], desc=request.form["desc"], user_limit=2)
    s.users.append(u)
    db.session.add(s)
    db.session.commit()
    response = {"id": request.args["id"], "name": s.name, "desc": s.desc,
                "limit": s.user_limit,
                "status": s.status}
    response["users"] = [{"id": i.id, "name": i.name, "status": i.status} for i in s.users]
    response["seed"] = s.seed
    response["extra"] = s.extra
    if s.users:
        response["host"] = {"id": s.users[0].id, "name": s.users[0].name,
                            "status": s.users[0].status}
    return jsonify(response)


@app.route("/sessions/<int:id>/connect", methods=["POST"])
@login_required
def connect_to_session(u, id):
    s = Session.query.filter(Session.id == id).first()
    if s:
        if s.status == PENDING:
            if len(s.users) < s.user_limit:
                s.users.append(u)
                db.session.commit()
                return ""
            else:
                return "Game is full", 400
        elif s.status == STARTED:
            return "Game started", 400
        elif s.status == FINISHED:
            return "Game finished", 400
    else:
        return "Session not exist", 404


@app.route("/sessions/disconnect", methods=["POST"])
@login_required
def disconnect(u):
    if u.session:
        s = u.session
        u.session_id = None
        if not s.users:
            Session.query.filter(Session.id == s.id).delete()
        db.session.commit()
        return ""
    else:
        return "User not in game", 400


@app.route("/sessions", methods=["GET"])
@login_not_required
def get_session(u):
    if request.args.get("id"):
        s = Session.query.filter(Session.id == request.args["id"]).first()
        if s:
            response = {"id": request.args["id"], "name": s.name, "desc": s.desc,
                        "limit": s.user_limit,
                        "status": s.status}
            if u:
                response["users"] = [{"id": i.id, "name": i.name, "status": i.status} for i in
                                     s.users]
                response["seed"] = s.seed
                response["extra"] = s.extra
            if s.users:
                response["host"] = {"id": s.users[0].id, "name": s.users[0].name,
                                    "status": s.users[0].status}
            return jsonify(response)
        else:
            return "Session not exist", 404
    else:
        response = []
        for s in Session.query.all():
            serv = {"id": s.id, "name": s.name, "desc": s.desc,
                    "limit": s.user_limit,
                    "status": s.status,
                    "users": []}
            if u:
                serv["users"] = [{"id": i.id, "name": i.name, "status": i.status} for i in s.users]
            if s.users:
                serv["host"] = {"id": s.users[0].id, "name": s.users[0].name,
                                "status": s.users[0].status}
            response.append(serv)
        return jsonify(response)


@app.route("/sessions/<int:id>/start", methods=["POST"])
@login_required
def start_game(u, id):
    s = Session.query.filter(Session.id == id).first()
    if s:
        if len(s.users) < 2:
            return "You need more players", 400
        elif s.users[0] != u:
            return "You not host in this game", 400
        else:
            s.status = STARTED
            s.seed = int(random * 1e16)
            db.session.commit()
            return "Game started successfully", 200
    else:
        return "Session not exist", 404


@app.route("/friends", methods=["GET"])
@login_required
def get_friends(u):
    response = {"confirmed": [], "received": [], "requested": []}
    for f in get_friends_from_db(u):
        friend = {"name": f.name, "status": f.status, "session": {}}
        if f.session:
            friend["session"]["id"] = f.session_id
            friend["session"]["status"] = f.session.status
            friend["session"]["name"] = f.session.name
        response["confirmed"].append(friend)
    for f in Relationship.query.filter(Relationship.receiving_user_id == u.id).filter(
            Relationship.status == PENDING).all():
        f = f.requesting_user
        friend = {"name": f.name, "status": f.status, "session": {}}
        if f.session:
            friend["session"]["id"] = f.session_id
            friend["session"]["status"] = f.session.status
            friend["session"]["name"] = f.session.name
        response["received"].append(friend)
    for f in Relationship.query.filter(
            Relationship.requesting_user_id == u.id).filter(Relationship.status == PENDING).all():
        f = f.receiving_user
        friend = {"name": f.name, "status": f.status, "session": {}}
        if f.session:
            friend["session"]["id"] = f.session_id
            friend["session"]["status"] = f.session.status
            friend["session"]["name"] = f.session.name
        response["requested"].append(friend)
    return jsonify(response)


@app.route("/friends/add", methods=["POST"])
@login_required
def add_friend(u):
    f = User.query.filter(User.name == request.form["name"]).first()
    if f == u:
        return "You are your friend", 400
    if not f:
        return "User not exist", 404
    friends = get_friends_from_db(u)
    if f in friends:
        return "Friend already added", 400
    if f in [i.receiving_user for i in u.friends]:
        return "Request already sent", 400
    flag = True
    for i in u.p_friends:
        if f == i.requesting_user:
            flag = False
            i.status = CONFIRMED
    if flag:
        r = Relationship()
        r.requesting_user_id = u.id
        r.receiving_user_id = f.id
        r.status = PENDING
        db.session.add(r)
    db.session.commit()
    friend = {"name": f.name, "status": f.status, "session": {}}
    if f.session:
        friend["session"]["id"] = f.session_id
        friend["session"]["status"] = f.session.status
        friend["session"]["name"] = f.session.name
    return jsonify(friend)


@app.route("/friends/remove", methods=["POST"])
@login_required
def remove_friend(u):
    f = User.query.filter(User.name == request.form["name"]).first()
    if f == u:
        return "You are your friend", 400
    if not f:
        return "User not exist", 404
    a = Relationship.query.filter(Relationship.receiving_user_id == u.id).filter(
        Relationship.requesting_user_id == f.id)
    b = Relationship.query.filter(Relationship.receiving_user_id == f.id).filter(
        Relationship.requesting_user_id == u.id)
    if a.delete() + b.delete():
        return ""
    else:
        return "This user not friend", 400


@app.route("/users", methods=["GET"])
def get_users():
    response = [u.name for u in User.query.all()]
    return jsonify(response)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.commit()
    db.session.remove()


def on_end():
    open("asd.txt", "w").close()
    for i in User.query.filter(User.status == ONLINE).all():
        i.status = OFFLINE
    try:
        num_rows_deleted = db.session.query(Session).delete()
        db.session.commit()
    except:
        db.session.rollback()


if __name__ == '__main__':
    db.create_all()
    atexit.register(on_end)
    app.run(port=8081, host='127.0.0.1')
'''
nc localhost 8081
POST /user?name=Vasya&email=42&password=123 HTTP/1.1
Host: 127.0.0.1

'''
