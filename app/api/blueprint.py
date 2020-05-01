import json
from random import random

import discord
from itsdangerous import SignatureExpired, BadSignature
from sqlalchemy import desc
from validate_email import validate_email
from flask import Blueprint, g, jsonify, request, url_for, render_template
from flask_httpauth import HTTPBasicAuth

from app.api import Game
from app.app import db, datetime, app, OrderedDict
from app.constants import FINISHED, STARTED, PENDING
from app.email import send_email_async
from app.models import User, Session, SessionLogs, Post, Tag
from app.token import generate_confirmation_token
import re

auth = HTTPBasicAuth()
discord_auth = HTTPBasicAuth()

api = Blueprint("api", __name__, template_folder="templates")


@auth.verify_password
def verify_password(username_or_token, password):
    try:
        user = User.verify_auth_token(username_or_token)
    except SignatureExpired:
        user = User.query.filter(
            (User.name == username_or_token) | (User.email == username_or_token)).first()
        if not user or user.password != password:
            return False
        user.in_client = False
        db.session.commit()
    except BadSignature:
        user = User.query.filter(
            (User.name == username_or_token) | (User.email == username_or_token)).first()
        if not user or user.password != password:
            return False
    if not user.confirmed:
        return False
    g.user = user
    return True


@discord_auth.verify_password
def discord_verify_password(token, password):
    if app.config["DISCORD_TOKEN"] == token:
        g.user = User.query.filter((User.name == request.args.get("user-name")) | (
                User.name == request.form.get("user-name"))).first_or_404()
        return True
    try:
        user = User.verify_auth_token(token)
    except SignatureExpired:
        user = User.query.filter(
            (User.name == token) | (User.email == token)).first()
        if not user or user.password != password:
            return False
        user.in_client = False
        db.session.commit()
    except BadSignature:
        user = User.query.filter(
            (User.name == token) | (User.email == token)).first()
        if not user or user.password != password:
            return False
    if not user.confirmed:
        return False
    g.user = user
    return True


def send_session_end(s):
    try:
        webhook = discord.Webhook.partial(app.config["WEBHOOK_SESSION_ID"],
                                          app.config["WEBHOOK_SESSION_TOKEN"],
                                          adapter=discord.RequestsWebhookAdapter())
        embed = discord.Embed()
        embed.title = "Сессия #{}".format(s.id)
        embed.colour = discord.Colour.darker_grey()
        embed.description = "Результаты игры"
        winner = "{} | <@!{}>".format(s.winner.name, s.winner.discord_id) if s.winner.discord_id \
            else s.winner.name
        embed.add_field(name="Победитель:", value=winner)
        embed.add_field(name="Игроки:",
                        value=", ".join(
                            map(lambda x: x[0], s.users.with_entities(User.name).all())))
        webhook.send(embed=embed)
    except Exception as e:
        print(e)


# TVOI GIMN

@api.route("/users/create_user", methods=['POST'])
def create_user():
    if not validate_email(request.form["email"]):
        return "Email not valid", 400
    u = User(confirmed=False)
    if not request.form.get("name"):
        return "Name empty", 400
    elif User.query.filter(User.name == request.form["name"]).first() or request.form[
        "name"].isdigit() or not re.fullmatch(r"[a-zA-Z1-9_]*", request.form["name"]):
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
    try:
        db.session.add(u)
        db.session.commit()
    except Exception as e:
        print(e)
        return "", 400
    try:
        token = generate_confirmation_token(u.email)
        confirm_url = url_for('users.confirm_email', token=token, _external=True)
        html = render_template('api/activate.html', confirm_url=confirm_url)
        subject = "Пожалуйста, подтвердите свою почту"
        send_email_async(u.email, subject, html)
    except Exception as e:
        print(e)
        return "", 400
    return jsonify({"id": u.id, "name": u.name})


@api.route('/log_in', methods=["POST"])
@auth.login_required
def login():
    if g.user.in_client:
        return "User online", 400
    token = g.user.generate_auth_token()
    g.user.in_client = True
    db.session.commit()
    user = {"id": g.user.id, "name": g.user.name, 'session_hash': token.decode('ascii'), }
    if g.user.discord_id:
        user["discord"] = int(g.user.discord_id)
    return jsonify(user)


@api.route('/token', methods=["POST"])
@auth.login_required
def get_token():
    token = g.user.generate_auth_token()
    user = {"id": g.user.id, "name": g.user.name, 'session_hash': token.decode('ascii'), }
    if g.user.discord_id:
        user["discord"] = int(g.user.discord_id)
    return jsonify(user)


@api.route("/log_out", methods=['POST'])
@auth.login_required
def log_out():
    sessions = g.user.sessions.all()
    if sessions:
        s = sessions[0]
        if s.status == PENDING:
            s.users.remove(g.user)
            if not s.users.all():
                Session.query.filter(Session.id == s.id).delete()
            elif s.host == g.user:
                s.host = s.users.first()
        elif s.status == STARTED:
            surrender_log = SessionLogs(user=g.user.id, session=s.id, action="SURRENDER",
                                        date=datetime.datetime.now())
            sur_users = {g.user}
            surs = SessionLogs.query.filter(SessionLogs.session == s.id).filter(
                SessionLogs.action == "SURRENDER").all()
            sur_users.update(set(map(lambda x: User.query.filter(User.id == x.user).first(), surs)))
            last = set(s.users) - sur_users
            if len(last) == 1:
                winner = last.pop()
                s.winner = winner
                try:
                    Game.ServerGame().sessions[s.id].ended = True
                except KeyError as e:
                    print(e)
                win_log = SessionLogs(user=winner.id, session=s.id, action="WIN",
                                      date=datetime.datetime.now())
                s.status = FINISHED
                db.session.add(win_log)
                send_session_end(s)
            db.session.add(surrender_log)
    g.user.in_client = False
    g.user = None
    db.session.commit()
    return ""


@api.route("/sessions/create_session", methods=["POST"])
@auth.login_required
def create_session():
    sessions = g.user.sessions.all()
    if not request.form.get("name", None):
        return "Empty name", 400
    elif Session.query.filter(Session.host == g.user).first():
        return "You in session", 400
    elif sessions and sessions[0].status == PENDING:
        return "You in session", 400
    s = Session(name=request.form["name"], host_id=g.user.id, desc=request.form["desc"],
                user_limit=2)
    s.users.append(g.user)
    db.session.add(s)
    db.session.commit()
    response = {"id": s.id, "name": s.name, "desc": s.desc,
                "limit": s.user_limit,
                "status": s.status, "users": []}
    for i in s.users:
        user = {"id": i.id, "name": i.name}
        if i.discord_id:
            user["discord"] = int(i.discord_id)
        response["users"].append(user)
    response["seed"] = s.seed
    response["extra"] = s.extra
    if s.host:
        response["host"] = {"id": s.host.id, "name": s.host.name}
    return jsonify(response)


@api.route("/sessions/<int:id>/connect", methods=["POST"])
@auth.login_required
def connect_to_session(id):
    s = Session.query.filter(Session.id == id).first()
    if s:
        if s.status == PENDING:
            if s.users.count() >= s.user_limit:
                return "Game is full", 400
            elif g.user in s.users or g.user.hosted_session:
                return "You in this session", 400
            else:
                s.users.append(g.user)
                db.session.commit()
                return ""
        elif s.status == STARTED:
            return "Game started", 400
        elif s.status == FINISHED:
            return "Game finished", 400
    else:
        return "Session not exist", 404


@api.route("/sessions/disconnect", methods=["POST"])
@auth.login_required
def disconnect():
    sessions = g.user.sessions.all()
    if sessions:
        s = sessions[0]
        if s.status == FINISHED:
            print("aaaa?")
            return "Session is finished", 400
        elif s.status == PENDING:
            s.users.remove(g.user)
            if g.user == s.host:
                if not s.users.all():
                    Session.query.filter(Session.id == s.id).delete()
                else:
                    s.host = s.users.first()
            db.session.commit()
            return ""
        elif s.status == STARTED:
            surrender_log = SessionLogs(user=g.user.id, session=s.id, action="SURRENDER",
                                        date=datetime.datetime.now())
            sur_users = {g.user}
            surs = SessionLogs.query.filter(SessionLogs.session == s.id).filter(
                SessionLogs.action == "SURRENDER").all()
            sur_users.update(set(map(lambda x: User.query.filter(User.id == x.user).first(), surs)))
            last = set(s.users) - sur_users
            if len(last) == 1:
                winner = last.pop()
                s.winner = winner
                win_log = SessionLogs(user=winner.id, session=s.id, action="WIN",
                                      date=datetime.datetime.now())
                s.status = FINISHED
                db.session.add(win_log)
                db.sessions.commit()
                try:
                    Game.ServerGame().sessions[s.id].ended = True
                except KeyError as e:
                    print(e)
                send_session_end(s)
            db.session.add(surrender_log)
            db.session.commit()
            return ""
    else:
        print("wtf")
        return "User not in game", 400


@api.route("/sessions", methods=["GET"])
def get_session():
    if request.args.get("id"):
        s = Session.query.filter(Session.id == request.args["id"]).first()
        if s:
            response = {"id": s.id, "name": s.name, "desc": s.desc,
                        "limit": s.user_limit,
                        "status": s.status, "users": []}
            response["seed"] = s.seed
            for i in s.users:
                user = {"id": i.id, "name": i.name}
                if i.discord_id:
                    user["discord"] = int(i.discord_id)
                response["users"].append(user)
            response["seed"] = s.seed
            response["extra"] = s.extra
            if s.host:
                response["host"] = {"id": s.host.id, "name": s.host.name}
            return jsonify(response)
        else:
            return "Session not exist", 404
    else:
        response = []
        for s in Session.query.all():
            if s.status == FINISHED:
                continue
            serv = {"id": s.id, "name": s.name, "desc": s.desc, "limit": s.user_limit,
                    "status": s.status, "users": []}
            serv["seed"] = s.seed
            for i in s.users:
                user = {"id": i.id, "name": i.name}
                if i.discord_id:
                    user["discord"] = int(i.discord_id)
                serv["users"].append(user)
            if s.host:
                serv["host"] = {"id": s.host.id, "name": s.host.name}
            response.append(serv)
        return jsonify(response)


@api.route("/sessions/<int:id>/start", methods=["POST"])
@auth.login_required
def start_game(id):
    s = Session.query.filter(Session.id == id).first()
    if s:
        if s.users.count() < 2:
            return "You need more players", 400
        elif s.host != g.user:
            return "You not host in this game", 400
        elif s.status == STARTED:
            return "Game is started", 400
        else:
            s.status = STARTED
            s.seed = int(random() * 1e16)
            game = Game.ServerGame()
            game.create_fight(s.id, s.seed, s.users.count())
            db.session.commit()
            return "Game started successfully", 200
    else:
        return "Session not exist", 404


@api.route("/sessions/<int:id>/changes")
@auth.login_required
def get_session_changes(id):
    s = Session.query.filter(Session.id == id).first()
    if not s:
        return "Session not exist", 404
    elif g.user not in s.users:
        return "You are not in this session", 400
    elif s.status == FINISHED:
        log = SessionLogs.query.filter(SessionLogs.action == "WIN").filter(
            SessionLogs.session == id).first()
        if log:
            user = User.query.filter(User.id == log.user).first()
            response = [{"action": log.action, "data": json.loads(log.data) if log.data else {},
                         "player": user.name}]
        else:
            response = []
        return jsonify(response)
    elif s.status == PENDING:
        return "GAME NOT STARTED", 404
    last: SessionLogs = SessionLogs.query.filter(SessionLogs.session == id) \
        .filter(SessionLogs.action == "GET").filter(
        SessionLogs.user == g.user.id).order_by(
        -SessionLogs.id).first()
    now = datetime.datetime.now()
    if last:
        logs = SessionLogs.query.filter(SessionLogs.session == id) \
            .filter(last.date <= SessionLogs.date).filter(
            SessionLogs.date <= now).filter(SessionLogs.user != g.user.id).filter(
            SessionLogs.action != "GET").all()
        last.date = now
    else:
        logs = SessionLogs.query.filter(SessionLogs.session == id) \
            .filter(SessionLogs.date <= now).filter(
            SessionLogs.user != g.user.id).filter(SessionLogs.action != "GET").all()
        get_log = SessionLogs(user=g.user.id, session=s.id, action="GET", date=now)
        db.session.add(get_log)
    db.session.commit()
    response = []
    for log in logs:
        rr = {"action": log.action, "data": json.loads(log.data) if log.data else {}}
        if log.user != 0:
            user = User.query.filter(User.id == log.user).first()
            rr["player"] = user.name
        response.append(rr)
    return jsonify(response)


@api.route("/sessions/<int:id>/surrender", methods=["POST"])
@auth.login_required
def surrender(id):
    s = Session.query.filter(Session.id == id).first()
    surrender_log = SessionLogs(user=g.user.id, session=s.id, action="SURRENDER",
                                date=datetime.datetime.now())
    sur_users = {g.user}
    surs = SessionLogs.query.filter(SessionLogs.session == s.id).filter(
        SessionLogs.action == "SURRENDER").all()
    sur_users.update(set(map(lambda x: User.query.filter(User.id == x.user).first(), surs)))
    last = set(s.users) - sur_users
    if len(last) == 1:
        winner = last.pop()
        s.winner = winner
        win_log = SessionLogs(user=winner.id, session=s.id, action="WIN",
                              date=datetime.datetime.now())
        s.status = FINISHED
        db.session.add(win_log)
        db.session.commit()
        try:
            Game.ServerGame().sessions[s.id].ended = True
        except KeyError as e:
            print(e)
        send_session_end(s)
    db.session.add(surrender_log)
    db.session.commit()
    return ""


def check_action(u, s, action, param):
    player = -1
    game = Game.ServerGame()
    for ind, us in enumerate(s.users, 1):
        if us == u:
            player = ind
            break
    print(action, param, player)
    if player == -1:
        print("WTF")
        return False
    if action == "BUILD":
        print("build")
        return game.sessions[s.id].build(player, param)
    elif action == "MAKE_PATH":
        print("make path")
        return game.sessions[s.id].make_path(player, param["path"], param["removed"],
                                             param["added"])
    elif action == "DESTROY":
        print("destroy")
        return game.sessions[s.id].destroy(player, param["hexagon"])
    return False


@api.route("/sessions/<int:id>/action/<action>", methods=["POST"])
@auth.login_required
def execute_action(id, action):
    s = Session.query.filter(Session.id == id).first()
    if s.status == FINISHED:
        return "GAME FINISHED", 404
    elif s.status == PENDING:
        return "GAME NOT STARTED", 404
    elif g.user not in s.users:
        return "You are not in session", 400
    try:
        if check_action(g.user, s, action.upper(), request.json.get("data", {})):
            log = SessionLogs(user=g.user.id, session=s.id, action=action.upper(),
                              data=json.dumps(request.json.get("data", {})),
                              date=datetime.datetime.now())
            db.session.add(log)
            db.session.commit()
            return ""
        else:
            player = -1
            for ind, us in enumerate(s.users, 1):
                if us == g.user:
                    player = ind
                    break
            print("ERROR")
            game = Game.ServerGame()
            return jsonify({"wood": game.sessions[s.id].resources[player].wood,
                            "rocks": game.sessions[s.id].resources[player].rocks}), 400
    except Exception as e:
        print("Exception", e.args)
    player = -1
    for ind, us in enumerate(s.users, 1):
        if us == g.user:
            player = ind
            break
    game = Game.ServerGame()
    return jsonify({"wood": game.sessions[s.id].resources[player].wood,
                    "rocks": game.sessions[s.id].resources[player].rocks}), 400


@api.route("/friends", methods=["GET"])
@discord_auth.login_required
def get_friends():
    response = {"confirmed": [], "received": [], "requested": []}
    for f in g.user.friends:
        friend = {"name": f.name, "session": {}, "status": f.in_client}
        if f.discord_id:
            friend["discord"] = int(f.discord_id)
        if f.sessions.count():
            friend["session"]["id"] = f.sessions[0].id
            friend["session"]["status"] = f.sessions[0].status
            friend["session"]["name"] = f.sessions[0].name
        response["confirmed"].append(friend)
    for f in g.user.followers:
        friend = {"name": f.name, "session": {}, "status": f.in_client}
        if f.discord_id:
            friend["discord"] = int(f.discord_id)
        if f.sessions.count():
            friend["session"]["id"] = f.sessions[0].id
            friend["session"]["status"] = f.sessions[0].status
            friend["session"]["name"] = f.sessions[0].name
        response["received"].append(friend)
    for f in g.user.follows:
        friend = {"name": f.name, "session": {}, "status": f.in_client}
        if f.discord_id:
            friend["discord"] = int(f.discord_id)
        if f.sessions.count():
            friend["session"]["id"] = f.sessions[0].id
            friend["session"]["status"] = f.sessions[0].status
            friend["session"]["name"] = f.sessions[0].name
        response["requested"].append(friend)
    return jsonify(response)


@api.route("/friends/add", methods=["POST"])
@discord_auth.login_required
def add_friend():
    f = User.query.filter(User.name == request.form["friend-name"]).first_or_404()
    if f == g.user:
        return "You are your friend", 400
    if not f:
        return "User not exist", 404
    if f in g.user.friends:
        return "Friend already added", 400
    if f in g.user.follows:
        return "Request already sent", 400
    g.user.f_follows.append(f)
    db.session.commit()
    friend = {"friends": f in g.user.friends, "name": f.name, "session": {}}
    if f.discord_id:
        friend["discord"] = int(f.discord_id)
    if f.sessions.count():
        friend["session"]["id"] = f.sessions[0].id
        friend["session"]["status"] = f.sessions[0].status
        friend["session"]["name"] = f.sessions[0].name
    return jsonify(friend)


@api.route("/friends/remove", methods=["POST"])
@discord_auth.login_required
def remove_friend():
    f = User.query.filter(User.name == request.form["friend-name"]).first()
    if not f:
        return "User not exist", 404
    if f == g.user:
        return "You are your friend", 400
    if f not in g.user.follows and f not in g.user.friends:
        return "This user not friend", 404
    g.user.f_follows.remove(f)
    db.session.commit()
    return ""


# Webserver + bot


@api.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    rates = list(OrderedDict.fromkeys(map(lambda x: x[1],
                                          db.session.query(User, User.win_sessions_c).order_by(
                                              desc(User.win_sessions_c)).all())))
    res = users_to_json(users)
    for ind in range(len(users)):
        res[ind]["place"] = rates.index(res[ind]["wins"]) + 1
    return jsonify()


@api.route("/users/<name>")
def get_user(name):
    u = User.query.filter(
        (User.name == name) | (User.discord_id == name) | (User.id == name)).first_or_404()
    rates = list(OrderedDict.fromkeys(map(lambda x: x[1],
                                          db.session.query(User, User.win_sessions_c).order_by(
                                              desc(User.win_sessions_c)).all())))
    res = user_to_json(u)
    res["place"] = rates.index(u.win_sessions_c) + 1
    return jsonify(res)


@api.route("/top")
def get_top():
    users = User.query.order_by(desc(User.win_sessions_c)).all()
    count = request.args.get("count")
    if count and count.isdigit():
        count = int(count)
    else:
        count = 10
    return jsonify(users_to_json(users[:count]))


@api.route("/posts")
def get_posts():
    count = request.args.get("count")
    if count and count.isdigit():
        count = min(500, max(1, int(count)))
    else:
        count = 100
    posts = Post.query.order_by(desc(Post.date)).limit(count).all()
    return jsonify(posts_to_json(posts))


@api.route("/post/<slug>")
def get_post(slug):
    post = Post.query.filter(Post.slug == slug).first_or_404()
    return jsonify(post_to_json(post))


def user_to_json(u: User, full_sessions=False):
    user = {"name": u.name, "id": u.id, "wins": u.win_sessions_c, "loose": u.loose_sessions_c,
            "all": u.sessions_c, "link": "{}/profile/{}".format(request.url, u.name),
            "status": u.in_client}
    if full_sessions:
        user["sessions"] = sessions_to_json(u.sessions.all())
    else:
        user["sessions"] = [s.id for s in u.sessions]
    if u.discord_id:
        user["discord"] = int(u.discord_id)
    return user


def users_to_json(users, full_sessions=False):
    res = []
    for u in users:
        res.append(user_to_json(u, full_sessions))
    return res


def post_to_json(p: Post):
    post = {"title": p.title, "slug": p.slug, "desc": p.description, "author": p.author_id,
            "tags": [t.name for t in p.tags], "created": p.date.microsecond * 1000,
            "last_updated": p.last_edit.microsecond * 1000,
            "link": "{}blog/{}".format(request.host_url, p.slug)}
    if p.discord_id:
        post["discord"] = int(p.discord_id)
    if p.img:
        post["img"] = request.host_url[:-1] + p.img.path
    return post


def posts_to_json(posts):
    res = []
    for p in posts:
        res.append(post_to_json(p))
    return res


def tag_to_json(t: Tag, full_posts=False):
    tag = {"name": t.name}
    if full_posts:
        tag["posts"] = posts_to_json(t.posts.all())
    else:
        tag["posts"] = [p.id for p in t.posts]
    return tag


def tags_to_json(tags, full_posts=False):
    res = []
    for t in tags:
        res.append(t, full_posts)
    return res


def session_to_json(s: Session, full_users=False):
    session = {"name": s.name, "limit": s.user_limit, "status": s.status,
               "users": [{"name": u.name, "id": u.id} for u in s.users],
               "host": {"name": s.host.name, "id": s.host.id}}
    if s.seed:
        session["seed"] = s.seed
    # if full_users:
    #     session["host"] = user_to_json(s.host)
    return session


def sessions_to_json(sessions, full_users=False):
    res = []
    for s in sessions:
        res.append(s, full_users)
    return res
