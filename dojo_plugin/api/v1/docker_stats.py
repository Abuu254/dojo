from flask import Blueprint, jsonify
from CTFd.utils.decorators import admins_only
from .. import get_container_stats, get_dojo_stats  # Import functions

docker_stats_bp = Blueprint("docker_stats", __name__, url_prefix="/admin/docker")

@docker_stats_bp.route("/stats")
@admins_only 
def docker_stats():
    """Return real-time stats of all containers inside dojo."""
    stats = get_container_stats()
    return jsonify(stats)

@docker_stats_bp.route("/dojo_stats")
@admins_only
def dojo_stats():
    """Return dojo-specific stats."""
    dojo_id = request.args.get("dojo_id")
    if not dojo_id:
        return jsonify({"error": "Missing dojo_id"}), 400

    stats = get_dojo_stats(dojo_id)
    return jsonify(stats)
