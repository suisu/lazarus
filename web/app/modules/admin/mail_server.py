from flask import render_template, flash, abort, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField
from wtforms.validators import HostnameValidation, DataRequired, \
    Email, ValidationError, NumberRange
from flask_login import login_required, current_user
from app import db
from app.models import MailServer
from app.modules.admin import admin_page
from jinja2 import TemplateNotFound
from wtforms.widgets import PasswordInput
from werkzeug.datastructures import ImmutableMultiDict
from app.modules.security import encryption
from app.modules.email import SMTPEmail


class DomainChecker(object):
    
    def __init__(self, require_tld=True, allow_ip=False, message=None):
        self.require_tld = require_tld
        self.allow_ip = allow_ip
        if not message:
            message = "This is not a valid domain."
        self.message = message

    def __call__(self, form, field):
        domainvalidator = HostnameValidation()
        isDomain = domainvalidator(field.data)
        if not isDomain:
            raise ValidationError(self.message)

class MailServerForm(FlaskForm):
    smtp_server = StringField('smtp_server', 
        validators=[DataRequired(message='*Required'),
                    DomainChecker()],
        render_kw={"placeholder":"SMTP Server"})
    smtp_port = IntegerField('smtp_port',
        validators=[DataRequired(message='*Required'),
                    NumberRange(min=25, max=2525, message="Not in allowed range 25-2525")],
        render_kw={"placeholder":"SMTP Port"})
    sender = StringField('sender',
        validators=[DataRequired(message="*Required"),
                    Email()],
        render_kw={"placeholder":"Sender E-Mail"})
    password = StringField('password', widget=PasswordInput(hide_value=False))
    web_domain = StringField('web_domain',
        validators=[DataRequired(message="*Required")],
        render_kw={"placeholder":"Web Domain"})
    user_domain = StringField('user_domain',
        validators=[DataRequired(message="*Required")])
    submit = SubmitField('Submit')
    submit = SubmitField('Test')
        
@admin_page.route('smtp-server', methods=['GET','POST'])
@login_required
def mail_server():
    if not current_user.is_admin():
        abort(403)
    if request.method == 'GET':
        try:
            mailServer = MailServer.query.first()
            form = MailServerForm(obj=mailServer)
            if mailServer is None:
                flash("Please enter SMTP Settings", category='warning')
            else:
                privKey = encryption.get_priv_keys()
                pass_dec = mailServer.getPassword(privKey)
                form.password.process(ImmutableMultiDict(
                    [('password', pass_dec)]
                ))
            return render_template('admin/mail-server.html',
                                    form=form, title="Mail Server")
        except TemplateNotFound:
            abort(404)
    if request.method == 'POST':
        form = MailServerForm()
        if form.validate_on_submit():

            pubKey = encryption.get_pub_keys()
            

            pass_enc = MailServer.setPassword(form.password.data, pubKey)

            if request.form.get('Submit', None):
                mailServer = MailServer.query.first()
                if mailServer is None:
                    ms = MailServer(sender=form.sender.data,
                                            smtp_server=form.smtp_server.data,
                                            password_enc=pass_enc,
                                            smtp_port=form.smtp_port.data,
                                            user_domain=form.user_domain.data,
                                            web_domain=form.web_domain.data
                                            )
                    db.session.add(ms)
                else:
                    mailServer.smtp_server = form.smtp_server.data
                    mailServer.sender = form.sender.data
                    mailServer.password_enc = pass_enc
                    mailServer.smtp_port = form.smtp_port.data
                    mailServer.user_domain = form.user_domain.data
                    mailServer.web_domain = form.web_domain.data
                db.session.commit()

                flash('Your SMTP Server Configuration was successful', category="info")
            elif request.form.get('Test', None):
                testServer = MailServer(sender=form.sender.data,
                            smtp_server=form.smtp_server.data,
                            password_enc=pass_enc,
                            smtp_port=form.smtp_port.data,
                            user_domain=form.user_domain.data,
                            web_domain=form.web_domain.data
                            )
                testEmail = SMTPEmail(testServer)
                result = testEmail.send_test(receiver=current_user.username)

                if result:
                    flash('Your SMTP Server works perfectly, save your changes', category="success")
                else:
                    flash('Your SMTP Server settings failed.', category="error")
            else:
                abort(404)

        return render_template('admin/mail-server.html',
                        form=form, title="Mail Server")
