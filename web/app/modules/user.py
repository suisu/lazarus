from io import BytesIO
from flask import Blueprint, render_template, session, url_for, redirect, flash, abort
from app import lm
from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, Email, ValidationError
from flask_login import current_user, login_user, logout_user
from app.modules.dashboard import dashboard_page
from app import db
from app.models import User, Role, MailServer, InitAdmin
import pyqrcode
from random import randint
from PIL import Image, ImageDraw, ImageFont
from itsdangerous import URLSafeTimedSerializer
from app.modules.email import SMTPEmail
import uuid

ts = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

user_page = Blueprint('user_page', __name__,
    template_folder='templates',
    static_folder='static')

@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class DomainEmailChecker(object):
    def __init__(self, domain=None, message=None):
        self.domain = domain
        if not message:
            message = f'E-mail cannot be registered for {self.domain} domain'
        self.message = message

    def __call__(self, form, field):
        if self.domain is None:
            return
        domain = field.data.split('@')[-1]
        if self.domain != domain:
            raise ValidationError(self.message)

class EmailForm(FlaskForm):
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
    submit = SubmitField('Reset')

class PasswordForm(FlaskForm):
    password = PasswordField(label="Password",
        validators=[DataRequired(message="*Required"),
                    Length(min=8, message='Password should be at least %(min)d characters long')],
        render_kw={"placeholder":"Password"})

class RegisterForm(FlaskForm):
    mailServer = MailServer.query.first()
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

    password = PasswordField(label='Password', 
        validators=[DataRequired(message='*Required'), 
                    Length(min=8, message='Password should be at least %(min)d characters long')],
        render_kw={"placeholder": "Password"})
    password_again = PasswordField(label='Password again', 
        validators=[DataRequired(message='*Required'), 
                    EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    mailServer = MailServer.query.first()
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
    password = PasswordField(label='Password', 
        validators=[DataRequired(message='*Required'), 
                    Length(min=8, message='Password should be at least %(min)d characters long')],
        render_kw={"placeholder": "Password"})
    token = StringField(label='Token', 
        validators=[DataRequired(), Length(min=6, message='Token should be at least %(min)d cahracters long')],
        render_kw={"placeholder": "Token"})
    submit = SubmitField('Login')

@lm.unauthorized_handler
def unauth_handler():
    return login()

@user_page.route('/register', methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_page.dashboard'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is not None:
            flash('Username already exists.')
            return redirect(url_for('user_page.register'))
        # add new user to the database
        user = User(username=form.username.data, password=form.password.data, role=Role.query.filter_by(name='NORMAL').one())
        db.session.add(user)
        db.session.commit()

        # redirect to the two-factor auth page, passing username in session
        session['username'] = user.username
        
        # if init_admin is present, dont't send email
        init_admin = InitAdmin.query.filter_by(email=user.username).one()
        if init_admin is not None:
            user.setAdminRole()
            db.session.commit()
            _uuid = uuid.uuid4().hex.upper()[0:13]
            return two_factor_setup(_uuid)

        try:
            email = SMTPEmail(MailServer.query.first())
            email.send_qr_code(user.username, qrcode())
        except Exception as error:
            print("Caught error", repr(error))
            abort(404)

        #return redirect(url_for('user_page.two_factor_setup'))
        flash('You have been successfully signed. Please, check your email.', category="info")
        return render_template('register.html', form=form)
    return render_template('register.html', form=form)

@user_page.route('/<_uuid>/twofactor')
def two_factor_setup(_uuid):
    if 'username' not in session:
        return redirect(url_for('index'))
    user = User.query.filter_by(username=session['username']).first()
    if user is None:
        return redirect(url_for('user_page.index'))
    # since this page contains the sensitive qrcode, make sure the browser 
    # will not cache it!!
    return render_template('two-factor-setup.html'), 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'}

@user_page.route('/qrcode_init')
def qrcode_init():
    if 'username' not in session:
        abort(404)
    user = User.query.filter_by(username=session['username']).first()
    if user is None:
        abort(404)

    # for added security, reove username from session!!
    del session['username']

    # render qrcode for FreeTOTP
    url = pyqrcode.create(user.get_totp_uri())
    
    stream = BytesIO()
    url.png(file=stream, scale=3.5, module_color=[0,0,0,128], background=[0xff,0xff,0xcc])
    #url.svg(stream, scale=2.5)
    return stream.getvalue(), 200, {
        'Content-Type': 'image/png',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

#@user_page.route('/qrcode')
def qrcode():
    if 'username' not in session:
        abort(404)
    user = User.query.filter_by(username=session['username']).first()
    if user is None:
        abort(404)

    # for added security, reove username from session!!
    del session['username']

    # render qrcode for FreeTOTP
    url = pyqrcode.create(user.get_totp_uri())
    
    stream = BytesIO()
    url.png(file=stream, scale=2.5, module_color=[0,0,0,128], background=[0xff,0xff,0xcc])
    return stream

@user_page.route('/')
@user_page.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_page.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.verify_password(form.password.data) or \
            not user.verify_totp(form.token.data):
            flash('Invalid username, password or token.', category='danger')
            return redirect(url_for('user_page.login'))

        # log user in
        login_user(user)
        flash('You are now logged in.', category="success")
        return redirect(url_for('dashboard_page.dashboard'))
    return render_template('login.html', form=form)

@user_page.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('user_page.login'))

def create_user_logo(first_letter):
    def bkg_color_randomizer(min,max):
        return (randint(min,max), randint(min,max), randint(min,max))
    res = bkg_color_randomizer(153,255)
    W,H = (100,100)
    user_img = Image.new('RGBA', (W,H), color=res)
    d = ImageDraw.Draw(user_img)
    fnt = ImageFont.truetype('web/app/static/fonts/aliendude.ttf', size=70)
    w,h = d.textsize(first_letter, font=fnt)
    d.text(((W-w)/2,(H-h)/2), first_letter, font=fnt, fill=(1,1,1), align='center')
    output = BytesIO()
    user_img.save(output, "PNG")
    return output

@user_page.route('/reset', methods=['GET','POST'])
def reset():
    form = EmailForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None:
            flash('Invalid username.', category='danger')
            return redirect(url_for('user_page.reset'))

        token = ts.dumps(user.username, salt='recover-key-lazarus')
        recover_url = url_for('user_page.reset_with_token', token=token, _external=True)
        
        try:
            email = SMTPEmail(MailServer.query.first())
            email.reset_password(user.username, recover_url)
        except Exception:
            abort(404)
        
        
        flash('Check your email please', category='info')
        return redirect(url_for('user_page.login'))

    return render_template('reset.html', form=form)

@user_page.route('/reset/<token>', methods=['GET','POST'])
def reset_with_token(token):
    try:
        email = ts.loads(token, salt="recover-key-lazarus", max_age=86400)
    except:
        abort(404)

    form = PasswordForm()
    if form.validate():
        user = User.query.filter_by(username=email).first_or_404()
        user.password = form.password.data
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('user_page.login'))
    return render_template('reset-with-token.html', email=email, form=form, token=token)