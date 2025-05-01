import requests
from flask import Blueprint, render_template, url_for, redirect, request, current_app, session,jsonify
from CTFd.utils.decorators import admins_only
from CTFd.models import Users
from CTFd.plugins import bypass_csrf_protection
from ..utils import  container_password, get_all_containers, get_current_container
from ..utils.stats import get_container_stats, get_full_container_stats
from ..utils.workspace import exec_run, start_on_demand_service, reset_home
from ..api.v1.docker import remove_container

admin_docker_bp = Blueprint("admin_docker", __name__, url_prefix="/admin")

@admin_docker_bp.route("/desktops")
@admins_only
def view_admin_desktops():
    return render_template("admin_desktops.html")

@admin_docker_bp.route("/workspace/<int:user_id>/<service>")
@admins_only
def view_user_workspace(user_id, service):
    if service not in {"desktop", "code"}:
        abort(400, description="Invalid service")

    user = Users.query.get_or_404(user_id)
    container = get_current_container(user)
    if not container:
        abort(404)

    return render_template("workspace.html", iframe_name="workspace", service=service, user_id=user_id, active=True)

@admin_docker_bp.route("/stop/<int:user_id>", methods=["POST"])
@bypass_csrf_protection
@admins_only
def stop_user_container(user_id):
    user = Users.query.get_or_404(user_id)
    try:
        remove_container(user)
    except Exception as e:
        current_app.logger.exception(f"Failed to stop container for user {user_id}: {e}")
        abort(500, description="Could not stop the container")

    return redirect(url_for("admin_docker.view_admin_desktops"))

@admin_docker_bp.route("/desktops.json")
@admins_only
def view_admin_desktops_json():
    full_stats = get_full_container_stats()
    user_ids = {
        int(s["labels"].get("dojo.user_id", -1))
        for s in full_stats
        if "labels" in s and "dojo.user_id" in s["labels"]
    }
    user_map = {
        u.id: u.name for u in Users.query.filter(Users.id.in_(user_ids)).all()
    }

    containers = []
    for stat in full_stats:
        labels = stat.get("labels", {})
        uid = int(labels.get("dojo.user_id", -1))
        if uid == -1:
            continue
        containers.append({
            "user_id":      uid,
            "user_name":    user_map.get(uid, "Unknown"),
            "challenge":    labels.get("dojo.challenge_id", "Unknown"),
            "mem_usage":    stat.get("mem_usage", 0),
            "mem_limit":    stat.get("mem_limit", 0),
            "mem_percent":  stat.get("mem_percent", 0),
        })
    return jsonify(containers)