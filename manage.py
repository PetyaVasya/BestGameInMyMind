from app.app import app, db
from app.models import User, UserSession, SessionLogs, Session, relationship, Post, Tag
from app.app import manager

if __name__ == "__main__":
    manager.run()
