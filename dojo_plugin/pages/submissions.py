from flask import Blueprint, render_template, request
from CTFd.utils.decorators import admins_only
from CTFd.models import Submissions, Challenges, Users
from sqlalchemy.orm import joinedload
from sqlalchemy import cast, String
from collections import defaultdict

# Import DojoChallenges to correctly map challenges to dojos
from ..models import DojoChallenges, Dojos, DojoStudents

# Create a new Blueprint for submissions
submissions_bp = Blueprint("submissions", __name__, url_prefix="/admin/submissions")

@submissions_bp.route("/")
@admins_only
def view():
    q = request.args.get("q", "").strip()

    # find the 'course' dojo
    course_dojo = Dojos.query.filter(Dojos.data["type"] == "course").first_or_404()

    # join to students to get only official enrollees
    users_q = (
        Users.query
        .join(DojoStudents, DojoStudents.user_id == Users.id)
        .filter(
            DojoStudents.dojo == course_dojo,
        )
    )

    #  search
    if q:
        users_q = users_q.filter(Users.name.ilike(f"%{q}%"))

    users = users_q.order_by(Users.name).all()

    return render_template("submissions.html", users=users, q=q)

