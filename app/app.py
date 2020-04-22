import os
from datetime import datetime
from functools import wraps

from flask import Flask, g, session, redirect, request, url_for, jsonify, render_template, flash, \
    abort
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from requests_oauthlib import OAuth2Session

from .config import Config

app = Flask(__name__)
app.debug = True
app.config.from_object(Config)
mail = Mail(app)

db = SQLAlchemy(app)
from .models import User
from .users.blueprint import users, friends, f_discord
# if 'http://' in OAUTH2_REDIRECT_URI:
#     os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

app.register_blueprint(users, url_prefix="/")
app.register_blueprint(friends, url_prefix="/friends")
app.register_blueprint(f_discord, url_prefix="/discord")


@app.route("/")
@app.route("/index")
def home():
    return render_template("main/index.html")


@app.route("/rating")
@app.route("/rating/")
def rating():
    page = request.args.get("page")
    friends = request.args.get("friends") == "True"
    if page and page.isdigit():
        page = int(page)
    else:
        page = 1
    if friends and current_user.is_authenticated:
        query = User.query.filter(User.is_friends(current_user))
    else:
        query = User.query
    users = query.order_by(User.win_sessions_c).paginate(page=page, per_page=100)
    return render_template("main/rating.html", title="Рейтинг игроков", users=users)

# if __name__ == '__main__':
#     app.run()
