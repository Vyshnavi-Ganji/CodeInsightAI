# ASDA career preparation

ASDA (Adaptive Scenario-Based Decision Support System) helps students compare real opportunities with their current skills, create a dated preparation plan, record completed and missed work, and track applications. This repository implements the Flask case-study application and its Docker, Kubernetes and Jenkins delivery assets.

The application is deterministic for its core workflow and needs no paid AI service. It does not invent vacancies: current individual job records are fetched from Remotive's public remote-jobs feed, with original vacancy URLs and retrieval timestamps. Naukri and Unstop are offered as explicitly labeled board search links, not as retrieved listings. Third-party requirements and eligibility should be checked on the original listing.

## Quick start on Windows with Docker Desktop

1. Copy `.asda.env.example` to `.asda.env` (this avoids overwriting any other project's `.env`).
2. Generate a unique key and replace `SECRET_KEY` in `.asda.env`:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

3. Build and start ASDA:

   ```powershell
   docker compose --env-file .asda.env up --build -d
   ```

4. Open [http://localhost:5000](http://localhost:5000), register, add skills and study availability, and open **Opportunities**. If the live feed is unavailable, ASDA explains that and keeps the labeled board searches available.

The Compose deployment stores SQLite data in a named Docker volume. For production, use PostgreSQL, HTTPS, a strong `SECRET_KEY`, backups and `SESSION_COOKIE_SECURE=true`.

## Local Python development

Python 3.11 or newer is recommended. Create and activate a virtual environment, install the dependencies, set a secret, then initialize and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = (python -c "import secrets; print(secrets.token_urlsafe(48))")
$env:DATABASE_URL = "sqlite:///asda.db"
flask --app asda.app db upgrade
flask --app asda.app run
```

The ASDA app is served by `wsgi.py`; Gunicorn is used in the container. Container startup applies the checked-in migration history in `migrations/` before serving requests.

## Core workflow

1. Register an account. Passwords are hashed, and every profile, saved job, plan, application, to-do and session query is scoped to that account.
2. In **Profile & timetable**, enter education, roles, locations, skills and evidence levels (`self-reported`, `partial`, `assessed`, `demonstrated`), time zone, study days, hours, preferred daily window, unavailable dates and fixed commitments. Fixed commitments can be written as `Mon 09:00-17:00; Wed 09:00-12:00`. Empty settings receive a disclosed reasonable default.
3. Search **Opportunities**. Individual records show the source, retrieval date, job details as supplied, source URL and any published compensation/deadline; missing values are marked unavailable. Searchboard links are not represented as specific openings.
4. Open a role to inspect extracted skills and the match. Saving it creates a persistent plan. If no employer deadline is published, the student-selected 14-day horizon is a preparation target, not a claimed deadline.
5. Work through each session's objective, direct learning resource, practical exercise, deliverable, duration, date and time. Mark work completed with evidence or missed to invoke schedule recalculation. Completed work remains intact, deferred tasks remain visible and every move is recorded in **Progress**.
6. Review **Decision Lab**, update application stages and keep personal to-dos.

ASDA uses transparent keyword extraction. A missing/partial listing produces starter topics labeled as estimates. Where a verified direct learning page is not configured, the plan labels the resource as an unverified resource search. It makes no interview or employment guarantees.

## Pages

- Dashboard: today's/upcoming sessions, saved opportunities, completion and next actions.
- Profile & timetable: persistent student data, evidence, time zone, constraints and availability.
- Opportunities and job details: current sourced vacancies, original vacancy text and skill match.
- Preparation plan: generated learning sessions, completion and missed-work rescheduling.
- Decision Lab: explainable next-step recommendations and uncertainty.
- Applications: Saved, Preparing, Applied, Assessment, Interview, Offer and Rejected.
- To-do list: persistent personal tasks with due dates.
- Progress: session states and a history of missed, moved and deferred work.

## Core data model

| Entity | Purpose and key relationships |
| --- | --- |
| `User` | Login identity; owns one profile and private student records. |
| `StudentProfile` | Education, target roles/locations, time zone, availability, study window and preferences; one-to-one with `User`. |
| `Skill` | Profile skill, proficiency/evidence level and unique profile/name constraint. |
| `Job` | Sourced vacancy, exact source URL, source, text, extracted skills, publication/deadline/salary fields and verification time. |
| `SavedJob` | User-to-job selection and the user's preparation target date. |
| `PreparationPlan` | Unique user/job plan and target date; owns ordered sessions. |
| `StudySession` | Objective, resource, exercise, deliverable, duration, scheduled times, status, evidence and dependency reference. |
| `ScheduleEvent` | Append-only history for completion, missed work, moves and deferrals. |
| `Application` | User/job application state and notes. |
| `Todo` | User-owned personal tasks and due dates. |

SQLite supports a local single-instance deployment; `DATABASE_URL` supports PostgreSQL for deployment. Schema changes use Flask-Migrate/Alembic. Session cookies are HTTP-only and SameSite=Lax; all state-changing forms require CSRF tokens. Production secrets are passed through environment variables or Jenkins credentials, never committed.

## Phased implementation roadmap

1. **Foundation and security:** Flask application factory, authentication, profile isolation, validation, CSRF and persistent schema/migrations.
2. **Career data:** live public feed adapter, source provenance, job search fallback links, description extraction and explainable profile matching.
3. **Preparation workflow:** per-vacancy curriculum, direct resources, dated availability-aware sessions, progress evidence and adaptive rescheduling/history.
4. **Decision support:** explainable apply/prepare/assess recommendations, applications, personal tasks and progress dashboard.
5. **Delivery automation:** container image, health checks, Kubernetes rollout and Jenkins build/test/push/deploy/verify pipeline.
6. **Operational validation:** run unit/workflow checks, validate manifests, verify live feed behavior, build/run the image and confirm the target cluster deployment and push-triggered Jenkins run.

## Tests

Install `requirements.txt` then run:

```powershell
python -m unittest discover -s asda/tests -v
```

The suite covers registration, health, profile validation, to-dos, ownership boundaries, generated plans, missed-session rescheduling, unique scheduling and preservation of completed work. Jenkins runs the same workflow test suite before publishing an image.

## Docker Hub publishing

The image name is `saivyshnavi06/asda`. Build and publish manually if needed:

```powershell
docker build -t saivyshnavi06/asda:latest .
docker login -u saivyshnavi06
docker push saivyshnavi06/asda:latest
```

Keep the Docker Hub access token out of source files. Jenkins uses a username/password credential with ID `dockerhub-asda` (use the Docker Hub access token as its password).

## Kubernetes deployment

Docker Desktop Kubernetes must be enabled and the cluster context available. A first manual deployment can use:

```powershell
kubectl create secret generic asda-secrets --from-literal=secret-key='<unique-long-secret>' --from-literal=database-url='sqlite:////data/asda.db'
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl rollout status deployment/asda
kubectl get pods,svc -l app=asda
```

The service uses NodePort 30190. If Docker Desktop does not route that port to Windows, run `kubectl port-forward service/asda 5002:80` and open [http://localhost:5002](http://localhost:5002). The SQLite PVC is suitable for the single-replica local case study. Use a managed PostgreSQL database for multi-replica or production use. `k8s/deployment.yaml` defaults to the supplied Docker Hub namespace and uses readiness/liveness probes and a restricted container security context.

## Jenkins CI/CD setup

1. Push this repository to a GitHub/Git SCM repository and configure a Pipeline job to use its `Jenkinsfile` (or use a Multibranch Pipeline).
2. Configure a GitHub webhook pointing to `https://<jenkins-public-url>/github-webhook/` and enable the GitHub webhook trigger in Jenkins. `triggers { githubPush() }` receives push notifications; Jenkins must be reachable by the SCM host.
3. Add credentials: `dockerhub-asda` (username and Docker Hub access token), `docker-desktop-kubeconfig` (secret file containing the deployment kubeconfig), `asda-secret-key` (a strong session key) and `asda-database-url` (deployment database URL).
4. The Jenkins agent needs Python/pip, Docker CLI access to a Docker daemon, `kubectl`, and network access to Docker Hub and the Kubernetes API. For Docker Desktop cluster access, Jenkins must run where the Docker Desktop kubeconfig is usable; a Jenkins container needs the host kubeconfig mounted and cluster endpoint reachable.
5. A push runs checks, builds an immutable build/commit tag and `latest`, pushes both, applies Kubernetes resources, updates the image, waits for rollout and probes `/healthz` from inside the cluster.

The pipeline and manifests are prepared here; they become an automatic live pipeline only after the repository, webhook, Jenkins credential IDs, agent access and Docker Desktop cluster connectivity are configured. This workspace had no Git remote configured at implementation time, so no source push or Jenkins-triggered rollout is claimed.

## Demonstration checklist

See [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md) and [`docs/DEMO_CHECKLIST.md`](docs/DEMO_CHECKLIST.md) for the case-study report structure and evidence checklist. Record actual deployment and pipeline run IDs after executing them; configuration files alone do not demonstrate a successful deployment.
