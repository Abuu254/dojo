from flask import Blueprint, render_template
from CTFd.utils.decorators import admins_only
from CTFd.models import Submissions, Challenges, Users
from sqlalchemy.orm import joinedload
from sqlalchemy import cast, String
from collections import defaultdict

# Import DojoChallenges to correctly map challenges to dojos
from ..models import DojoChallenges, Dojos

# Create a new Blueprint for submissions
submissions_bp = Blueprint("submissions", __name__, url_prefix="/admin/submissions")

@submissions_bp.route("/")
@admins_only
def view():
    # Get only the course dojo
    course_dojo = Dojos.query.filter(Dojos.data["type"] == "course").first()
    if not course_dojo:
        return render_template("submissions.html", grouped={})

    # Get challenges for that dojo
    dojo_challenges = (
        DojoChallenges.query
        .filter_by(dojo_id=course_dojo.dojo_id)
        .options(joinedload(DojoChallenges.challenge), joinedload(DojoChallenges.module))
        .all()
    )

    # Group challenges per module
    modules = defaultdict(list)
    for dc in dojo_challenges:
        if dc.module and dc.challenge:
            modules[dc.module.name].append(dc.challenge)

    users = Users.query.filter(Users.type != "admin").all()
    challenge_ids = [dc.challenge_id for dc in dojo_challenges]

    # Get relevant submissions
    submissions = (
        Submissions.query
        .filter(Submissions.challenge_id.in_(challenge_ids))
        .filter(Submissions.user_id.in_([u.id for u in users]))
        .all()
    )

    submission_map = defaultdict(dict)
    for sub in submissions:
        submission_map[sub.user_id][sub.challenge_id] = sub

    # Group by user -> module -> (challenge, submission)
    grouped_submissions = defaultdict(lambda: defaultdict(list))
    for user in users:
        for module_name, challenges in modules.items():
            for challenge in challenges:
                submission = submission_map.get(user.id, {}).get(challenge.id)
                grouped_submissions[user.name][module_name].append((challenge, submission))

    return render_template("submissions.html", grouped=grouped_submissions)
