from flask import Flask
from flask_admin import Admin
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_migrate import Migrate
from flask_security import SQLAlchemyUserDatastore, Security
from flask_sqlalchemy import SQLAlchemy


app = None
attach_path = None
ncbi_api_key = None
bootstrap = None

db = SQLAlchemy()
migrate = Migrate()
admin_obj = Admin(template_mode='bootstrap3')
mail = Mail()
security = Security()


def create_app():
    global app, db, bootstrap, admin_obj, mail, security
    app = Flask(__name__)
    app.config.from_pyfile('config.cfg')
    app.config.from_pyfile('secret.cfg')
    ncbi_api_key = app.config['NCBI_API_KEY']

    db.init_app(app)
    migrate.init_app(app, db)
    bootstrap = Bootstrap(app)
    admin_obj.init_app(app)
    mail.init_app(app)
