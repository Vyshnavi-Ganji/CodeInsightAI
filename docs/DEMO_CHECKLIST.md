# ASDA demonstration checklist

## Application workflow

- [ ] Register a new student account and sign in.
- [ ] Enter a degree, graduation year, target roles, location, skill evidence and weekly timetable.
- [ ] Show that the profile persists after signing out and back in.
- [ ] Search live listings and open an individually sourced vacancy with its source, original link, retrieval date and missing fields clearly indicated.
- [ ] Save a vacancy and show the automatically created plan, extracted/missing skills, objectives, resource links, practical exercises, deliverables, durations and exact dates/times.
- [ ] Mark one session completed with evidence and confirm it remains completed after plan refresh.
- [ ] Miss another session and show its new slot plus the event in Progress.
- [ ] Change skills/availability and recalculate; verify completed work remains and deferred work remains visible.
- [ ] Review a Decision Lab recommendation, update an application stage, add and complete a personal to-do.
- [ ] Sign in as a second student and verify the first student's plan and sessions are inaccessible.

## DevOps workflow

- [x] Run the automated workflow suite: all five tests passed.
- [x] Build `saivyshnavi06/asda:latest`, run the container, and verify its startup migrations and `/healthz` response.
- [x] Deploy to Docker Desktop Kubernetes; the ready pod returned health HTTP 200 and the registration page returned HTTP 200 via port-forward.
- [x] Confirm the deployed pod can retrieve current Remotive listings with original HTTPS URLs.
- [ ] Push source, Dockerfile, Jenkinsfile and Kubernetes manifests to the configured SCM repository.
- [ ] Show the SCM webhook delivery and automatic Jenkins trigger for a code push. The Git remote is not configured yet.
- [ ] Show Jenkins tests, image build, Docker Hub image tag publication, Kubernetes rollout and health verification. Docker Hub publishing and Kubernetes rollout were verified manually; Jenkins remains to be connected to SCM.
- [x] Open the deployed registration page through the local port-forward and confirm health.

Record date/time, commit SHA, image tag, Jenkins build number, cluster context and the commands/output for each completed check. Do not mark infrastructure checks complete based only on the presence of configuration files.
