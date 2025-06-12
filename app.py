from flask import Flask, request, render_template, redirect, url_for, flash, session
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_default_secret")

# پوشه‌ی ذخیره‌ی سشن‌ها
SESSION_FOLDER = "sessions"
if not os.path.exists(SESSION_FOLDER):
    os.makedirs(SESSION_FOLDER)

def get_session_file(username):
    return os.path.join(SESSION_FOLDER, f"{username}_session.json")

def save_session(client, username):
    with open(get_session_file(username), "w") as f:
        f.write(json.dumps(client.dump_settings()))

def load_session(client, username):
    session_file = get_session_file(username)
    if os.path.exists(session_file):
        with open(session_file, "r") as f:
            settings = json.load(f)
        client.load_settings(settings)
        return True
    return False

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        session["username"] = username
        session["password"] = password

        cl = Client()
        session_loaded = load_session(cl, username)

        try:
            cl.login(username, password)
            save_session(cl, username)
            return redirect(url_for("home"))
        except TwoFactorRequired as e:
            # ذخیره مقادیر مورد نیاز برای ورود دو مرحله‌ای
            session["twofa_identifier"] = e.two_factor_identifier
            return redirect(url_for("twofa"))
        except Exception as e:
            flash(f"Login failed: {str(e)}")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/twofa", methods=["GET", "POST"])
def twofa():
    if request.method == "POST":
        code = request.form.get("code")
        username = session.get("username")
        password = session.get("password")
        identifier = session.get("twofa_identifier")

        cl = Client()
        try:
            cl.two_factor_login(
                username=username,
                password=password,
                verification_code=code,
                two_factor_identifier=identifier
            )
            save_session(cl, username)
            return redirect(url_for("home"))
        except Exception as e:
            flash(f"2FA Login failed: {str(e)}")
            return redirect(url_for("login"))

    return render_template("twofa.html")

@app.route("/home")
def home():
    return render_template("home.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
