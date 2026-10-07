from flask import Blueprint, abort, request, session, redirect
from werkzeug.security import check_password_hash

from backend import app, db, ADMIN_HASH


main_bp = Blueprint("main", __name__)


@main_bp.route('/')
def homepage():
    return app.send_static_file("homepage.html")

@main_bp.route("/admin")
def admin_dashboard():
    if not session.get("is_admin", False):
        return redirect("/login")
    return "You are an admin!"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if not ADMIN_HASH:
        return "Server Error: Admin credentials are not configured in the system environment.", 500

    if request.method == 'POST':
        submitted_password = request.form.get('password')

        if check_password_hash(ADMIN_HASH, submitted_password):
            session['is_admin'] = True
            return redirect("/admin")

        return redirect('/login?error=1')

    return app.send_static_file('login.html')

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect('/')
