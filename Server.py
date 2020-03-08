from functools import wraps, partial

from flask import Flask, request, jsonify
from sqlalchemy.exc import IntegrityError

from Database import db_session, init_db
from Models import User, Session, Relationship
from validate_email import validate_email

from constants import *

app = Flask(__name__)


def get_friends(user):
    requested_friends = (
        db_session.query(Relationship.receiving_user_id)
        .filter(Relationship.requesting_user == user)
        .filter(Relationship.status == CONFIRMED)
    )

    received_friends = (
        db_session.query(Relationship.requesting_user_id)
        .filter_by(receiving_user=user)
        .filter_by(status=CONFIRMED)
    )
    return requested_friends.union(received_friends).all()


def check_user(name, password):
    if validate_email(name):
        user = db_session.query(User).filter(User.email == name).first()
    else:
        user = db_session.query(User).filter(User.name == name).first()
    if user and user.password == password:
        return user
    elif user:
        return "Wrong password", 400
    else:
        return "User not exist", 400


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
print(login_not_required)


@app.route("/users/create_user", methods=['POST'])
def create_user():
    if request.method == "POST":
        if not validate_email(request.form["email"]):
            return "Email not valid", 400
        u = User()
        u.name = request.form["name"]
        u.email = request.form["email"]
        u.password = request.form["pass"]
        try:
            db_session.add(u)
            db_session.commit()
        except IntegrityError as e:
            return "User existed: " + e.args[0].rsplit(".", 1)[-1], 400
        return ""


@app.route("/log_in", methods=['POST'])
def sign_in():
    u = check_user(request.headers["name"], request.headers["pass"])
    if isinstance(u, User):
        if u.status == ONLINE:
            return "User online", 400
        elif u:
            u.status = ONLINE
            # db_session.add(user)
            db_session.commit()
            return ""
    else:
        return u


@app.route("/log_out", methods=['POST'])
@login_required
def log_out(u):
    u.status = OFFLINE
    # db_session.add(user)
    db_session.commit()
    return ""


@app.route("/sessions/create_session", methods=["POST"])
@login_required
def create_session(u):
    s = Session(name=request.form["name"], desc=request.form["desc"], user_limit=2)
    s.users.append(u)
    db_session.add(s)
    db_session.commit()


@app.route("/sessions/connect", methods=["POST"])
@login_required
def connect_to_session(u):
    s = Session.query.filter(Session.id == request.form["id"]).first()
    if s.status == PENDING:
        if len(s.users) < s.user_limit:
            s.users.append(u)
            db_session.commit()
            return ""
        else:
            return "Game is full", 400
    elif s.status == STARTED:
        return "Game started", 400


@app.route("/sessions/disconnect", methods=["POST"])
@login_required
def disconnect(u):
    if u.session:
        s = u.session
        u.session_id = None
        if not s.users:
            Session.query.filter(Session.id == s.id).delete()
        db_session.commit()
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
                response["users"] = [[u.name for u in s.users]]
            if s.users:
                response["host"] = s.users[0].name
            return jsonify(response)
        else:
            return "", 404
    else:
        response = []
        for s in Session.query.all():
            serv = {"id": s.id, "name": s.name, "desc": s.desc,
                     "limit": s.user_limit,
                     "status": s.status}
            if u:
                serv["users"] = [[u.name for u in s.users]]
            if s.users:
                serv["host"] = s.users[0].name
            response.append(serv)
        return jsonify(response)


@app.route("/friends", methods=["GET"])
@login_required
def get_friends(u):
    response = []
    for f in get_friends(u):
        friend = {"name": f.name, "status": f.status, "session": {}}
        if f.session:
            friend["session"]["id"] = f.session_id
            friend["session"]["status"] = f.session.status
            friend["session"]["name"] = f.session.name
        response.append(friend)
    return response


@app.route("/friends/add", methods=["POST"])
@login_required
def add_friend(u):
    f = User.query.filter(User.name == request.form["name"]).first()
    if not f:
        return "Friend not exist", 404
    friends = get_friends(u)
    if f in friends:
        return "Friend already added", 400
    if f in [i.requesting_user for i in u.friends]:
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
        db_session.add(r)
    db_session.commit()
    return ""


@app.route("/friends/remove", methods=["POST"])
@login_required
def remove_friend(u):
    f = User.query.filter(User.name == request.form["name"]).first()
    if not f:
        return "Friend not exist", 404
    a = Relationship.query.filter(Relationship.receiving_user_id == u.id).filter(Relationship.requesting_user_id == f.id)
    b = Relationship.query.filter(Relationship.receiving_user_id == f.id).filter(
        Relationship.requesting_user_id == u.id)
    if a.union(b).delete():
        return ""
    else:
        return "This user not friend", 400


@app.route("/users", methods=["GET"])
def get_users():
    response = [u.name for u in User.query.all()]
    return jsonify(response)


@app.teardown_appcontext
def shutdown_session(exception=None):
    for i in User.query.filter(User.status == ONLINE).all():
        i.status = OFFLINE
    try:
        num_rows_deleted = db_session.query(Session).delete()
        db_session.commit()
    except:
        db_session.rollback()
    db_session.remove()


if __name__ == '__main__':
    app.run(port=8081, host='127.0.0.1')
    init_db()
'''
nc localhost 8081
POST /user?name=Vasya&email=42&password=123 HTTP/1.1
Host: 127.0.0.1

'''
