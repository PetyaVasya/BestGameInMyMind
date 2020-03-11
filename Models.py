import flask
# from sqlalchemy import Column, Integer, String, Table, ForeignKey
# from sqlalchemy.orm import relationship, backref
from sqlalchemy_utils import EmailType, PasswordType
from Database import db
from sqlalchemy_mixins import AllFeaturesMixin
from constants import *


class Session(db.Model, AllFeaturesMixin):
    __tablename__ = "session"
    __repr_attrs = ["users", "name", "status"]

    id = db.Column(db.Integer, primary_key=True)
    user_limit = db.Column(db.Integer, default=2)
    name = db.Column(db.String(50), nullable=False)
    desc = db.Column(db.String(300), nullable=True)
    # host = relationship("User", backref=backref("parents", uselist=False))
    users = db.relationship("User", backref="session")
    status = db.Column(db.Integer, default=PENDING)
    seed = db.Column(db.Integer, nullable=True)
    extra = db.Column(db.String(1000), nullable=True)


class User(db.Model, AllFeaturesMixin):
    __tablename__ = 'user'
    __repr_attrs__ = ['name']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    email = db.Column(EmailType, unique=True)
    password = db.Column(PasswordType(
        schemes=[
            'pbkdf2_sha512',
            'md5_crypt'
        ],

        deprecated=['md5_crypt']
    ))
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=True)
    status = db.Column(db.Integer, default=OFFLINE)
    friends = db.relationship(
        'Relationship',
        foreign_keys='Relationship.requesting_user_id',
        backref='requesting_user'
    )
    p_friends = db.relationship(
        'Relationship',
        foreign_keys='Relationship.receiving_user_id',
        backref='receiving_user'
    )

    def __repr__(self):
        return '<User "{}" {}>'.format(self.name,  "ONLINE" if self.status - 1 else "OFFLINE")


class Relationship(db.Model, AllFeaturesMixin):
    __tablename__ = "relationship"
    __repr_attrs__ = ["status"]

    requesting_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    receiving_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    status = db.Column(db.Integer)
