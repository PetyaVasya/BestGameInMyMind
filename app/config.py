import datetime
import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'db/app.db')
    OAUTH2_CLIENT_ID = os.environ.get('OAUTH2_CLIENT_ID', "702101622762766347")
    OAUTH2_CLIENT_SECRET = os.environ.get('OAUTH2_CLIENT_SECRET',
                                          "72_eMJRHIvjFttxCdRC2hPXSY_spKGTY")
    OAUTH2_REDIRECT_URI = 'http://127.0.0.1:5000/discord/callback'
    UPLOAD_FOLDER = "static/img/upload"

    API_BASE_URL = os.environ.get('API_BASE_URL', 'https://discordapp.com/api')
    AUTHORIZATION_BASE_URL = API_BASE_URL + '/oauth2/authorize'
    TOKEN_URL = API_BASE_URL + '/oauth2/token'
    REVOKE_URL = TOKEN_URL + '/revoke'
    SECURITY_PASSWORD_SALT = 'my_precious_two'
    SECRET_KEY = os.environ.get("SECRET_KEY", OAUTH2_CLIENT_SECRET)
    DISCORD_SERVER_ID = os.environ.get("DISCORD_SERVER_ID", "702102338713944104")
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=365)

    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 465
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True

    # gmail authentication
    MAIL_USERNAME = os.environ.get('APP_MAIL_USERNAME', "bestgameinmymind@gmail.com")
    MAIL_PASSWORD = os.environ.get('APP_MAIL_PASSWORD', "viVrij-gaswac-nytvy1")

    # mail accounts
    MAIL_DEFAULT_SENDER = '123@gmail.com'


    SQLALCHEMY_TRACK_MODIFICATIONS = False