from app import db
from flask import current_app as app
from .models import Github
from sqlalchemy.orm.exc import NoResultFound

@app.context_processor
def utility_processor():
    def last_updated():
        updated = ''
        try:
            last_updated = db.session.query(Github.time_created).order_by(Github.time_created.desc()).first()
            updated = last_updated[0].strftime("%d.%m.%Y %H:%M")
        except NoResultFound:
            updated = ''
        finally:
            return updated
    return dict(last_updated=last_updated)

