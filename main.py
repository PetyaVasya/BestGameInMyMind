from app.app import app, db
from app.models import User, UserSession, Role

if __name__ == "__main__":
    db.create_all()
    if not Role.query.filter(Role.name == "admin").first():
        db.session.add(Role(name="admin"))
        db.session.commit()
    app.run()
