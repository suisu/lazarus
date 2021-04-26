import os
from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import base64
import onetimepass
import rsa
import binascii

class Organization(db.Model):
    __tablename__ = "organization"
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column("name", db.String(60))
    url = db.Column("url", db.String)
    repositories = db.relationship('Repository', backref='organization',
                                lazy='dynamic')
    __table_args__ = (
        db.UniqueConstraint("name"),
    )

    def __init__(self, **kwargs):
        super(Organization, self).__init__(**kwargs)

    def __repr__(self):
        return f"<Organization(name={self.name}, url={self.url})>"


class Repository(db.Model):
    __tablename__ = "repository"
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column("name", db.String(60))
    url = db.Column("url", db.String)
    private = db.Column("private", db.Boolean, unique=False, default=True)
    description = db.Column("description", db.String)
    last_updated = db.Column("last_updated", db.DateTime(timezone=True), nullable=True)

    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    __table_args__ = (
        db.UniqueConstraint("name", "organization_id"),
    )
    branches = db.relationship("Branch", backref='repository', lazy='dynamic')
    languages = db.relationship("Language", backref='repository', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Repository, self).__init__(**kwargs)

    def __repr__(self):
        return f"<Repository(name={self.name}, url={self.url}, \
            private={self.private}, description={self.description}, \
            last_updated={self.last_updated})>"

class Branch(db.Model):
    __tablename__ = "branch"
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column("name", db.String)
    default_branch = db.Column("default_branch", db.Boolean, unique=False, default=False)
    repository_id = db.Column(db.Integer, db.ForeignKey('repository.id'))

    __table_args__ = (
        db.UniqueConstraint("name", "repository_id"),
    )

    vulns = db.relationship("Vuln", backref="branch", lazy='dynamic')
    scans = db.relationship("Scan", backref="branch", lazy='dynamic')

    def __init__(self, **kwargs):
        super(Branch, self).__init__(**kwargs)

    def __repr__(self):
        return f"<Branch(name={self.name}, default_branch={self.default_branch})>"

class Language(db.Model):
    __tablename__ = "language"
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column("name", db.String(50))
    lines = db.Column("lines", db.BigInteger)
    repository_id = db.Column(db.Integer, db.ForeignKey('repository.id'))
    __table_args__ = (
        db.UniqueConstraint("name", "repository_id"),
    )

    def __init__(self, **kwargs):
        super(Language, self).__init__(**kwargs)

    def __repr__(self):
        return f"<Language(name={self.name}, lines={self.lines})>"

class Github(db.Model):
    __tablename__ = "github"
    id = db.Column(db.Integer, primary_key=True)
    time_created = db.Column("time_created", db.DateTime(timezone=True), default=datetime.now())

    def __init__(self, **kwargs):
        super(Github, self).__init__(**kwargs)

    def __repr__(self):
        return f"<Github(time_created={self.time_created})>"

class Vuln(db.Model):
    __tablename__ = "vuln"
    id = db.Column("id", db.Integer, primary_key=True)
    reason = db.Column("reason", db.String)
    stringsfound = db.Column("stringsfound", db.ARRAY(db.String),  default= dict)
    commithash = db.Column("commithash", db.String, nullable=False)
    commit = db.Column("commit", db.String, nullable=True)
    printdiff = db.Column("printdiff", db.String, nullable=True)
    date = db.Column("date", db.DateTime)
    path = db.Column("path", db.String)
    false_positive = db.Column("false_positive", db.Boolean, unique=False, default=False)

    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'))
    scan_id = db.Column(db.Integer, db.ForeignKey('scan.id'))

    def __init__(self, **kwargs):
        super(Vuln, self).__init__(**kwargs)

    def __repr__(self):
        return f"<Vuln(reason={self.reason}, stringsfound={self.stringsFound}, commithash={self.commitHash}, commit={self.commit}, \
           printdiff={self.printDiff}, date={self.date}, path={self.path}, false_positive={self.false_positive}>"

class Scan(db.Model):
    __tablename__ = "scan"
    id = db.Column("id", db.Integer, primary_key=True)
    count = db.Column("count", db.Integer, nullable=False)
    time_created = db.Column("time_created", db.DateTime(timezone=True), default=datetime.now())

    branch_id = db.Column(db.Integer, db.ForeignKey("branch.id"))
    vulns = db.relationship("Vuln", backref="scan", lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint("branch_id"),
    )

    def __init__(self, **kwargs):
        super(Scan, self).__init__(**kwargs)

    def __repr__(self):
        return f"<Scan(count={self.count}, time_created={self.time_created})>"

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column("id", db.Integer, primary_key=True)
    username = db.Column(db.String(120), index=True)
    password_hash = db.Column(db.String(128))
    otp_secret = db.Column(db.String(16))
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"))
    role = db.relationship("Role", back_populates="users")

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.otp_secret is None:
            # generate random secret
            self.otp_secret = base64.b32encode(os.urandom(10)).decode('utf-8')

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_totp_uri(self):
        return 'otpauth://totp/Lazarus:{0}?secret={1}&issuer=LazarusScanner' \
            .format(self.username, self.otp_secret)

    def verify_totp(self, token):
        return onetimepass.valid_totp(token, self.otp_secret)

    def is_admin(self):
        return self.role.name == 'ADMIN'

    def is_operator(self):
        return self.role.name == 'OPERATOR'

    def is_normal(self):
        return self.role.name == 'NORMAL'

    def setAdminRole(self):
        self.role = Role.query.filter_by(name='ADMIN').one_or_none()
    

class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    users = db.relationship("User", back_populates="role")

    __table_args__ = (
        db.UniqueConstraint("name"),
    )

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return self.name

class MailServer(db.Model):
    __tablename__ = 'mailserver'
    id = db.Column("id", db.Integer, primary_key=True)
    sender = db.Column("sender", db.String(120), index=True)
    password_enc = db.Column(db.String(512))
    smtp_server = db.Column(db.String(120))
    smtp_port = db.Column(db.Integer)
    user_domain = db.Column(db.String(12))
    web_domain = db.Column(db.String(120))

    __table_args__ = (
        db.UniqueConstraint("user_domain"),
        db.UniqueConstraint("web_domain")
    )

    def getPassword(self, privateKey):
        bpassword_enc = binascii.unhexlify(self.password_enc)
        return rsa.decrypt(bpassword_enc, privateKey).decode()        

    @staticmethod
    def setPassword(password, publicKey):
        password_enc = rsa.encrypt(password.encode(), publicKey)
        bpassword_enc = binascii.hexlify(password_enc)
        password_enc = bpassword_enc.decode()
        return password_enc

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_enc = password


class InitAdmin(db.Model):
    __tablename__ = 'initadmin'
    id = db.Column("id", db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True)

class ScannerSettings(db.Model):
    __tablename__ = 'scannersettings'
    id = db.Column("id", db.Integer, primary_key=True)
    github_api_url = db.Column("github_api_url", db.String(120), index=True)
    github_last_updated_days = db.Column("github_last_updated_days", db.Integer)
    token = db.Column("github_token", db.String(512)) #unencrypted up to 255
    scan_github_domain = db.Column("scan_github_domain", db.String(120))
    scan_newer_days = db.Column("scan_newer_days", db.Integer)
    scan_max_depth = db.Column("scan_max_depth", db.Integer)
    scan_entropy = db.Column("scan_entropy",db.Boolean, default=True)
    scan_threads = db.Column("scan_threads", db.Integer)

    def getToken(self, privateKey):
        bpassword_enc = binascii.unhexlify(self.token)
        return rsa.decrypt(bpassword_enc, privateKey).decode()        

    @staticmethod
    def setToken(token, publicKey):
        password_enc = rsa.encrypt(token.encode(), publicKey)
        bpassword_enc = binascii.hexlify(password_enc)
        password_enc = bpassword_enc.decode()
        return password_enc

    @property
    def github_token(self):
        raise AttributeError('Token is not a readable attribute')

    @github_token.setter
    def github_token(self, token):
        self.token = token

    