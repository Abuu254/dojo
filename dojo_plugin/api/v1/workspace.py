import hmac
from flask_restx import Namespace, Resource
from flask import request, render_template, url_for, abort
from CTFd.utils.user import get_current_user, is_admin
from CTFd.models import Users
from CTFd.utils.decorators import authed_only
from ...utils import get_current_container, container_password
from ...utils.workspace import exec_run, start_on_demand_service, reset_home

workspace_namespace = Namespace(
    "workspace", description="Endpoint to manage workspace iframe urls"
)

@workspace_namespace.route("")
class view_desktop(Resource):
    @authed_only
    def get(self):
        user_id  = request.args.get("user")
        password = request.args.get("password")
        service  = request.args.get("service")

        if not service:
            return {"active": False}

        # Admins bypass all password checks
        admin_user = is_admin()

        # Non-admins must supply a password when viewing another user
        if user_id and not password and not admin_user:
            abort(401)

        user = get_current_user() if not user_id else Users.query.filter_by(id=int(user_id)).first_or_404()
        container = get_current_container(user)
        if not container:
            return {"active": False}

        # DESKTOP SERVICE
        if service == "desktop":
            interact_pw = container_password(container, "desktop", "interact")[:8]
            view_pw     = container_password(container, "desktop", "view")[:8]

            if admin_user:
                # full access, no view-only
                password  = interact_pw
                view_only = False
            else:
                if user_id and password:
                    if not (
                        hmac.compare_digest(password, interact_pw) or
                        hmac.compare_digest(password, view_pw)
                    ):
                        abort(403)
                    password = password[:8]
                else:
                    password = interact_pw
                view_only = not hmac.compare_digest(password, interact_pw)

            service_param = "~".join(("desktop", str(user.id), container_password(container, "desktop")))
            vnc_params = {
                "autoconnect":    1,
                "reconnect":      1,
                "reconnect_delay":200,
                "resize":         "remote",
                "path":           url_for("pwncollege_workspace.forward_workspace", service=service_param, service_path="websockify"),
                "view_only":      int(view_only),
                "password":       password,
            }
            iframe_src = url_for(
                "pwncollege_workspace.forward_workspace",
                service=service_param,
                service_path="vnc.html",
                **vnc_params
            )

        # DESKTOP-WINDOWS SERVICE
        elif service == "desktop-windows":
            service_param = "~".join(("desktop-windows", str(user.id), container_password(container, "desktop-windows")))
            if admin_user:
                vnc_password = container_password(container, "desktop-windows")
            else:
                vnc_password = "password"  # as before

            vnc_params = {
                "autoconnect":    1,
                "reconnect":      1,
                "reconnect_delay":200,
                "resize":         "local",
                "path":           url_for("pwncollege_workspace.forward_workspace", service=service_param, service_path="websockify"),
                "password":       vnc_password,
            }
            iframe_src = url_for(
                "pwncollege_workspace.forward_workspace",
                service=service_param,
                service_path="vnc.html",
                **vnc_params
            )

        # OTHER SERVICES (e.g. code)
        else:
            if admin_user and user_id:
                service_param = f"{service}~{user.id}"
                iframe_src = f"/workspace/{service_param}/"
            else:
                iframe_src = f"/workspace/{service}/"

        # ensure the service is running
        if start_on_demand_service(user, service) is False:
            return {"active": False}

        return {
            "iframe_src": iframe_src,
            "service":    service,
            "active":     True
        }

@workspace_namespace.route("/reset_home")
class ResetHome(Resource):
    @authed_only
    def post(self):
        user = get_current_user()
        if not get_current_container(user):
            return {"success": False, "error": "No running container found. Please start a container and try again."}
        try:
            reset_home(user.id)
        except AssertionError as e:
            return {"success": False, "error": f"Reset failed with error: {e}"}
        return {"success": True, "message": "Home directory reset successfully"}
