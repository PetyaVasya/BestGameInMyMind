import flask
from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy_utils import EmailType, PasswordType
from Database import Base
from sqlalchemy_mixins import AllFeaturesMixin
from constants import *


class Session(Base, AllFeaturesMixin):
    __tablename__ = "session"
    __repr_attrs = ["users", "name", "status"]

    id = Column(Integer, primary_key=True)
    user_limit = Column(Integer, default=2)
    name = Column(String(50), nullable=False)
    desc = Column(String(300), nullable=True)
    # host = relationship("User", backref=backref("parents", uselist=False))
    users = relationship("User", backref="session")
    status = Column(Integer, default=PENDING)
    seed = Column(Integer, nullable=True)


class User(Base, AllFeaturesMixin):
    __tablename__ = 'user'
    __repr_attrs__ = ['name']
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    email = Column(EmailType, unique=True)
    password = Column(PasswordType(
        schemes=[
            'pbkdf2_sha512',
            'md5_crypt'
        ],

        deprecated=['md5_crypt']
    ))
    session_id = Column(Integer, ForeignKey('session.id'), nullable=True)
    status = Column(Integer, default=OFFLINE)
    friends = relationship(
        'Relationship',
        foreign_keys='Relationship.requesting_user_id',
        backref='requesting_user'
    )
    p_friends = relationship(
        'Relationship',
        foreign_keys='Relationship.receiving_user_id',
        backref='receiving_user'
    )


class Relationship(Base, AllFeaturesMixin):
    __tablename__ = "relationship"
    __repr_attrs__ = ["status"]

    requesting_user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    receiving_user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    status = Column(Integer)
