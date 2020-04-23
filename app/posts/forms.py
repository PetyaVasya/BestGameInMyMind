from flask_wtf import FlaskForm
from wtforms import PasswordField, BooleanField, SubmitField, StringField, TextAreaField, FileField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

from app.models import User, Post


class PostForm(FlaskForm):
    title = StringField('Название поста', validators=[DataRequired()])
    img = FileField("Изображение")
    description = TextAreaField('Описание')

    def validate_img(self, img):
        if img and not allowed_file(img.filename):
            raise ValidationError("Недопустимое расширение файла")


class TagForm(FlaskForm):
    name = StringField('Никнейм', validators=[DataRequired()])
    email = StringField('Почта', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password2 = PasswordField(
        'Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    def validate_name(self, name):
        user = User.query.filter_by(name=name.data).first()
        if user is not None:
            raise ValidationError('Данный никнейм уже занят')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Данная почта уже занята')
