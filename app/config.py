import datetime
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'db/app.db')
    OAUTH2_CLIENT_ID = os.environ.get('OAUTH2_CLIENT_ID', "702101622762766347")
    OAUTH2_CLIENT_SECRET = os.environ.get('OAUTH2_CLIENT_SECRET',
                                          "72_eMJRHIvjFttxCdRC2hPXSY_spKGTY")
    OAUTH2_REDIRECT_URI = 'http://aa69bc2a.ngrok.io/discord/callback'
    UPLOAD_FOLDER = "static/img/upload"

    API_BASE_URL = os.environ.get('API_BASE_URL', 'https://discordapp.com/api')
    AUTHORIZATION_BASE_URL = API_BASE_URL + '/oauth2/authorize'
    TOKEN_URL = API_BASE_URL + '/oauth2/token'
    REVOKE_URL = TOKEN_URL + '/revoke'
    SECURITY_PASSWORD_SALT = 'my_precious_two'
    SECRET_KEY = os.environ.get("SECRET_KEY", OAUTH2_CLIENT_SECRET)
    DISCORD_SERVER_ID = os.environ.get("DISCORD_SERVER_ID", "702102338713944104")
    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "NzAyMTAxNjIyNzYyNzY2MzQ3.Xq"
                                                    "VJhA.NM1NU5LBnNUjOHbSiM5JIuslswM")
    WEBHOOK_NEWS_ID = os.environ.get("WEBHOOK_NEWS_ID", "704339781810913363")
    WEBHOOK_NEWS_TOKEN = os.environ.get("WEBHOOK_NEWS_TOKEN",
                                        "KgbrBlPg5fGdMypnlHsIaCW0KLgff82ue4FbZmFp_"
                                        "4Qj7s3Nk1mWIiPKTWYKQiNiYIse")
    WEBHOOK_SESSION_ID = os.environ.get("WEBHOOK_SESSION_ID", "704339787754242188")
    WEBHOOK_SESSION_TOKEN = os.environ.get("WEBHOOK_SESSION_TOKEN",
                                        "gbdmnWyNGR6cdfLiDoTInH8NfJ6KEb3FrgN"
                                        "4TcCtBJD3178m9AT4MFOff6GIZYNgULd4")
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
