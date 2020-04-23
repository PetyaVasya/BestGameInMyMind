import json
from datetime import datetime
from functools import wraps

import requests
from flask import Blueprint, redirect, render_template, url_for, flash, jsonify, request, session
from flask_breadcrumbs import register_breadcrumb, default_breadcrumb_root
from flask_login import current_user, login_user, login_required, logout_user, LoginManager
from requests_oauthlib import OAuth2Session

from .forms import LoginForm, RegistrationForm
from app.app import db, app
from app.email import send_email
from app.models import User
from app.token import generate_confirmation_token, confirm_token

login_manager = LoginManager()
login_manager.init_app(app)

users = Blueprint("users", __name__, template_folder="templates")
default_breadcrumb_root(users, '.')

def check_confirmed(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user.confirmed is False:
            flash('Пожалуйста, подтвердите свой аккаунт', 'warning')
            return redirect(url_for('users.unconfirmed'))
        return func(*args, **kwargs)

    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)


@login_manager.unauthorized_handler
def catch():
    return redirect("/")


@users.errorhandler(404)
def error404(e):
    return render_template("users/404.html")


@users.route('/login', methods=['GET', 'POST'])
@register_breadcrumb(users, '.login', 'Авторизация')
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter(User.email == form.email.data).first()
        login_user(user, remember=form.remember_me.data)
        return redirect("/")
    return render_template('users/login.html', title='Авторизация', form=form)


@users.route('/registration', methods=['GET', 'POST'])
@register_breadcrumb(users, '.registration', 'Регистрация')
def registration():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(name=form.name.data, email=form.email.data, password=form.password.data,
                        confirmed=False)
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            print(e)
        token = generate_confirmation_token(user.email)
        confirm_url = url_for('users.confirm_email', token=token, _external=True)
        html = render_template('users/activate.html', confirm_url=confirm_url)
        subject = "Пожалуйста, подтвердите свою почту"
        send_email(user.email, subject, html)
        login_user(user)
        flash('Письмо для подтверждения было отправленно', 'success')
        return redirect(url_for("users.unconfirmed"))
    return render_template('users/registration.html', title='Регистрация', form=form)


@users.route('/confirm/<token>')
@register_breadcrumb(users, '.confirmation', 'Подтверждение почты')
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('Ссылка для подтверждения больше не работает.', 'danger')
    user = User.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash('Аккаунт уже подтвержден. Пожалуйста, авторизуйтесь.', 'success')
    else:
        user.confirmed = True
        user.confirmed_on = datetime.now()
        db.session.commit()
        flash('Вы подтвердили аккаунт. Спасибо!', 'success')
    return redirect("/")


@users.route('/unconfirmed')
@login_required
@register_breadcrumb(users, '.unconfirmed', 'Профиль')
def unconfirmed():
    if current_user.confirmed:
        return redirect("/")
    flash('Пожалуйста, подтвердите аккаунт!', 'warning')
    return render_template('users/unconfirmed.html')


@users.route('/resend')
@login_required
@register_breadcrumb(users, '.resend', 'Профиль')
def resend_confirmation():
    token = generate_confirmation_token(current_user.email)
    confirm_url = url_for('users.confirm_email', token=token, _external=True)
    html = render_template('users/activate.html', confirm_url=confirm_url)
    subject = "Пожалуйста, подтвердите ваш электронный адресс"
    send_email(current_user.email, subject, html)
    flash('Новое письмо для подтверждения отправленно', 'success')
    return redirect(url_for('users.unconfirmed'))


@users.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


def profile_breadcrumbs(*args, **kwargs):
    name = request.view_args.get('name')
    if not name:
        return [{'text': 'Профиль', 'url': url_for("users.profile")}]
    user = User.query.filter(User.name == name).first()
    if not user:
        return [{'text': 'Профиль', 'url': url_for("users.profile")}, {'text': "Ошибка", 'url': ""}]
    return [{'text': 'Профиль', 'url': url_for("users.profile")}, {'text': user.name, 'url': url_for("users.profile", name=user.name)}]


@users.route("/profile")
@users.route("/profile/<name>")
@login_required
@check_confirmed
@register_breadcrumb(users, '.profile', '', dynamic_list_constructor=profile_breadcrumbs)
def profile(name=""):
    page = request.args.get("page")
    if page and page.isdigit():
        page = int(page)
    else:
        page = 1
    if name and name != current_user.name:
        user = User.query.filter(User.name == name).first_or_404()
        sessions = user.sessions.paginate(page=page, per_page=10)
        return render_template("users/profile.html", title="Профиль: " + name,
                               user=user, sessions=sessions)
    if current_user.token_info:
        discord_s = make_session(token=json.loads(current_user.token_info))
        user = discord_s.get(app.config["API_BASE_URL"] + '/users/@me').json()
        if user.get('message') and user["message"] == "401: Unauthorized":
            user = {}
            session["oauth2_token"] = None
    else:
        user = {}
    sessions = current_user.sessions.paginate(page=page, per_page=10)
    return render_template("users/profile.html", title="Профиль", user=current_user,
                           discord_user=user, sessions=sessions)


friends = Blueprint("friends", __name__, template_folder="templates")


@friends.route("/", methods=["GET"])
@login_required
def get_friends():
    response = {"confirmed": [], "received": [], "requested": []}
    for f in current_user.friends:
        friend = {"name": f.name, "status": f.status, "session": {}}
        if f.sessions:
            friend["session"]["id"] = f.sessions[0].id
            friend["session"]["status"] = f.sessions[0].status
            friend["session"]["name"] = f.sessions[0].name
        response["confirmed"].append(friend)
    for f in current_user.followers:
        friend = {"name": f.name, "status": f.status, "session": {}}
        if f.sessions:
            friend["session"]["id"] = f.sessions[0].id
            friend["session"]["status"] = f.sessions[0].status
            friend["session"]["name"] = f.sessions[0].name
        response["received"].append(friend)
    for f in current_user.follows:
        friend = {"name": f.name, "status": f.status, "session": {}}
        if f.sessions:
            friend["session"]["id"] = f.sessions[0].id
            friend["session"]["status"] = f.sessions[0].status
            friend["session"]["name"] = f.sessions[0].name
        response["requested"].append(friend)
    return jsonify(response)


@friends.route("/add", methods=["POST"])
@login_required
def add_friend():
    f = User.query.filter(User.name == request.form["name"]).first()
    if f == current_user:
        return "You are your friend", 400
    if not f:
        return "User not exist", 404
    if f in current_user.friends:
        return "Friend already added", 400
    if f in current_user.follows:
        return "Request already sent", 400
    current_user.f_follows.append(f)
    db.session.commit()
    friend = {"friends": f in current_user.friends, "name": f.name, "status": f.status,
              "session": {}}
    if f.sessions:
        friend["session"]["id"] = f.sessions[0].id
        friend["session"]["status"] = f.sessions[0].status
        friend["session"]["name"] = f.sessions[0].name
    return jsonify(friend)


@friends.route("/remove", methods=["POST"])
@login_required
def remove_friend():
    f = User.query.filter(User.name == request.form["name"]).first()
    if not f:
        return "User not exist", 404
    if f == current_user:
        return "You are your friend", 400
    if f not in current_user.follows and f not in current_user.friends:
        return "This user not friend and not in you follows", 404
    print(current_user.f_follows)
    current_user.f_follows.remove(f)
    db.session.commit()
    return ""


def token_updater(token):
    session['oauth2_token'] = token


def make_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=app.config["OAUTH2_CLIENT_ID"],
        token=token,
        state=state,
        scope=scope,
        redirect_uri=app.config["OAUTH2_REDIRECT_URI"],
        auto_refresh_kwargs={
            'client_id': app.config["OAUTH2_CLIENT_ID"],
            'client_secret': app.config["OAUTH2_CLIENT_SECRET"],
        },
        auto_refresh_url=app.config["TOKEN_URL"],
        token_updater=token_updater)


f_discord = Blueprint("discord", __name__, template_folder="templates")


@f_discord.route('/login')
@login_required
def discord_login():
    scope = request.args.get(
        'scope',
        'identify email connections guilds guilds.join')
    discord_s = make_session(scope=scope.split(' '))
    authorization_url, state = discord_s.authorization_url(app.config["AUTHORIZATION_BASE_URL"])
    session['oauth2_state'] = state
    return redirect(authorization_url)


@f_discord.route('/callback')
@login_required
def callback():
    if request.values.get('error'):
        return redirect(url_for('users.profile'))
    discord_s = make_session(state=session.get('oauth2_state'))
    token = discord_s.fetch_token(
        app.config["TOKEN_URL"],
        client_secret=app.config["OAUTH2_CLIENT_SECRET"],
        authorization_response=request.url.replace("http", "https"))
    current_user.discord_id = discord_s.get(app.config["API_BASE_URL"] + '/users/@me').json()["id"]
    current_user.token_info = json.dumps(token)
    db.session.commit()
    return redirect(url_for('users.profile'))


# @f_discord.route('/revoke')
# @login_required
# def revoke():
#     if session.get("oauth2_token"):
#         discord_s = make_session(token=session['oauth2_token'])
#         print(requests.post(app.config["REVOKE_URL"], {"access_token": session["oauth2_token"]["access_token"]}).text)
#         # print(discord_s.post(discord_s.authorization_url(app.config["REVOKE_URL"])[0], {"access_token": session["oauth2_token"]["access_token"]}).text)
#         # session["oauth2_token"] = None
#         # url = discord_s.authorization_url(app.config["REVOKE_URL"])[0]
#         # url += "&access_token=%s&client_secret=%s" % (session["oauth2_token"]["access_token"], app.config["OAUTH2_CLIENT_SECRET"])
#         print(discord_s.request("post", app.config["REVOKE_URL"], withhold_token=True).text)
#         print(discord_s.request("post", app.config["REVOKE_URL"], {"access_token": session["oauth2_token"]["access_token"]}, client_id=app.config["OAUTH2_CLIENT_ID"], client_secret=app.config["OAUTH2_CLIENT_SECRET"]).text)
#         return redirect(url_for("users.profile"))
#         # return redirect(url)
#     return redirect(url_for("users.profile"))
#
#
# @discord.route('/me')
# def me():
#     discord = make_session(token=session.get('oauth2_token'))
#     users = discord.get(API_BASE_URL + '/users/@me').json()
#     guilds = discord.get(API_BASE_URL + '/users/@me/guilds').json()
#     connections = discord.get(API_BASE_URL + '/users/@me/connections').json()
#     return jsonify(users=users, guilds=guilds, connections=connections)
