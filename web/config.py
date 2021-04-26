from os import path, pardir, urandom, environ
from yaml import safe_load, YAMLError
basedir = path.abspath(path.dirname(__file__))


class Settings():
    config = {}
 
    @classmethod
    def init(cls, *args, **kwargs):
        if not cls.config:
            configdir = path.abspath(path.join(basedir, pardir))
            with open(path.join(configdir, "config.yaml"), 'r') as stream:
                try:
                    cls.config = safe_load(stream)
                except YAMLError as exc:
                        raise exc
Settings.init()

class Config(object):
    SECRET_KEY = environ.get('SECRET_KEY') or urandom(42)
    CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI = Settings.config.get('db').get('database_uri')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_NAME='lazarus'
    SESSION_COOKIE_SECURE=True
    SESSION_TYPE = 'filesystem'
    TESTING = False

    #mail settings
    MAIL_SERVER = "smtp.googlemail.com"
    