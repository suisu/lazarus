from flask import Blueprint

admin_page = Blueprint('admin_page', __name__,
    template_folder='templates',
    static_folder='static')

from app.modules.admin import users
from app.modules.admin import mail_server
from app.modules.admin import settings