import requests
import re
import yalies
from urllib.parse import urlencode
from flask import Blueprint, redirect, request, session, url_for, flash
from CTFd.models import Users, db, Admins
from CTFd.utils.security.auth import login_user, logout_user
from CTFd.utils.logging import log
from ...config import CAS_SERVER, SERVICE_URL,YALIES_API_TOKEN,CAS_ADMIN_NETIDS

cas_auth_bp = Blueprint("cas_auth", __name__, url_prefix="/cas")

@cas_auth_bp.route("/login")
def cas_login():
    """Redirect user to CAS for authentication."""
    session["next"] = request.args.get("next")
    service_url = url_for("cas_auth.cas_callback", _external=True)
    login_url = f"{CAS_SERVER}/login?{urlencode({'service': service_url})}"
    return redirect(login_url)

@cas_auth_bp.route("/callback")
def cas_callback():
    """CAS Callback after authentication."""
    ticket = request.args.get("ticket")

    if not ticket:
        flash("CAS authentication failed: No ticket provided.", "error")
        return redirect(url_for("auth.login"))

    validate_url = (
        f"{CAS_SERVER}/serviceValidate?"
        + urlencode({
            "service": url_for("cas_auth.cas_callback", _external=True),
            "ticket": ticket,
        })
    )
    response = requests.get(validate_url)

    match = re.search(r"<cas:user>(.*?)</cas:user>", response.text)
    if not match:
        flash("CAS authentication failed: No valid user found.", "error")
        return redirect(url_for("auth.login"))

    username = match.group(1).strip()

    # Create or fetch the CTFd user record
    user = Users.query.filter_by(name=username).first()
    if not user:
        user = Users(name=username, verified=True)
        db.session.add(user)
        db.session.commit()

    # If this NetID is in your admin list, promote them
    if username in CAS_ADMIN_NETIDS:
        user.type = "admin"
        # hide them from rankings
        user.hidden = True
        if not Admins.query.filter_by(name=username).first():
            db.session.add(Admins(
                name=username,
                email=user.email or "",
                type="admin",
                hidden=True,
            ))
        db.session.commit()

    login_user(user)
    log("logins", "[{date}] {ip} - {name} logged in via CAS", name=user.name)

    next_url = session.pop("next", None) or request.args.get("next") or url_for("pwncollege_dojo.listing")
    return redirect(next_url)

@cas_auth_bp.route("/logout")
def cas_logout():
    """Logout user from both CTFd and CAS, then redirect"""
    logout_user()
    cas_logout_url = f"{CAS_SERVER}/logout?service={url_for('static_html_override', route='index', _external=True)}"
    return redirect(cas_logout_url)

def get_user(netid):
    """Getting user information from yalies.io"""
    headers = {
        "Authorization": f"Bearer {YALIES_API_TOKEN}",
    }
    body = {
        "filters": {
            "netid": netid
        }
    }

    response = requests.post("https://api.yalies.io/v2/people", headers=headers, json=body)

    if response.status_code != 200:
        raise Exception(f"Yalies API request failed: {response.text}")

    data = response.json()
    if not data:
        raise Exception(f"No user found with netid: {netid}")

    return data[0]