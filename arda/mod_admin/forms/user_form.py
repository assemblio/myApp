from flask_wtf import Form
from wtforms import RadioField, TextField, PasswordField


class UserForm(Form):

    first_name = TextField("First Name")
    last_name = TextField("Last Name")
    email = TextField("E-mail")
    password = PasswordField("Password")
    roles = RadioField(
        "User Type",
        choices=[
            ('Regular', 'Regular'),
            ('Admin', 'Admin')
        ],
        default='Regular'
    )
