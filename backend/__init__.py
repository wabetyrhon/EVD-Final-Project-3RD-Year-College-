from os import getenv
from datetime import timedelta

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__, static_folder="../frontend", static_url_path="")

app.config["SECRET_KEY"] = getenv("SECRET_KEY")
app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax'
        )

app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DB_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {
            'ssl': {}
            }
        }

db = SQLAlchemy(app)
ADMIN_HASH = getenv("ADMIN_HASH")

from backend import dev
from backend.routes.main import main_bp

app.register_blueprint(main_bp)
