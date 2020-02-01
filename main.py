from flask import Flask, jsonify
from generator import generate


app = Flask(__name__)


@app.route("/new/game/<session>/")
def create_game(session):
    return jsonify(generate(session))


if __name__ == "__main__":
    app.run()
