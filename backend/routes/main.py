from flask import jsonify, request, send_from_directory, render_template
from flask import Blueprint

from backend import app, db


main_bp = Blueprint("main", __name__)


@main_bp.route('/')
def homepage():
    return app.send_static_file("homepage.html")

