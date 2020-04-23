from flask import Flask, request, render_template, session, redirect, url_for
from flask_login import current_user
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy

from .config import Config

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager

app = Flask(__name__)
app.debug = True
app.config.from_object(Config)
mail = Mail(app)

db = SQLAlchemy(app)
from .models import *
from .users.blueprint import users, friends, f_discord
from .posts.blueprint import posts
# if 'http://' in OAUTH2_REDIRECT_URI:
#     os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

app.register_blueprint(users, url_prefix="/")
app.register_blueprint(friends, url_prefix="/friends")
app.register_blueprint(f_discord, url_prefix="/discord")
app.register_blueprint(posts, url_prefix="/blog")

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command("db", MigrateCommand)


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


@app.route("/search")
@app.route("/search/")
def search():
    page = request.args.get("page")
    q = request.args.get("q", "")
    players = request.args.get("players") == "True"
    if page and page.isdigit() and session.get("search_players") == players:
        page = int(page)
    else:
        page = 1
    session["search_players"] = players
    if q:
        if players:
            res = User.query.filter(User.name.contains(q))
        else:
            res = Post.query.filter(Post.title.contains(q) | Post.description.contains(q))
    else:
        return redirect(url_for("posts.index"))
    res = res.paginate(page=page, per_page=10)
    return render_template("main/search.html", res=res)


# if __name__ == '__main__':
#     app.run()
