from flask import Flask


app = Flask(__name__)


@app.route("/create/party")
def new_session():
    return "it's a cart"


if __name__ == "__main__":
    app.run()
