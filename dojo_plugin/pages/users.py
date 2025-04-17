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
    user_solves = {}
    course_grade_details = {}
    late_day_usage = {}

    for dojo in dojos:
        if not dojo.course:
            dojo_id = dojo.id
            user_solves[dojo_id] = {}

            for module in dojo.modules:
                module_id = module.id
                solves = module.solves(user=user, ignore_visibility=True, ignore_admins=False) if user else []

                if solves:
                    user_solves[dojo_id][module_id] = {
                        solve.challenge_id: solve.date.strftime("%Y-%m-%d %H:%M:%S") for solve in solves
                    }
        if dojo.course:
            student = DojoStudents.query.filter_by(dojo=dojo, user=user).first()
            if student and student.official:
                result = next(grade(dojo, user, ignore_pending=True), None)
                if result:
                    course_grade_details[dojo.id] = result
                # Add late day usage per course
                total_late_days = dojo.course.get("late_days", 0)
                used_late_days = (
                    db.session.query(db.func.sum(LateDayUsage.late_days_used))
                    .filter_by(user_id=user.id, dojo_id=dojo.dojo_id)
                    .scalar()
                ) or 0
                late_day_usage[dojo.id] = (used_late_days, total_late_days)

    return render_template(
        "hacker.html",
        dojos=dojos, user=user,
        dojo_scores=dojo_scores(), module_scores=module_scores(),
        belts=get_belts(), badges=get_viewable_emojis(user),
        user_solves=user_solves,
        course_grades=course_grade_details,
        current_user=get_current_user(),
        late_day_usage=late_day_usage,
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
