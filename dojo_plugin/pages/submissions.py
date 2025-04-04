from flask import Blueprint, render_template
from CTFd.utils.decorators import admins_only
from CTFd.models import Submissions, Challenges, Users
from sqlalchemy.orm import joinedload
from collections import defaultdict

# Import DojoChallenges to correctly map challenges to dojos
from ..models import DojoChallenges, Dojos

# Create a new Blueprint for submissions
submissions_bp = Blueprint("submissions", __name__, url_prefix="/admin/submissions")

@submissions_bp.route("/")
@admins_only
def view():
    """Fetch and group submissions by users → dojos → challenges"""
    submissions = (
        Submissions.query
        .options(joinedload(Submissions.user), joinedload(Submissions.challenge))
        .filter(Submissions.user_id.isnot(None))  # Ignore team submissions
        .order_by(Submissions.date.desc())
        .all()
    )

    # Structure: {user: {dojo: [challenges]}}
    grouped_submissions = defaultdict(lambda: defaultdict(list))

    for sub in submissions:
        # Skip admin users
        if sub.user.type == "admin":
            continue
        user_key = sub.user.name if sub.user else "Unknown User"

        # Map the submission's challenge to the correct dojo
        dojo_challenge = DojoChallenges.query.filter_by(challenge_id=sub.challenge_id).first()
        dojo_key = dojo_challenge.dojo.name if dojo_challenge and dojo_challenge.dojo else "Unknown Dojo"

        grouped_submissions[user_key][dojo_key].append(sub)

    return render_template("submissions.html", grouped_submissions=grouped_submissions)
