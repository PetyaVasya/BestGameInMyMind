import os
import random

from flask import Flask, request, render_template, session, redirect, url_for
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import FileUploadField
from flask_login import current_user
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from werkzeug.utils import secure_filename
from jinja2 import Markup

from .config import Config

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_admin import Admin
from flask_breadcrumbs import Breadcrumbs, register_breadcrumb

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
Breadcrumbs(app=app)

class SlugModelView(ModelView):

    def after_model_change(self, form, model, is_created):
        model.generate_slug()
        db.session.commit()


class FileModelView(ModelView):

    form_extra_fields = {
        'file': FileUploadField('file', base_path=".")
    }

    # form_excluded_columns = {
    #     "path", "name", "type"
    # }

    def _change_path_data(self, _form):
        try:
            storage_file = _form.file.data

            if storage_file is not None:
                ext = storage_file.filename.split('.')[-1]
                filename = secure_filename(
                    str(abs(hash(str(datetime.datetime.now().microsecond) + secure_filename(
                        storage_file.filename))))) + "." + ext
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                storage_file.save(os.path.join("./app", path))

                _form.name.data = _form.name.data or filename
                _form.path.data = os.path.join("/", path)
                _form.type.data = ext

                del _form.file

        except Exception as e:
            print(e)

        return _form

    def edit_form(self, obj=None):
        return self._change_path_data(
            super(FileModelView, self).edit_form(obj)
        )

    def create_form(self, obj=None):
        return self._change_path_data(
            super(FileModelView, self).create_form(obj)
        )

    def _list_thumbnail(view, context, model, name):
        if not model.path:
            return ''

        if model.type in ['jpg', 'jpeg', 'png', 'svg', 'gif']:
            return Markup('<img src="%s" width="100">' % model.path)

        if model.type in ['mp3']:
            return Markup(
                '<audio controls="controls"><source src="%s" type="audio/mpeg" /></audio>' % model.path)

    column_formatters = {
        'path': _list_thumbnail
    }


admin = Admin(app)
admin.add_view(ModelView(User, db.session))
admin.add_view(SlugModelView(Post, db.session))
admin.add_view(SlugModelView(Tag, db.session))
admin.add_view(ModelView(Session, db.session))
admin.add_view(FileModelView(File, db.session))


# admin.add_view(ModelView(relationship, db.session))


@app.route("/")
@app.route("/index")
@register_breadcrumb(app, '.', 'Главная')
def home():
    return render_template("main/index.html")


@app.route("/rating")
@app.route("/rating/")
@register_breadcrumb(app, '.rating', 'Рейтинг')
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
@register_breadcrumb(app, '.search', 'Поиск')
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
            res = User.query.filter(User.name.contains(q)).order_by(desc(User.win_sessions_c))
        else:
            res = Post.query.filter(Post.title.contains(q) | Post.description.contains(q)).order_by(
                Post.date.desc())
    else:
        return redirect(url_for("posts.index"))
    res = res.paginate(page=page, per_page=10)
    return render_template("main/search.html", res=res)

# if __name__ == '__main__':
#     app.run()