from app.app import app, db
from app.models import User, UserSession

if __name__ == "__main__":
    db.create_all()
    app.run()
