from flask import Flask, request, render_template, redirect, url_for, flash, session
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired
import os
import json
import random
import time

app = Flask(__name__)
app.secret_key = "YOUR_SECRET_KEY"  # حتما عوضش کن

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

        # تلاش بارگذاری سشن
        session_loaded = load_session(cl, username)
        try:
            if session_loaded:
                cl.login(username, password)
            else:
                cl.login(username, password)
        except TwoFactorRequired:
            # ذخیره کلاینت و اطلاعات در session برای 2FA
            session["client_settings"] = cl.dump_settings()
            flash("کد ۲FA لازم است، لطفا وارد کنید.", "error")
            return redirect(url_for("twofa"))
        except Exception as e:
            flash(f"خطا در لاگین: {e}", "error")
            return redirect(url_for("login"))

        save_session(cl, username)
        flash(f"✅ ورود موفق! خوش آمدید {username}", "success")
        return redirect(url_for("home"))

    return render_template("login.html")

@app.route("/twofa", methods=["GET", "POST"])
def twofa():
    if request.method == "POST":
        code = request.form.get("code").strip()
        username = session.get("username")
        password = session.get("password")

        if not username or not password:
            flash("اطلاعات لاگین یافت نشد. لطفا دوباره تلاش کنید.", "error")
            return redirect(url_for("login"))

        cl = Client()
        # بارگذاری تنظیمات کلاینت که در زمان 2FA ذخیره شده بود
        settings = session.get("client_settings")
        if settings:
            cl.load_settings(settings)
        else:
            flash("تنظیمات کلاینت موجود نیست.", "error")
            return redirect(url_for("login"))

        try:
            cl.login(username, password, verification_code=code)
        except Exception as e:
            flash(f"کد ۲FA اشتباه یا خطا: {e}", "error")
            return redirect(url_for("twofa"))

        save_session(cl, username)
        flash("✅ ۲FA تایید شد و ورود موفق!", "success")
        return redirect(url_for("home"))

    return render_template("twofa.html")

@app.route("/home", methods=["GET"])
def home():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))
    return render_template("home.html", username=username)

@app.route("/do_actions", methods=["POST"])
def do_actions():
    username = session.get("username")
    password = session.get("password")
    if not username or not password:
        flash("ابتدا وارد شوید.", "error")
        return redirect(url_for("login"))

    target_username = request.form.get("target_username").strip()
    amount = int(request.form.get("amount"))

    cl = Client()
    # بارگذاری سشن
    session_loaded = load_session(cl, username)
    try:
        if session_loaded:
            cl.login(username, password)
        else:
            cl.login(username, password)
    except Exception as e:
        flash(f"خطا در لاگین: {e}", "error")
        return redirect(url_for("login"))

    try:
        user_id = cl.user_id_from_username(target_username)
        posts = cl.user_medias(user_id, amount)
    except Exception as e:
        flash(f"خطا در دریافت پست‌ها از {target_username}: {e}", "error")
        return redirect(url_for("home"))

    for idx, post in enumerate(posts):
        action = random.choice(["like", "comment", "both"])

        if action in ["like", "both"]:
            try:
                cl.media_like(post.id)
            except Exception as e:
                flash(f"خطا در لایک پست {idx+1}: {e}", "error")

        if action in ["comment", "both"]:
            comment = random.choice([
                "Nice shot! 🔥",
                "Great post! 💯",
                "Awesome picture 🙌",
                "Loved this! 🌿",
                "Wow! 📸"
            ])
            try:
                cl.media_comment(post.id, comment)
            except Exception as e:
                flash(f"خطا در کامنت پست {idx+1}: {e}", "error")

    save_session(cl, username)
    flash("🎉 عملیات با موفقیت انجام شد.", "success")
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
