from flask import Flask, render_template, abort
from flask_session import Session
from config import Config
from flask_sqlalchemy import SQLAlchemy

from flask_socketio import SocketIO
from flask_login import LoginManager

socketio = SocketIO()
db = SQLAlchemy()
lm = LoginManager()

def create_app():
    """Construct the core application."""
    app = Flask(__name__, 
                    static_url_path='', 
                    static_folder='./static',
                    template_folder='./templates')
    app.config.from_object(Config)

    db.init_app(app)

    lm.init_app(app)
    Session(app)
    socketio.init_app(app, manage_session=False)

    from flask_wtf import CSRFProtect
    csrf = CSRFProtect()
    csrf.init_app(app)

    with app.app_context():
        from app import routes  # Import routes

        # Register Blueprints
        from app.modules import vulnerabilities
        app.register_blueprint(vulnerabilities.vulnerabilities_page)
        
        from app.modules import details
        app.register_blueprint(details.details_page)

        from app.modules import repository
        app.register_blueprint(repository.repository_page)

        from app.modules import scanner
        app.register_blueprint(scanner.scanner_page)

        from app.modules import dashboard
        app.register_blueprint(dashboard.dashboard_page)

        from app.modules import user
        app.register_blueprint(user.user_page)

         

        db.create_all()  # Create database tables for our data models

        from sqlalchemy.sql import text
        with open('web/scripts/roles.sql') as f:
            db.session.execute(text(f.read()))
            db.session.commit()
        with open('web/scripts/init_admin.sql') as f:
            db.session.execute(text(f.read()))
            db.session.commit()

        from app.modules.admin import admin_page
        app.register_blueprint(admin_page, url_prefix='/admin')


        @app.errorhandler(403)
        def errorhandler(error):
            return render_template('errors/403.html', title='Forbidden'), 403

        @app.errorhandler(404)
        def page_not_found(error):
            return render_template('errors/404.html', title="Page not found"), 404

        @app.errorhandler(500)
        def internal_server_error(error):
            return render_template('errors/500.html', title='Server Error'), 500
            
        @app.route('/500')
        def error():
            abort(500)

        return app

