from flask_wtf import FlaskForm
from wtforms import PasswordField, BooleanField, SubmitField, StringField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

from app.models import User


class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

    def validate(self):
        if not super().validate():
            return False
        user = User.query.filter_by(email=self.email.data).first()
        if user is None:
            self.email.errors.append('Пользователя с такой почтой не существует')
            return False
        if not user.check_password(self.password.data):
            self.password.errors.append('Неверный пароль')
            return False
        return True


class RegistrationForm(FlaskForm):
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
        if name.data.isdigit():
            raise ValidationError("Имя не может состоять только из цифр")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Данная почта уже занята')
