import threading

from flask import copy_current_request_context
from flask_mail import Message

from app.app import app
from app.app import mail


def send_email(to, subject, template):
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=app.config['MAIL_DEFAULT_SENDER']
    )
    mail.send(msg)


def send_email_async(to, subject, template):
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=app.config['MAIL_DEFAULT_SENDER']
    )

    @copy_current_request_context
    def send_message(message):
        mail.send(message)

    sender = threading.Thread(name='mail_sender', target=send_message, args=(msg,))
    sender.start()