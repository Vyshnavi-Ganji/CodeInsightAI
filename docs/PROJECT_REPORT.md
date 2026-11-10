# ASDA project report

## Objective

Deliver a Flask student career preparation system that connects real job information to explainable skill matching, learning plans, a flexible timetable, application tracking and an automated container deployment path.

## Architecture

The Flask application in `asda/app.py` serves authenticated pages and uses SQLAlchemy models with Flask-Migrate/Alembic schema versioning. SQLite is the local default; PostgreSQL is supported through `DATABASE_URL`. External job discovery is isolated behind `cached_job_search`, which consumes the public Remotive remote jobs API, caches sourced records and preserves each listing's actual URL and retrieval timestamp. Naukri and Unstop links are board searches, clearly labeled as searches.

Skill extraction uses deterministic keyword rules and profile evidence levels. Plan generation makes a curriculum from current gaps or a disclosed starter topic, with learning objectives, resources, practical work and deliverables. The scheduler respects the profile time zone, study days, rest days, study window, weekly capacity, unavailable dates, fixed weekly commitments and existing sessions. It records missed/rescheduled/deferred events and retains completed sessions.

## Core entities

`User` owns a one-to-one `StudentProfile`. The profile owns `Skill` rows. `Job` stores an externally sourced opportunity. `SavedJob` links a user and vacancy. `PreparationPlan` is unique per user and job and owns `StudySession` rows. `ScheduleEvent` records session history. `Application` tracks a user's vacancy status and notes. `Todo` stores personal tasks. Foreign keys and account-scoped queries enforce student-level separation.

## Phased roadmap

1. Foundation: application setup, accounts, profile, validation, CSRF and database migration support.
2. Data: source-backed vacancy feed, visible provenance, description parsing and skill matching.
3. Planning: job-linked curriculum, resources and exercises, exact study slots and adaptive missed-task handling.
4. Student workflow: dashboard, decisions, applications, to-dos and learning history.
5. DevOps: Docker image, health check, Kubernetes resources and Jenkins CI/CD.
6. Demonstration: execute and capture the actual test, local-container, cluster, webhook and Jenkins-run evidence.

## Verification status on 25 October 2026

- Five workflow tests passed, covering CSRF rejection, health/profile/to-do behavior, account ownership, role/location relevance, and the save-plan-miss-reschedule-completion flow.
- `flask db check` reported no ungenerated schema changes; both Alembic migrations upgraded successfully.
- Docker image `saivyshnavi06/asda:latest` built and was pushed successfully. Final digest: `sha256:cee02110987b8883695c96a22ded301a6a44baf2de181ae0dae629e82bba2d31`.
- Docker Desktop Kubernetes rolled out one ready replica. `/healthz` returned HTTP 200 through a local `kubectl port-forward`; the registration page returned HTTP 200. The pod also reached Remotive's public API and received live job records with individual HTTPS source links.
- A Git remote was not configured, so there was no source push, webhook delivery or Jenkins build to demonstrate. Configure the repository URL, Jenkins job/webhook and credentials before counting that final automated trigger as complete.
