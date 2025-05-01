import datetime
import hashlib
import itertools
import re

from flask import Blueprint, Response, render_template, abort, url_for, request, redirect, flash
from sqlalchemy.sql import and_, or_
from CTFd.utils.user import get_current_user
from CTFd.utils.decorators import authed_only
from CTFd.models import db, Users, Challenges, Solves
from CTFd.cache import cache

from ..models import Dojos, DojoModules, DojoChallenges, DojoStudents, LateDayUsage
from ..utils.scores import dojo_scores, module_scores
from ..utils.awards import get_belts, get_viewable_emojis
from ..pages.course import grade
from ..utils.dojo import dojo_route


users = Blueprint("pwncollege_users", __name__)


def view_hacker(user, bypass_hidden=False):
    if user.hidden and not bypass_hidden:
        abort(404)

    dojos = (Dojos
             .viewable(user=get_current_user())
             .filter(Dojos.data["type"] != "hidden")
             .all())

    hacker_courses = []
    late_day_usage = {}

    for dojo in dojos:
        if not dojo.course:
            continue

        student = DojoStudents.query.filter_by(dojo=dojo, user=user).first()
        if not (student and student.official):
            continue

        gd = next(grade(dojo, user, ignore_pending=True), None)
        if not gd:
            continue

        # attach the Dojo object so the template can read dojo.name
        gd["dojo"] = dojo

        # compute late days
        total_late = dojo.course.get("late_days", 0)
        used_late = db.session.query(db.func.sum(LateDayUsage.late_days_used)).filter_by(user_id=user.id, dojo_id=dojo.dojo_id).scalar() or 0

        late_day_usage[dojo.id] = (used_late, total_late)

        hacker_courses.append(gd)

    return render_template(
        "hacker.html",
        user=user,
        current_user=get_current_user(),
        hacker_courses=hacker_courses,
        late_day_usage=late_day_usage,
        dojo_scores=dojo_scores(),
        module_scores=module_scores(),
        belts=get_belts(),
        badges=get_viewable_emojis(user),
    )

@users.route("/hacker/<int:user_id>")
def view_other(user_id):
    user = Users.query.filter_by(id=user_id).first()
    if user is None or user.hidden:
        abort(404)
    return view_hacker(user)

@users.route("/hacker/<user_name>")
def view_other_name(user_name):
    user = Users.query.filter_by(name=user_name).first()
    if user is None or user.hidden:
        abort(404)
    return view_hacker(user)

@users.route("/hacker/")
@authed_only
def view_self():
    return view_hacker(get_current_user(), bypass_hidden=True)
