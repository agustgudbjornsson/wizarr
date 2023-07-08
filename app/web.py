import logging
import os
import os.path
import threading

from flask import (make_response, redirect, render_template, request,
                   send_from_directory)

from app import Settings, app, get_locale
from app.helpers import is_invite_valid
from app.plex import plex_handle_oauth_token


@app.route('/')
def redirect_to_invite():
    # if not Settings.get_or_none("server_verified"):
    #     return redirect('/settings')
    return redirect('/admin')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/j/<code>", methods=["GET"])
def plex(code):
    valid, message = is_invite_valid(code)

    if not valid:
        return render_template('invalid-invite.html', error=message)
    if Settings.get(key="server_type").value == "jellyfin":
        return render_template("welcome-jellyfin.html", code=code)
    return render_template('user-plex-login.html', code=code)


@app.route("/join", methods=["POST"])
def connect():
    code = request.form.get('code')
    token = request.form.get("token")

    valid, message = is_invite_valid(code)

    if not valid:
        return render_template("user-plex-login.html", name=Settings.get(Settings.key == "server_name").value, code=code, code_error=message)

    if Settings.get(key="server_type").value == "plex":
        threading.Thread(target=plex_handle_oauth_token, args=(token, code)).start()
        return redirect(os.getenv("APP_URL") + "/setup")

    elif Settings.get(key="server_type").value == "jellyfin":
        return render_template("signup-jellyfin.html", code=code)


@app.route('/setup', methods=["GET"])
def setup():
    resp = make_response(render_template(
        "wizard.html", server_type=Settings.get(Settings.key == "server_type").value, server_url=Settings.get(Settings.key == "server_url").value))
    resp.set_cookie('current', "0")

    return resp


@app.route('/setup/open-plex', methods=["GET"])
def open_plex():
    return redirect('https://app.plex.tv/desktop/#!/')


@app.route('/setup/action=<action>', methods=["POST"])
def wizard(action):
    # Get video language and URL based on language
    video_lang = get_locale()
    videos = {
        "en": {
            "web_video": "https://www.youtube.com/embed/yO_oPny-Y_I",
            "app_video": "https://www.youtube.com/embed/e7Gy4FHDy5k"
        },
        "fr": {
            "web_video": "https://www.youtube.com/embed/f1ce3_OY5OE",
            "app_video": "https://www.youtube.com/embed/u8ejqsGfntw"
        }
    }

    if video_lang not in videos:
        video_lang = "en"

    # Get current step from cookies
    current = int(request.cookies.get('current'))

    # Get settings from database
    settings = {}
    for setting in Settings.select():
        settings[setting.key] = setting.value

    server_type = settings.get("server_type", "")

    # Build list of steps
    steps = [f"wizard/{server_type}/download.html",]

    if settings.get("request_url"):
        steps.append("wizard/requests.html")

    if settings.get("discord_id"):
        if settings.get("discord_widget") == "on":
            steps.append("wizard/discord-widget.html")
        else:
            steps.append("wizard/discord.html")

    if settings.get("custom_html"):
        steps.append("wizard/custom.html")

    steps.append(f"wizard/{server_type}/tips.html")

    # Render template for next or previous step
    if action == "next":
        next_step = current + 1
        max_step = len(steps) - 1
        resp = make_response(render_template(
            steps[next_step], videos=videos,
            video_lang=video_lang,
            discord_id=settings.get("discord_id"),
            request_url=settings.get("request_url"),
            custom_html=settings.get("custom_html"),
            server_url=settings.get("server_url"),
            next=True))
        resp.headers['current'] = str(next_step)
        resp.headers['max'] = "1" if next_step == max_step else "0"
        resp.set_cookie('current', str(next_step))
        return resp

    elif action == "prev":
        prev_step = current - 1
        resp = make_response(render_template(
            steps[prev_step], videos=videos,
            video_lang=video_lang,
            discord_id=settings.get("discord_id"),
            request_url=settings.get("request_url"),
            custom_html=settings.get("custom_html"),
            server_url=settings.get("server_url"),
            prev=True))
        resp.headers['current'] = str(prev_step)
        resp.headers['max'] = "0"
        resp.set_cookie('current', str(prev_step))
        return resp


def error_handler(code):
    @app.errorhandler(code)
    def handler(exception):
        logging.error(exception)
        return render_template(f'error/{code}.html'), code

error_handler(500)
error_handler(404)
error_handler(401)


@app.context_processor
def inject_user():
    name = ""
    try:
        name = Settings.get(Settings.key == "server_name").value
    except:
        name = "Wizarr"
        print("Could not find name :( ")
    return dict(server_name=name)
