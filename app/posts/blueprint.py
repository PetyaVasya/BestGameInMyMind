from flask import Blueprint, render_template, url_for, request

from app.models import Post, Tag

posts = Blueprint("posts", __name__, template_folder="templates")


@posts.route("/")
def index():
    page = request.args.get("page")
    if page and page.isdigit():
        page = int(page)
    else:
        page = 1
    posts = Post.query.paginate(page=page, per_page=10)
    return render_template("posts/index.html", posts=posts)


@posts.route("/<slug>")
def post_detail(slug):
    post = Post.query.filter(Post.slug == slug).first_or_404()
    render_template("posts/post_detail.html", post=post, tags=post.tags.all())


@posts.route("/tag/<slug>")
@posts.route("/tag/<slug>/")
def tag_detail(slug):
    page = request.args.get("page")
    if page and page.isdigit():
        page = int(page)
    else:
        page = 1
    tag = Tag.query.filter(Tag.slug == slug).first_or_404()
    posts = tag.posts.paginate(page=page, per_page=10)
    return render_template("posts/tag_detail.html", posts=posts, tag=tag)


@posts.errorhandler(404)
def error404():
    return render_template("posts/404.html")
