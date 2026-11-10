from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date, datetime, time, timedelta
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    profile = db.relationship("StudentProfile", backref="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), unique=True, nullable=False)
    education = db.Column(db.String(240), default="")
    graduation_year = db.Column(db.Integer)
    target_roles = db.Column(db.String(500), default="Software Engineer, DevOps Engineer")
    preferred_locations = db.Column(db.String(300), default="Hyderabad, India, Remote")
    timezone = db.Column(db.String(80), default="Asia/Kolkata")
    weekly_hours = db.Column(db.Float, default=8)
    daily_hours = db.Column(db.Float, default=2)
    session_minutes = db.Column(db.Integer, default=45)
    study_days = db.Column(db.String(40), default="0,1,2,3,4,5")
    study_start = db.Column(db.String(5), default="19:00")
    study_end = db.Column(db.String(5), default="21:00")
    unavailable_dates = db.Column(db.Text, default="")
    fixed_commitments = db.Column(db.Text, default="")
    rest_days = db.Column(db.String(40), default="6")
    resume_url = db.Column(db.String(500), default="")
    portfolio_url = db.Column(db.String(500), default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    skills = db.relationship("Skill", backref="profile", cascade="all, delete-orphan")


class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("student_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    proficiency = db.Column(db.String(20), nullable=False, default="self-reported")
    evidence = db.Column(db.String(500), default="")
    __table_args__ = (UniqueConstraint("profile_id", "name", name="uq_profile_skill"),)


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    title = db.Column(db.String(240), nullable=False)
    company = db.Column(db.String(240), nullable=False)
    location = db.Column(db.String(240), default="Unavailable")
    employment_type = db.Column(db.String(80), default="Unavailable")
    description = db.Column(db.Text, default="")
    skills_json = db.Column(db.Text, default="[]")
    url = db.Column(db.String(1000), nullable=False)
    source = db.Column(db.String(100), nullable=False)
    published_at = db.Column(db.String(80), default="Unavailable")
    deadline = db.Column(db.Date, nullable=True)
    salary = db.Column(db.String(240), default="Unavailable")
    verified_at = db.Column(db.DateTime, default=datetime.utcnow)
    saved_by = db.relationship("SavedJob", backref="job", cascade="all, delete-orphan")

    @property
    def skills(self):
        try:
            return json.loads(self.skills_json)
        except (TypeError, json.JSONDecodeError):
            return []


class SavedJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    target_date = db.Column(db.Date, nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_saved_job"),)


class PreparationPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    target_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default="active")
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_plan_job"),)
    job = db.relationship("Job")
    sessions = db.relationship("StudySession", backref="plan", cascade="all, delete-orphan", order_by="StudySession.start_at")


class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("preparation_plan.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(240), nullable=False)
    objective = db.Column(db.Text, nullable=False)
    exercise = db.Column(db.Text, nullable=False)
    deliverable = db.Column(db.Text, nullable=False)
    resource_title = db.Column(db.String(240), nullable=False)
    resource_url = db.Column(db.String(1000), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="scheduled")
    priority = db.Column(db.Integer, default=2)
    dependency_id = db.Column(db.Integer, db.ForeignKey("study_session.id"), nullable=True)
    dependency = db.relationship("StudySession", remote_side="StudySession.id", foreign_keys=[dependency_id])
    completion_evidence = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScheduleEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("study_session.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.String(30), nullable=False)
    note = db.Column(db.Text, default="")
    occurred_at = db.Column(db.DateTime, default=datetime.utcnow)
    session = db.relationship("StudySession", backref="history")


class JobSearchFetch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(100), nullable=False, index=True)
    fetched_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(30), default="Saved")
    notes = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    job = db.relationship("Job")
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_application_job"),)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(240), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="open")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


SKILL_RESOURCES = {
    "python": ("Python tutorial", "https://docs.python.org/3/tutorial/"),
    "docker": ("Docker Get Started", "https://docs.docker.com/get-started/"),
    "kubernetes": ("Kubernetes Basics", "https://kubernetes.io/docs/tutorials/kubernetes-basics/"),
    "jenkins": ("Jenkins Pipeline documentation", "https://www.jenkins.io/doc/book/pipeline/"),
    "git": ("Pro Git book", "https://git-scm.com/book/en/v2"),
    "linux": ("Linux command line introduction", "https://ubuntu.com/tutorials/command-line-for-beginners"),
    "sql": ("PostgreSQL tutorial", "https://www.postgresql.org/docs/current/tutorial.html"),
    "flask": ("Flask tutorial", "https://flask.palletsprojects.com/en/stable/tutorial/"),
    "aws": ("AWS Skill Builder Cloud Practitioner Essentials", "https://skillbuilder.aws/"),
    "ci/cd": ("GitHub Actions CI documentation", "https://docs.github.com/en/actions"),
}
SKILL_ALIASES = {"k8s": "kubernetes", "postgresql": "sql", "c++": "c++", "node.js": "node", "ci cd": "ci/cd"}
STOP_WORDS = {"and", "with", "from", "that", "this", "will", "have", "your", "our", "their", "the", "for", "you", "are", "role", "work", "team", "years", "experience", "skills", "ability", "strong", "good", "using", "build", "working", "across", "into", "about", "must", "required", "preferred", "responsibilities"}


def canonical_skill(value):
    key = re.sub(r"\s+", " ", value.strip().lower())
    return SKILL_ALIASES.get(key, key)


def extract_skills(text):
    known = set(SKILL_RESOURCES) | {"java", "javascript", "typescript", "react", "node", "go", "rust", "terraform", "ansible", "azure", "gcp", "html", "css", "communication", "data structures", "linux", "monitoring", "prometheus", "grafana", "helm", "security", "networking"}
    low = (text or "").lower()
    found = {s for s in known if re.search(r"(?<![\w+#])" + re.escape(s) + r"(?![\w+#])", low)}
    # Keep meaningful technical tokens from incomplete descriptions, marked as extracted rather than verified.
    for token in re.findall(r"\b[a-z][a-z0-9+#.-]{2,}\b", low):
        if token not in STOP_WORDS and token not in {"company", "candidate", "application", "position", "responsible", "including", "develop", "developing", "ensure", "provide", "support", "related", "looking", "join", "across", "strongly", "please", "equal", "opportunity"} and (token in known or token in {"microservices", "api", "rest", "agile", "testing", "cloud", "automation", "scripting", "containers", "deployment"}):
            found.add(token)
    return sorted(found)


def get_timezone(profile):
    try:
        return ZoneInfo(profile.timezone or "Asia/Kolkata")
    except ZoneInfoNotFoundError:
        return ZoneInfo("Asia/Kolkata")


def skill_match(job, profile):
    required = set(job.skills)
    owned = {canonical_skill(s.name) for s in profile.skills}
    demonstrated = {canonical_skill(s.name) for s in profile.skills if s.proficiency in ("assessed", "demonstrated")}
    exact = required & owned
    partial = {canonical_skill(s.name) for s in profile.skills if s.proficiency == "partial"}
    self_reported = {canonical_skill(s.name) for s in profile.skills if s.proficiency == "self-reported"}
    return {"required": sorted(required), "matched": sorted(exact), "demonstrated": sorted(required & demonstrated), "self_reported": sorted(required & self_reported), "partial": sorted(required & partial), "missing": sorted(required - owned), "unknown": ["eligibility and assessment expectations"] if not job.description.strip() else [], "percent": round(100 * len(exact) / max(1, len(required))), "is_estimate": not bool(job.description.strip())}


ROLE_VARIANTS = {
    "software engineer": ("software engineer", "software developer", "software engineering", "backend engineer", "backend developer", "frontend engineer", "frontend developer", "full stack engineer", "full stack developer", "software intern", "developer intern", "swe intern"),
    "devops engineer": ("devops", "dev ops", "site reliability", "platform engineer", "cloud engineer", "infrastructure engineer", "devops intern"),
}


def role_phrases(profile):
    roles = [canonical_skill(x) for x in (profile.target_roles or "").split(",") if x.strip()]
    return roles[:2] or ["software engineer", "devops engineer"]


def title_role_index(job, roles):
    title = re.sub(r"[^a-z0-9]+", " ", job.title.lower()).strip()
    for index, role in enumerate(roles):
        variants = ROLE_VARIANTS.get(role, (role,))
        if any(re.sub(r"[^a-z0-9]+", " ", variant).strip() in title for variant in variants):
            return index
    return None


def location_fit(job, profile):
    location = (job.location or "").lower()
    preferences = (profile.preferred_locations or "india, hyderabad, remote").lower()
    if any(place.strip() in location for place in preferences.split(",") if place.strip() and place.strip() != "remote"):
        return "Preferred location listed"
    if any(word in location for word in ("worldwide", "remote", "anywhere")):
        return "Remote; confirm India eligibility"
    return "Check location eligibility on source"


def cached_job_search(query="", profile=None):
    q = (query or "").strip()[:80]
    profile = profile or StudentProfile(target_roles="Software Engineer, DevOps Engineer", preferred_locations="Hyderabad, India, Remote")
    queries = [q] if q else role_phrases(profile)
    now = datetime.utcnow()
    requests_today = db.session.scalar(db.select(db.func.count(JobSearchFetch.id)).filter(JobSearchFetch.fetched_at >= now - timedelta(hours=24))) or 0
    # Remotive advises a maximum of four public-feed requests per day; cache each query for six hours.
    for term in queries:
        normalized = term.lower().strip()
        latest = db.session.scalar(db.select(JobSearchFetch).filter_by(query=normalized).order_by(JobSearchFetch.fetched_at.desc()).limit(1))
        if latest and now - latest.fetched_at < timedelta(hours=6):
            continue
        if requests_today >= 4:
            continue
        data = []
        try:
            response = requests.get("https://remotive.com/api/remote-jobs", params={"search": term[:80], "limit": 100}, timeout=8, headers={"User-Agent": "ASDA-career-preparation/1.0"})
            response.raise_for_status()
            data = response.json().get("jobs", [])
        except (requests.RequestException, ValueError, TypeError):
            pass
        db.session.add(JobSearchFetch(query=normalized, fetched_at=now))
        requests_today += 1
        for item in data:
            url = item.get("url")
            title = item.get("title")
            company = item.get("company_name")
            if not url or not str(url).startswith("https://") or not title or not company:
                continue
            ext_id = f"remotive:{item.get('id') or hashlib.sha256(url.encode()).hexdigest()[:24]}"
            job = db.session.scalar(db.select(Job).filter_by(external_id=ext_id)) or Job(external_id=ext_id, title=title[:240], company=company[:240], url=url[:1000], source="Remotive")
            job.location = str(item.get("candidate_required_location") or "Remote; eligibility location unavailable")[:240]
            job.employment_type = str(item.get("job_type") or "Unavailable")[:80]
            job.description = str(item.get("description") or "")[:30000]
            job.skills_json = json.dumps(extract_skills(job.title + " " + job.description))
            job.published_at = str(item.get("publication_date") or "Unavailable")[:80]
            job.salary = str(item.get("salary") or "Unavailable")[:240]
            job.verified_at = now
            db.session.add(job)
        db.session.commit()

    rows = db.session.scalars(db.select(Job).order_by(Job.verified_at.desc()).limit(300)).all()
    if q:
        needle = q.lower()
        rows = [job for job in rows if needle in job.title.lower() or needle in job.company.lower() or needle in job.description.lower()]
    else:
        roles = role_phrases(profile)
        # The default student discovery feed must not present senior-only jobs as
        # plausible opportunities. Keep broader senior listings available when
        # the user explicitly searches for them.
        senior_markers = ("senior", "staff", "principal", "lead", "director", "head of")
        rows = [
            job for job in rows
            if title_role_index(job, roles) is not None
            and not any(marker in job.title.lower() for marker in senior_markers)
            and not re.search(r"\b(experienced|5\+ years|7\+ years|10\+ years)\b", job.description.lower())
        ]
        preferred = [x.strip().lower() for x in (profile.preferred_locations or "").split(",") if x.strip()]
        rows.sort(key=lambda job: (
            title_role_index(job, roles),
            0 if any(place in job.location.lower() for place in preferred if place != "remote") else (1 if any(w in job.location.lower() for w in ("worldwide", "remote", "anywhere")) else 2),
            0 if any(level in job.title.lower() for level in ("intern", "junior", "entry level", "graduate", "associate")) else 1,
            -job.verified_at.timestamp() if job.verified_at else 0,
        ), reverse=False)
    return rows[:50]


def build_curriculum(job, profile):
    analysis = skill_match(job, profile)
    target = analysis["missing"]
    if not target:
        target = ["role-specific practice"]
    items = []
    for skill in target[:8]:
        resource = SKILL_RESOURCES.get(skill, (f"{skill.title()} resource search (direct page not verified)", f"https://www.google.com/search?q={quote_plus(skill + ' official documentation')}"))
        inferred = skill not in job.skills or analysis["is_estimate"]
        label = "Estimated starter topic" if inferred else "Extracted from vacancy description"
        items.append({"title": f"{skill.title()} foundations", "objective": f"Explain the core concepts of {skill} and identify where they apply to the selected role. ({label})", "exercise": f"Create a small role-relevant example using {skill}; record the commands, decisions, and one failure you investigated.", "deliverable": f"A runnable example or concise notes demonstrating {skill}, with a README and evidence of the result.", "resource": resource, "duration": int(profile.session_minutes or 45), "priority": 1 if skill in analysis["missing"] else 2})
    items.append({"title": "Role-aligned project and interview review", "objective": f"Connect the learned skills to responsibilities in the {job.title} vacancy and identify remaining uncertainty.", "exercise": "Improve one portfolio project or complete a small scenario, then explain your design and trade-offs aloud.", "deliverable": "A project link or written walkthrough, plus three questions to validate with the employer.", "resource": ("STAR interview method guide", "https://www.careeronestop.org/JobSearch/Interview/star-method.aspx"), "duration": int(profile.session_minutes or 45), "priority": 2})
    return analysis, items


def available_slots(profile, target, minutes, existing):
    tz = get_timezone(profile)
    now = datetime.now(tz).replace(second=0, microsecond=0)
    start_time = time.fromisoformat(profile.study_start or "19:00")
    end_time = time.fromisoformat(profile.study_end or "21:00")
    weekdays = {int(x) for x in (profile.study_days or "0,1,2,3,4,5").split(",") if x.isdigit()}
    if not weekdays:
        weekdays = {0, 1, 2, 3, 4, 5}
    rest_days = {int(x) for x in (profile.rest_days or "").split(",") if x.strip().isdigit()}
    weekdays -= rest_days
    unavailable = {x.strip() for x in (profile.unavailable_dates or "").split(",") if x.strip()}
    busy_dates = {(s.start_at.date(), s.start_at.time(), s.end_at.time()) for s in existing if s.status == "scheduled"}
    commitments = []
    day_names = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    for match in re.finditer(r"\b(mon|tue|wed|thu|fri|sat|sun)\s+(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\b", profile.fixed_commitments or "", re.I):
        try:
            commitments.append((day_names[match.group(1).lower()], time.fromisoformat(match.group(2)), time.fromisoformat(match.group(3))))
        except ValueError:
            pass
    daily_session_cap = max(1, int(float(profile.daily_hours or 2) * 60 // max(minutes, 1)))
    weekly_session_cap = max(1, int(float(profile.weekly_hours or 8) * 60 // max(minutes, 1)))
    day_counts = {}
    week_counts = {}
    for session in existing:
        if session.status == "scheduled":
            iso = session.start_at.date().isocalendar()
            key = (iso.year, iso.week)
            week_counts[key] = week_counts.get(key, 0) + 1
    for d in range((target - now.date()).days + 1):
        day = now.date() + timedelta(days=d)
        if day.weekday() not in weekdays or day.isoformat() in unavailable:
            continue
        cursor = datetime.combine(day, start_time, tzinfo=tz)
        last = datetime.combine(day, end_time, tzinfo=tz)
        if day == now.date() and cursor < now:
            cursor = now.replace(minute=(now.minute // 5 + 1) * 5 % 60, second=0)
            if cursor.minute == 0:
                cursor += timedelta(hours=1)
        count = day_counts.get(day, 0)
        iso = day.isocalendar()
        week_key = (iso.year, iso.week)
        while cursor + timedelta(minutes=minutes) <= last and count < daily_session_cap and week_counts.get(week_key, 0) < weekly_session_cap:
            end = cursor + timedelta(minutes=minutes)
            conflict = any(bd == day and cursor.time() < be and bs < end.time() for bd, bs, be in busy_dates)
            conflict = conflict or any(day.weekday() == wd and cursor.time() < be and bs < end.time() for wd, bs, be in commitments)
            if not conflict:
                yield cursor.replace(tzinfo=None), end.replace(tzinfo=None)
                count += 1
                week_counts[week_key] = week_counts.get(week_key, 0) + 1
            cursor = end + timedelta(minutes=10)
        day_counts[day] = count


def schedule_plan(plan, curriculum, profile, preserve=True):
    sessions = plan.sessions[:]
    existing = [s for s in sessions if s.status in ("scheduled", "completed")]
    pending = [s for s in sessions if s.status == "missed"] if preserve else []
    if not preserve:
        existing = [s for s in sessions if s.status == "completed"]
        pending = [s for s in sessions if s.status not in ("completed", "deferred")]
    active_titles = {s.title for s in sessions if s.status in ("scheduled", "completed")}
    work = [item for item in curriculum if item["title"] not in active_titles]
    for s in sessions:
        if s.status == "missed" and all(item["title"] != s.title for item in work):
            template = next((i for i in curriculum if i["title"] == s.title), None)
            if template:
                work.insert(0, template)
    slots = iter(available_slots(profile, plan.target_date, int(profile.session_minutes or 45), existing))
    changes = []
    for item in work:
        try:
            start, end = next(slots)
        except StopIteration:
            break
        s = next((x for x in sessions if x.title == item["title"] and x.status in ("missed", "deferred")), None)
        if s:
            s.status = "scheduled"
            s.start_at, s.end_at = start, end
            s.duration_minutes = item["duration"]
            db.session.add(ScheduleEvent(session_id=s.id, event_type="rescheduled", note="Moved to the next available study slot after schedule recalculation."))
            changes.append(f"{s.title} moved to {start:%Y-%m-%d %H:%M}")
        else:
            s = StudySession(plan=plan, title=item["title"], objective=item["objective"], exercise=item["exercise"], deliverable=item["deliverable"], resource_title=item["resource"][0], resource_url=item["resource"][1], duration_minutes=item["duration"], start_at=start, end_at=end, status="scheduled", priority=item["priority"])
            db.session.add(s)
            sessions.append(s)
    unscheduled = [item for item in work if not any(s.title == item["title"] and s.status in ("scheduled", "completed") for s in sessions)]
    for item in unscheduled:
        prior = next((s for s in sessions if s.title == item["title"] and s.status in ("missed", "deferred")), None)
        if prior:
            prior.status = "deferred"
        else:
            prior = StudySession(plan=plan, title=item["title"], objective=item["objective"], exercise=item["exercise"], deliverable=item["deliverable"], resource_title=item["resource"][0], resource_url=item["resource"][1], duration_minutes=item["duration"], start_at=datetime.combine(plan.target_date, time.min), end_at=datetime.combine(plan.target_date, time.min), status="deferred", priority=item["priority"])
            db.session.add(prior)
            sessions.append(prior)
    if unscheduled:
        plan.status = "schedule_conflict"
        changes.append("These sessions remain listed as deferred because they do not fit before the target date: " + ", ".join(item["title"] for item in unscheduled))
    elif plan.status == "schedule_conflict":
        plan.status = "active"
    db.session.flush()
    ordered_sessions = sorted((s for s in plan.sessions if s.status in ("scheduled", "completed")), key=lambda s: s.start_at)
    for index, session in enumerate(ordered_sessions):
        session.dependency_id = ordered_sessions[index - 1].id if index else None
    return changes


def owner_job(job_id):
    job = db.session.get(Job, job_id)
    if not job or not db.session.scalar(db.select(SavedJob).filter_by(user_id=current_user.id, job_id=job_id)):
        abort(404)
    return job


def create_app(test_config=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", ""),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///asda.db").replace("postgres://", "postgresql://", 1),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        WTF_CSRF_TIME_LIMIT=3600,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Set SECRET_KEY before starting ASDA. Copy .env.example and use a unique secret.")
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"
    csrf.init_app(app)
    migrate.init_app(app, db)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_globals():
        return {"today": date.today(), "current_year": date.today().year, "location_fit": location_fit}

    @app.get("/healthz")
    def healthz():
        try:
            db.session.execute(db.text("SELECT 1"))
            return {"status": "ok", "service": "asda"}, 200
        except Exception:
            db.session.rollback()
            return {"status": "unavailable"}, 503

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(password) < 12:
                flash("Enter a valid email and a password with at least 12 characters.", "error")
            elif db.session.scalar(db.select(User).filter_by(email=email)):
                flash("An account with that email already exists.", "error")
            else:
                user = User(email=email)
                user.set_password(password)
                user.profile = StudentProfile()
                db.session.add(user)
                db.session.commit()
                login_user(user)
                return redirect(url_for("dashboard"))
        return render_template("auth.html", mode="register")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            user = db.session.scalar(db.select(User).filter_by(email=request.form.get("email", "").strip().lower()))
            if not user or not user.check_password(request.form.get("password", "")):
                flash("Email or password was not recognized.", "error")
            else:
                login_user(user, remember=False, fresh=True)
                return redirect(url_for("dashboard"))
        return render_template("auth.html", mode="login")

    @app.post("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def dashboard():
        now = datetime.utcnow()
        plans = db.session.scalars(db.select(PreparationPlan).filter_by(user_id=current_user.id).order_by(PreparationPlan.created_at.desc())).all()
        plan_ids = [p.id for p in plans]
        sessions = db.session.scalars(db.select(StudySession).filter(StudySession.plan_id.in_(plan_ids), StudySession.status == "scheduled").order_by(StudySession.start_at).limit(5)).all() if plan_ids else []
        saved = db.session.scalars(db.select(SavedJob).filter_by(user_id=current_user.id).order_by(SavedJob.saved_at.desc())).all()
        todos = db.session.scalars(db.select(Todo).filter_by(user_id=current_user.id, status="open").order_by(Todo.due_date, Todo.created_at).limit(5)).all()
        all_sessions = db.session.scalars(db.select(StudySession).join(PreparationPlan).filter(PreparationPlan.user_id == current_user.id)).all()
        complete = sum(s.status == "completed" for s in all_sessions)
        return render_template("dashboard.html", sessions=sessions, saved=saved, todos=todos, complete=complete, total=len(all_sessions), profile=current_user.profile)

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        p = current_user.profile
        if request.method == "POST":
            try:
                hours = float(request.form.get("weekly_hours", 8))
                daily_hours = float(request.form.get("daily_hours", 2))
                duration = int(request.form.get("session_minutes", 45))
                year = request.form.get("graduation_year", "").strip()
                if not 1 <= hours <= 60 or not 0.5 <= daily_hours <= 12 or not 15 <= duration <= 180 or (year and not 2000 <= int(year) <= date.today().year + 10):
                    raise ValueError
                timezone = request.form.get("timezone", "Asia/Kolkata").strip()
                ZoneInfo(timezone)
                start, end = time.fromisoformat(request.form.get("study_start", "19:00")), time.fromisoformat(request.form.get("study_end", "21:00"))
                if start >= end:
                    raise ValueError
            except (ValueError, ZoneInfoNotFoundError):
                flash("Check the hours, session duration, year, time window and timezone values.", "error")
                return redirect(url_for("profile"))
            p.education = request.form.get("education", "")[:240]
            p.graduation_year = int(year) if year else None
            p.target_roles = request.form.get("target_roles", "")[:500]
            p.preferred_locations = request.form.get("preferred_locations", "")[:300]
            p.timezone, p.weekly_hours, p.daily_hours, p.session_minutes = timezone, hours, daily_hours, duration
            p.study_days = ",".join(str(x) for x in range(7) if str(x) in request.form.getlist("study_days"))
            p.study_start, p.study_end = start.isoformat(timespec="minutes"), end.isoformat(timespec="minutes")
            p.unavailable_dates = request.form.get("unavailable_dates", "")[:1000]
            p.fixed_commitments = request.form.get("fixed_commitments", "")[:2000]
            p.rest_days = request.form.get("rest_days", "")[:40]
            p.resume_url, p.portfolio_url = request.form.get("resume_url", "")[:500], request.form.get("portfolio_url", "")[:500]
            for s in list(p.skills):
                db.session.delete(s)
            # Flush pending deletes before inserting replacements. The profile
            # skill uniqueness constraint is immediate in SQLite/PostgreSQL.
            db.session.flush()
            names = set()
            for line in request.form.get("skills", "").splitlines():
                parts = [x.strip() for x in line.split("|", 2)]
                name = canonical_skill(parts[0])
                if not name or name in names:
                    continue
                names.add(name)
                proficiency = parts[1].lower() if len(parts) > 1 else "self-reported"
                if proficiency not in {"self-reported", "assessed", "demonstrated", "partial"}:
                    proficiency = "self-reported"
                db.session.add(Skill(profile=p, name=name, proficiency=proficiency, evidence=parts[2][:500] if len(parts) > 2 else ""))
            db.session.commit()
            plans = db.session.scalars(db.select(PreparationPlan).filter_by(user_id=current_user.id)).all()
            schedule_notes = []
            for plan in plans:
                _, curriculum = build_curriculum(plan.job, p)
                current_titles = {item["title"] for item in curriculum}
                for session in plan.sessions:
                    if session.status == "scheduled" and session.title not in current_titles:
                        session.status = "deferred"
                        db.session.add(ScheduleEvent(session_id=session.id, event_type="deferred", note="Requirements changed after the student profile was updated; task retained for review."))
                schedule_notes.extend(schedule_plan(plan, curriculum, p, preserve=True))
            db.session.commit()
            flash("Profile saved. Existing plans were recalculated while completed sessions were preserved. " + " ".join(schedule_notes), "success")
            return redirect(url_for("profile"))
        return render_template("profile.html", profile=p)

    @app.get("/jobs")
    @login_required
    def jobs():
        q = request.args.get("q", "")[:80]
        listings = cached_job_search(q, current_user.profile)
        saved_ids = {x.job_id for x in db.session.scalars(db.select(SavedJob).filter_by(user_id=current_user.id)).all()}
        slug = re.sub(r"[^a-z0-9]+", "-", (q or "software-engineer-internship").lower()).strip("-")
        return render_template("jobs.html", jobs=listings, saved_ids=saved_ids, q=q, searches={"Naukri": "https://www.naukri.com/" + slug + "-jobs-in-hyderabad", "Unstop": "https://unstop.com/jobs?search=" + quote_plus(q or "software internship")})

    @app.post("/jobs/<int:job_id>/save")
    @login_required
    def save_job(job_id):
        job = db.session.get(Job, job_id)
        if not job:
            abort(404)
        saved = db.session.scalar(db.select(SavedJob).filter_by(user_id=current_user.id, job_id=job.id))
        if not saved:
            try:
                horizon = int(request.form.get("horizon", 14))
            except ValueError:
                horizon = 0
            if not 1 <= horizon <= 90:
                flash("Preparation horizon must be 1 to 90 days.", "error")
                return redirect(url_for("jobs"))
            target = job.deadline or date.today() + timedelta(days=horizon)
            saved = SavedJob(user_id=current_user.id, job_id=job.id, target_date=target)
            db.session.add(saved)
            app_record = Application(user_id=current_user.id, job_id=job.id, status="Saved")
            db.session.add(app_record)
            plan = PreparationPlan(user_id=current_user.id, job_id=job.id, target_date=target)
            db.session.add(plan)
            _, curriculum = build_curriculum(job, current_user.profile)
            db.session.flush()
            changes = schedule_plan(plan, curriculum, current_user.profile, preserve=False)
            db.session.commit()
            flash("Job saved and its preparation plan created. " + (" ".join(changes) if changes else ""), "success")
        return redirect(url_for("job_detail", job_id=job.id))

    @app.get("/jobs/<int:job_id>")
    @login_required
    def job_detail(job_id):
        job = db.session.get(Job, job_id)
        if not job:
            abort(404)
        saved = db.session.scalar(db.select(SavedJob).filter_by(user_id=current_user.id, job_id=job.id))
        analysis, curriculum = build_curriculum(job, current_user.profile)
        return render_template("job_detail.html", job=job, saved=saved, analysis=analysis, curriculum=curriculum)

    @app.get("/plan")
    @login_required
    def plans():
        rows = db.session.scalars(db.select(PreparationPlan).filter_by(user_id=current_user.id).order_by(PreparationPlan.created_at.desc())).all()
        return render_template("plan.html", plans=rows)

    @app.post("/sessions/<int:session_id>/status")
    @login_required
    def session_status(session_id):
        session = db.session.get(StudySession, session_id)
        if not session or session.plan.user_id != current_user.id:
            abort(404)
        status = request.form.get("status")
        if status not in {"completed", "missed", "scheduled"}:
            abort(400)
        previous = session.status
        if previous == "completed" and status != "completed":
            flash("Completed work is preserved and cannot be reverted.", "error")
            return redirect(request.referrer or url_for("plans"))
        session.status = status
        session.completion_evidence = request.form.get("evidence", "")[:1000] if status == "completed" else session.completion_evidence
        db.session.add(ScheduleEvent(session_id=session.id, event_type=status, note=session.completion_evidence if status == "completed" else "Status changed from " + previous))
        plan = session.plan
        if status == "missed":
            _, curriculum = build_curriculum(plan.job, current_user.profile)
            changes = schedule_plan(plan, curriculum, current_user.profile, preserve=True)
            flash("Missed session recorded. " + (" ".join(changes) if changes else "Remaining sessions were recalculated."), "success")
        else:
            db.session.commit()
            flash("Session status saved.", "success")
        db.session.commit()
        return redirect(request.referrer or url_for("plans"))

    @app.get("/decision")
    @login_required
    def decision_lab():
        saved = db.session.scalars(db.select(SavedJob).filter_by(user_id=current_user.id)).all()
        results = []
        capacity = float(current_user.profile.weekly_hours or 8)
        for row in saved:
            match = skill_match(row.job, current_user.profile)
            deadline = row.job.deadline
            if not match["missing"] and (not deadline or deadline >= date.today()):
                recommendation, why = "Apply now", "No extracted skill gaps remain in the saved profile; confirm eligibility and evidence before applying."
            elif deadline and (deadline - date.today()).days < 7 and match["missing"]:
                recommendation, why = "Apply while continuing preparation", "A short deadline and identified gaps make parallel preparation more practical."
            elif match["percent"] >= 60:
                recommendation, why = "Prepare first", "The current profile matches many extracted skills; address the listed gaps and review eligibility."
            else:
                recommendation, why = "Assess missing skills", "The match is low or incomplete; validate the extracted requirements and your demonstrated ability."
            results.append((row, match, recommendation, why, capacity))
        return render_template("decision.html", results=results)

    @app.route("/applications", methods=["GET", "POST"])
    @login_required
    def applications():
        if request.method == "POST":
            record = db.session.get(Application, int(request.form.get("application_id", 0)))
            if not record or record.user_id != current_user.id:
                abort(404)
            status = request.form.get("status")
            if status not in {"Saved", "Preparing", "Applied", "Assessment", "Interview", "Offer", "Rejected"}:
                abort(400)
            record.status = status
            record.notes = request.form.get("notes", "")[:2000]
            db.session.commit()
            flash("Application tracker updated.", "success")
            return redirect(url_for("applications"))
        rows = db.session.scalars(db.select(Application).filter_by(user_id=current_user.id).order_by(Application.updated_at.desc())).all()
        return render_template("applications.html", applications=rows)

    @app.route("/todos", methods=["GET", "POST"])
    @login_required
    def todos():
        if request.method == "POST":
            if request.form.get("action") == "complete":
                item = db.session.get(Todo, int(request.form.get("todo_id", 0)))
                if not item or item.user_id != current_user.id:
                    abort(404)
                item.status = "completed"
            else:
                title = request.form.get("title", "").strip()
                if not title or len(title) > 240:
                    flash("To-do title is required and must be under 240 characters.", "error")
                    return redirect(url_for("todos"))
                try:
                    due = date.fromisoformat(request.form["due_date"]) if request.form.get("due_date") else None
                except ValueError:
                    flash("Enter a valid due date.", "error")
                    return redirect(url_for("todos"))
                db.session.add(Todo(user_id=current_user.id, title=title, due_date=due))
            db.session.commit()
            return redirect(url_for("todos"))
        rows = db.session.scalars(db.select(Todo).filter_by(user_id=current_user.id).order_by(Todo.status, Todo.due_date, Todo.created_at.desc())).all()
        return render_template("todos.html", todos=rows)

    @app.get("/progress")
    @login_required
    def progress():
        rows = db.session.scalars(db.select(StudySession).join(PreparationPlan).filter(PreparationPlan.user_id == current_user.id).order_by(StudySession.updated_at.desc())).all()
        events = db.session.scalars(db.select(ScheduleEvent).join(StudySession).join(PreparationPlan).filter(PreparationPlan.user_id == current_user.id).order_by(ScheduleEvent.occurred_at.desc()).limit(100)).all()
        return render_template("progress.html", sessions=rows, events=events)

    @app.post("/plans/<int:plan_id>/refresh")
    @login_required
    def refresh_plan(plan_id):
        plan = db.session.get(PreparationPlan, plan_id)
        if not plan or plan.user_id != current_user.id:
            abort(404)
        analysis, curriculum = build_curriculum(plan.job, current_user.profile)
        changes = schedule_plan(plan, curriculum, current_user.profile, preserve=True)
        db.session.commit()
        flash("Plan recalculated using your current skills and availability. " + (" ".join(changes) if changes else "No new sessions were needed."), "success")
        return redirect(url_for("plans"))

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="That page or record is not available in your account."), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
