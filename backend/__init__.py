from os import getenv
from datetime import timedelta

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, static_folder="../frontend", static_url_path="")

app.config["SQLALCHEMY_DATABASE_URI"] = getenv("DB_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

from backend import dev
from backend.routes.main import main_bp

app.register_blueprint(main_bp)
