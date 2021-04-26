from flask import render_template, session, \
    url_for, redirect, flash, abort, flash, request
from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, BooleanField
from wtforms.validators import HostnameValidation, DataRequired, \
    Length, EqualTo, Email, ValidationError, NumberRange, URL, Optional
from flask_login import login_required, current_user, login_user, logout_user
from app import db
from app.models import User, Role, ScannerSettings
from config import Settings
from flask_expects_json import expects_json
from app.modules.admin import admin_page
from jinja2 import TemplateNotFound
from os import path
from wtforms.widgets import PasswordInput
from werkzeug.datastructures import ImmutableMultiDict
import rsa
from app.modules.security import encryption
from app.modules.admin.mail_server import DomainChecker


class SettingsForm(FlaskForm):
    github_api_url = StringField('github_api_url', 
        validators=[DataRequired(message='*Required'),
                    URL()],
        render_kw={"placeholder":"Github API URL"})
    github_token = StringField('github_token', 
        validators=[DataRequired(message='*Required')],
        widget=PasswordInput(hide_value=False))
    github_last_updated_days = IntegerField('github_last_updated_days',
        validators=[DataRequired(message='*Required'),
                    NumberRange(min=0, max=365, message="Not in allowed range 0-365")],
        default=30)
    scan_github_domain = StringField('sender',
        validators=[DataRequired(message="*Required"),
                    DomainChecker()],
        render_kw={"placeholder":"Github Domain"})
    scan_newer_days = IntegerField('scan_newer_days',
        validators=[DataRequired(message='*Required'),
                    NumberRange(min=0, max=365, message="Not in allowed range 0-365")],
        default=30)
    scan_max_depth = IntegerField('scan_max_depth',
        validators=[DataRequired(message='*Required'),
                    NumberRange(min=0, max=1000000, message="Not in allowed range 0-1,000,000")],
        default=1000000,
        render_kw={"placeholder":1000000})
    scan_entropy = BooleanField('scan_entropy', default=True)
    scan_threads = IntegerField('scan_threads',
        validators=[DataRequired(message='*Required'),
                    NumberRange(min=1, max=5, message="Not in allowed range 1-5")],
        default=5)
    
    submit = SubmitField('Submit')
        
@admin_page.route('settings', methods=['GET','POST'])
@login_required
def settings():
    if not current_user.is_admin():
        abort(403)
    if request.method == 'GET':
        try:
            scannerSettings = ScannerSettings.query.first()
            form = SettingsForm(obj=scannerSettings)
            if scannerSettings is None:
                flash("Please fill basic Settings for scanner", category='warning')
            else:
                privKey = encryption.get_priv_keys()
                token_dec = scannerSettings.getToken(privKey)
                form.github_token.process(ImmutableMultiDict(
                    [('github_token', token_dec)]
                ))
            return render_template('admin/settings.html',
                                    form=form, title="Scanning Settings")
        except TemplateNotFound:
            abort(404)
    if request.method == 'POST':
        form = SettingsForm()
        if form.validate_on_submit():

            pubKey = encryption.get_pub_keys()
            

            token_enc = ScannerSettings.setToken(form.github_token.data, pubKey)
            print("encrypted: ", token_enc)

            scannerSettings = ScannerSettings.query.first()
            if scannerSettings is None:
                ss = ScannerSettings(github_api_url=form.github_api_url.data,
                                        github_last_updated_days=form.github_last_updated_days.data,
                                        token=token_enc,
                                        scan_github_domain=form.scan_github_domain.data,
                                        scan_newer_days=form.scan_newer_days.data,
                                        scan_max_depth=form.scan_max_depth.data,
                                        scan_entropy=form.scan_entropy.data,
                                        scan_threads=form.scan_threads.data
                                        )
            
                db.session.add(ss)
            else:
                scannerSettings.github_api_url = form.github_api_url.data
                scannerSettings.github_last_updated_days = form.github_last_updated_days.data
                scannerSettings.token = token_enc
                scannerSettings.scan_github_domain = form.scan_github_domain.data
                scannerSettings.scan_newer_days = form.scan_newer_days.data
                scannerSettings.scan_max_depth = form.scan_max_depth.data
                scannerSettings.scan_entropy = form.scan_entropy.data
                scannerSettings.scan_threads = form.scan_threads.data
            db.session.commit()
            

            flash('Your Scanning Configuration was successful set', category="info")

        return render_template('admin/settings.html',
                        form=form, title="Scanning Settings")
