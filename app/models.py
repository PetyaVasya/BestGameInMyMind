import datetime

from sqlalchemy import func, select, alias, exists, table
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
import re
from sqlalchemy.orm import aliased

from .app import db
from flask_login import UserMixin

from sqlalchemy_utils import EmailType, PasswordType

from .constants import OFFLINE, PENDING
import transliterate


def slugify(s):
    pattern = r"[^\w+]"
    return transliterate.translit(re.sub(pattern, "-", s), reversed=True).replace("'", "")


relationship = db.Table('relationship',
                        db.Column('requesting_user_id', db.Integer, db.ForeignKey('user.id')),
                        db.Column('receiving_user_id', db.Integer, db.ForeignKey('user.id'))
                        )


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    __repr_attrs__ = ['name']
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True)
    discord_id = db.Column(db.String, unique=True, nullable=True)
    email = db.Column(EmailType, unique=True)
    admin = db.Column(db.Boolean, default=False, nullable=False)
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)
    notifications = db.Column(db.Boolean, default=True)
    password = db.Column(PasswordType(
        schemes=[
            'pbkdf2_sha512',
            'md5_crypt'
        ],

        deprecated=['md5_crypt']
    ))
    sessions = db.relationship("Session", secondary="user_session",
                               order_by="desc(UserSession.date)", lazy='dynamic')
    f_follows = db.relationship('User', secondary=relationship,
                                primaryjoin=(relationship.c.requesting_user_id == id),
                                secondaryjoin=(relationship.c.receiving_user_id == id),
                                backref=db.backref('f_followers', lazy='dynamic'),
                                lazy='dynamic')
    status = 0
    token_info = db.Column(db.String, nullable=True)
    posts = db.relationship("Post", order_by="desc(Post.date)", backref="author")
    # f_followers = db.relationship(
    #     'Relationship',
    #     foreign_keys='Relationship.receiving_user_id',
    #     backref='receiving_user'
    # )

    def check_password(self, password):
        return self.password == password

    def __repr__(self):
        return '<User "{}" {}>'.format(self.name, "ONLINE" if self.is_active else "OFFLINE")

    @hybrid_property
    def sessions_c(self):
        return 0

    @hybrid_property
    def win_sessions_c(self):
        return len(self.win_sessions)

    @win_sessions_c.expression
    def win_sessions_c(cls):
        return select([func.count(User.sessions)]). \
            where(Session.winner_id == cls.id). \
            label('total_balance')

    @hybrid_property
    def loose_sessions_c(self):
        return len(self.loose_sessions)

    @hybrid_property
    def win_sessions(self):
        return [s for s in self.sessions if s.winner == self]

    @hybrid_property
    def loose_sessions(self):
        return [s for s in self.sessions if s.winner != self]

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.confirmed

    @hybrid_property
    def friends(self):
        return tuple(set(self.f_follows) & set(self.f_followers))

    @friends.expression
    def friends(cls):
        left = relationship.alias("a")
        right = relationship.alias("b")
        a = select([relationship]).select_from(left.join(right,
                                                         (
                                                                 left.c.requesting_user_id == right.c.receiving_user_id) & (
                                                                 right.c.requesting_user_id == left.c.receiving_user_id))).group_by(
            relationship.c.requesting_user_id, relationship.c.receiving_user_id)
        b = select([User]).select_from(a).where(
            (relationship.c.requesting_user_id == cls.id)).group_by(User.id)
        return b

    @hybrid_property
    def follows(self):
        return tuple(set(self.f_follows) - set(self.f_followers))

    @hybrid_property
    def followers(self):
        return tuple(set(self.f_followers) - set(self.f_follows))

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)
            return self

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)
            return self

    def is_following(self, user):
        return self.followed.filter(relationship.c.requesting_user_id == user.id).count() > 0

    @hybrid_method
    def is_friends(self, user):
        return user in self.friends

    @is_friends.expression
    def is_friends(cls, user):
        left = relationship.alias("a")
        right = relationship.alias("b")
        # a = left.join(right,
        #               left.c.requesting_user_id == right.c.receiving_user_id
        #               | left.c.receiving_user_id == right.c.requesting_user_id)
        # print(select(User).join(a, cls.id == a.left.c.requesting_user_id
        #                            | cls.id == a.left.c.receiving_user_id))
        # print(table("user").join(left, left.c.requesting_user_id == cls.id))
        # print(select([User]).join(a, ))
        a = select([relationship]).select_from(left.join(right,
                                                         (
                                                                 left.c.requesting_user_id == right.c.receiving_user_id) & (
                                                                 right.c.requesting_user_id == left.c.receiving_user_id))).group_by(
            relationship.c.requesting_user_id, relationship.c.receiving_user_id)
        # print(a)
        # b = select([User]).select_from(left.join(right,
        #               left.c.requesting_user_id == right.c.receiving_user_id)).where((left.c.receiving_user_id == user.id) & (left.c.requesting_user_id == cls.id))
        # b = select([User]).join(a, (right.c.receiving_user_id == user.id) | (left.c.receiving_user_id == user.id))
        # f_user = aliased(User, name="u1")
        # s_user = aliased(User, name="u2")
        # print(a.join(f_user, relationship.c.requesting_user_id == f_user.id).join(s_user, relationship.c.receiving_user_id == s_user.id))
        # print(select([User]).select_from(relationship).where((relationship.c.requesting_user_id == user.id) & (relationship.c.receiving_user_id == cls.id)))
        b = select([User.id]).select_from(a).where((relationship.c.requesting_user_id == cls.id) & (
                relationship.c.receiving_user_id == user.id))
        # print(a)
        # b = select([User.id]).join(a, (relationship.c.requesting_user_id == cls.id) & (
        #              relationship.c.receiving_user_id == user.id))
        # print(b)
        # print(b.c)
        # print(select([User]).c)
        # return select([User]).label("user")
        # print(cls.id.in_(select([User.id])))
        # print(cls.id.in_(b))
        # return cls.id.in_(b)
        return (b)


class Session(db.Model):
    __tablename__ = "session"
    __repr_attrs = ["user", "name", "status"]

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_limit = db.Column(db.Integer, default=2)
    name = db.Column(db.String(50), nullable=False)
    desc = db.Column(db.String(300), nullable=True)
    host_id = db.Column(db.Integer, nullable=True)
    # users = db.relationship(
    #     'UserSession',
    #     foreign_keys='UserSession.session_id',
    #     backref='session',
    #     order_by='UserSession.date'
    # )
    users = db.relationship("User", secondary="user_session", order_by="UserSession.date",
                            lazy='dynamic')
    status = db.Column(db.Integer, default=PENDING)
    seed = db.Column(db.Integer, nullable=True)
    extra = db.Column(db.String(1000), nullable=True)
    winner_id = db.Column(db.Integer, nullable=True)

    @hybrid_property
    def winner(self):
        return User.query.filter(User.id == self.winner_id).first()

    @winner.expression
    def winner(cls):
        return select([User]).where(cls.winner_id == User.id)


class UserSession(db.Model):
    __tablename__ = "user_session"
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), primary_key=True)
    # users = db.relationship("User", backref="sessions")
    # session = db.relationship("Session", backref="users")
    user = db.relationship(User, backref=db.backref("user_session", cascade="all, delete-orphan",
                                                    lazy='dynamic'))
    session = db.relationship(Session,
                              backref=db.backref("user_session", cascade="all, delete-orphan",
                                                 lazy='dynamic'))
    date = db.Column(db.DateTime, default=datetime.datetime.now())


class SessionLogs(db.Model):
    __tablename__ = "session_logs"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user = db.Column(db.Integer, db.ForeignKey('user.id'))
    session = db.Column(db.Integer, db.ForeignKey('session.id'))
    action = db.Column(db.String)
    data = db.Column(db.String, default="{}")
    date = db.Column(db.DateTime, default=datetime.datetime.now())


post_tags = db.Table("post_tag",
                     db.Column('post_id', db.Integer, db.ForeignKey('post.id')),
                     db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                     )


class Post(db.Model):
    __tablename__ = "post"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(140), nullable=False)
    slug = db.Column(db.String(140), unique=True)
    description = db.Column(db.String, nullable=True)
    discord_id = db.Column(db.String, nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    img_id = db.Column(db.Integer, db.ForeignKey("file.id"), nullable=True)
    date = db.Column(db.DateTime, default=datetime.datetime.now)
    last_edit = db.Column(db.DateTime, onupdate=datetime.datetime.now)
    tags = db.relationship("Tag",
                           secondary=post_tags,
                           backref=db.backref("posts", lazy="dynamic"),
                           lazy="dynamic")

    def __init__(self, *args, **kwargs):
        super(Post, self).__init__(*args, **kwargs)
        # self.slug = self.generate_slug()
        self.generate_slug()

    def generate_slug(self):
        slug = slugify(self.title)
        c = max(0, Post.query.filter(Post.slug == slug).count() - 1)
        self.slug = slug + ("-{}".format(c + 1) if c else "")

    def __repr__(self):
        return "<Post {} title: '{}'>".format(self.id, self.title)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100))
    slug = db.Column(db.String(100), unique=True)

    def __init__(self, *args, **kwargs):
        super(Tag, self).__init__(*args, **kwargs)
        self.generate_slug()

    def generate_slug(self):
        slug = slugify(self.name)
        c = max(0, Tag.query.filter(Tag.slug == slug).count() - 1)
        self.slug = slug + ("-{}".format(c + 1) if c else "")

    def __repr__(self):
        return "<Tag {} name: '{}'>".format(self.id, self.name)


class File(db.Model):
    __tablename__ = "file"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    path = db.Column(db.String)
    type = db.Column(db.String)
    date = db.Column(db.Date, default=datetime.datetime.now)
    posts = db.relationship("Post", backref="img")

    def __repr__(self):
        return "<File {} >".format(self.name)