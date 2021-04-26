from flask import render_template, \
    url_for, redirect, abort, flash
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Email, ValidationError
from flask_login import login_required, current_user
from app import db
from app.models import User, Role, MailServer
from app.modules.user import DomainEmailChecker
from app.modules.admin import admin_page

roles = db.session.query(Role.name).all()
roles = set(map(lambda x: x[0], roles))

class RoleChecker(object):
    def __init__(self, roles, message=None):
        self.roles = roles
        if not message:
            message = "This role doesn't exist."
        self.message = message

    def __call__(self, form, field):
        role = field.data
        if role not in self.roles:
            raise ValidationError(self.message)

class UserForm(FlaskForm):
    mailServer = MailServer.query.one_or_none()
    if mailServer is None:
        username = StringField(label='E-mail', 
            validators=[DataRequired(message='*Required'),
                        Email(),
                        Length(max=120)], 
            render_kw={"placeholder": "E-mail"})
    else:
        username = StringField(label='E-mail', 
            validators=[DataRequired(message='*Required'),
                        Email(),
                        Length(max=120),
                        DomainEmailChecker(domain=mailServer.user_domain)], 
            render_kw={"placeholder": "E-mail"})

    role = StringField(label='Role',
        validators=[DataRequired(message="*Required"),
                    RoleChecker(roles=roles)],
        render_kw={"placeholder": "Role"})

    submit = SubmitField('Submit')

@admin_page.route('users', methods=['GET','POST'])
@login_required
def list_users():
    if not current_user.is_admin():
        abort(403)

    users = User.query.all()
    return render_template('admin/users/users.html',
                            users=users, title="Users")

@admin_page.route('/users/add', methods=['GET','POST'])
@login_required
def add_user():
    if not current_user.is_admin():
        abort(403)
    
    add_user = True
    form = UserForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is not None:
            flash('Username already exists.', category='danger')
            return redirect(url_for('admin_page.list_users'))
        try:
            user = User(username=form.username.data, password='1234567890#', role=Role.query.filter_by(name=form.role.data).one())
            db.session.add(user)
            db.session.commit()
        except:
            flash('Error occurred.', category='danger')
        return redirect(url_for('admin_page.list_users'))

    return render_template('admin/users/user.html',
            add_user=add_user, 
            form=form, 
            title="Add user", 
            submit_title='Add',
            roles=roles)

@admin_page.route('/users/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_user(id):
    if not current_user.is_admin():
        abort(403)

    add_user = False
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        role = Role.query.filter_by(name=form.role.data).first()
        user.role = role
        db.session.commit()
        flash('You have successfully edited the user.')

        return redirect(url_for('admin_page.list_users'))

    form.username.data = user.username
    form.role.data = user.role
    return render_template('admin/users/user.html',
            userid=id,
            add_user=add_user, 
            form=form, 
            title="Edit user", 
            submit_title='Add',
            roles=roles)

@admin_page.route('/users/delete/<int:id>', methods=['GET','POST'])
@login_required
def delete_user(id):
    if not current_user.is_admin():
        abort(403)

    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash(f"You have successfully deleted the user {user.username}.", category="success")

    return redirect(url_for('admin_page.list_users'))

    return render_template(title="Delete Department")
