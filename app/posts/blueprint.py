import os

from flask import Blueprint, render_template, url_for, request
from flask_breadcrumbs import register_breadcrumb
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.app import app, db
from app.models import Post, Tag
from app.posts.forms import PostForm

posts = Blueprint("posts", __name__, template_folder="templates")


@posts.errorhandler(404)
def error404(e):
    return render_template("posts/404.html")


@posts.route("/")
@register_breadcrumb(posts, '.', 'Блог')
def index():
    page = request.args.get("page")
    if page and page.isdigit():
        page = int(page)
    else:
        page = 1
    posts = Post.query.order_by(Post.date.desc()).paginate(page=page, per_page=10)
    return render_template("posts/index.html", posts=posts)


def post_detail_breadcrumbs(*args, **kwargs):
    slug = request.view_args['slug']
    post = Post.query.filter(Post.slug == slug).first()
    if not post:
        return [{'text': "Ошибка", 'url': ""}]
    return [{'text': post.title, 'url': url_for("posts.post_detail", slug=post.slug)}]


@posts.route("/<slug>")
@register_breadcrumb(posts, '.post-slug', '', dynamic_list_constructor=post_detail_breadcrumbs)
def post_detail(slug):
    post = Post.query.filter(Post.slug == slug).first_or_404()
    return render_template("posts/post_detail.html", post=post, tags=post.tags.all())


def tag_detail_breadcrumbs(*args, **kwargs):
    slug = request.view_args['slug']
    tag = Tag.query.filter(Tag.slug == slug).first()
    if not tag:
        return [{'text': "Ошибка", 'url': ""}]
    return [{'text': 'Тег', 'url': ""},
            {'text': tag.name, 'url': url_for("posts.tag_detail", slug=tag.slug)}]


@posts.route("/tag/<slug>")
@posts.route("/tag/<slug>/")
@register_breadcrumb(posts, '.tag-slug', '', dynamic_list_constructor=tag_detail_breadcrumbs)
def tag_detail(slug):
    page = request.args.get("page")
    if page and page.isdigit():
        page = int(page)
    else:
        page = 1
    tag = Tag.query.filter(Tag.slug == slug).first_or_404()
    posts = tag.posts.order_by(Post.date.desc()).paginate(page=page, per_page=10)
    return render_template("posts/tag_detail.html", posts=posts, tag=tag)

# @posts.route("/create", methods=["POST", "GET"])
# @login_required
# def create_post():
#     form = PostForm()
#     if form.validate_on_submit():
#         try:
#             post = Post(title=form.title, description=form.description, author_id=current_user.id)
#             if form.file:
#                 filename = secure_filename(form.file.filename)
#                 path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#                 form.file.save(path)
#                 post.img = path
#                 db.session.add(post)
#                 db.session.commit()
#         except Exception as e:
#             print(e)
#
#     return render_template("posts/create_post.html", form=form)
