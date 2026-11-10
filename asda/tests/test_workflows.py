import os
import unittest
from datetime import datetime

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

from asda.app import Application, Job, JobSearchFetch, PreparationPlan, SavedJob, Skill, StudySession, Todo, User, cached_job_search, create_app, db


class AsdaWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret-key-not-for-production",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "WTF_CSRF_ENABLED": False,
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        self.client.post("/register", data={"email": "student@example.test", "password": "a-long-test-password-123"})
        user = db.session.scalar(db.select(User).filter_by(email="student@example.test"))
        job = Job(
            external_id="fixture:realistic-source-id", title="Junior DevOps Engineer", company="Example employer",
            description="Role requires Docker and Kubernetes experience. Work with Git and CI/CD.",
            skills_json='["docker", "kubernetes", "git", "ci/cd"]',
            url="https://example.org/jobs/123", source="Test fixture", location="Hyderabad",
        )
        db.session.add(job)
        db.session.commit()
        self.job_id = job.id
        self.user_id = user.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_profile_job_to_plan_missed_reschedule_and_completion(self):
        response = self.client.post(f"/jobs/{self.job_id}/save", data={"horizon": "14"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        plan = db.session.scalar(db.select(PreparationPlan).filter_by(user_id=self.user_id, job_id=self.job_id))
        self.assertIsNotNone(plan)
        self.assertGreaterEqual(len(plan.sessions), 1)
        first = next(s for s in plan.sessions if s.status == "scheduled")
        self.assertTrue(first.objective and first.exercise and first.deliverable and first.resource_url)
        detail = self.client.get(f"/jobs/{self.job_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"Original job description", detail.data)
        chain = sorted((s for s in plan.sessions if s.status == "scheduled"), key=lambda s: s.start_at)
        self.assertTrue(all(s.dependency_id == chain[index - 1].id for index, s in enumerate(chain) if index))
        before = len(plan.sessions)
        self.client.post(f"/sessions/{first.id}/status", data={"status": "missed"})
        self.assertEqual(first.status, "scheduled")  # the missed attempt is recorded, and the same work gets a new slot
        self.assertTrue(any(event.event_type == "rescheduled" for event in first.history))
        self.assertGreaterEqual(len(plan.sessions), before)
        scheduled = [s for s in plan.sessions if s.status == "scheduled"]
        self.assertEqual(len({s.start_at for s in scheduled}), len(scheduled))
        self.client.post(f"/sessions/{first.id}/status", data={"status": "completed", "evidence": "Runnable project"})
        self.assertEqual(first.status, "completed")
        self.client.post(f"/plans/{plan.id}/refresh")
        self.assertEqual(first.status, "completed")
        self.assertEqual(len(plan.sessions), len({s.title for s in plan.sessions}))

    def test_student_records_are_scoped_to_owner(self):
        self.client.post(f"/jobs/{self.job_id}/save", data={"horizon": "14"})
        self.client.post("/logout")
        self.client.post("/register", data={"email": "other@example.test", "password": "another-long-test-password"})
        self.assertEqual(self.client.get("/plan").status_code, 200)
        session = db.session.scalar(db.select(StudySession).limit(1))
        response = self.client.post(f"/sessions/{session.id}/status", data={"status": "missed"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get("/progress").status_code, 200)

    def test_health_profile_validation_and_todo(self):
        self.assertEqual(self.client.get("/healthz").json["status"], "ok")
        response = self.client.post("/profile", data={"weekly_hours": "0", "session_minutes": "999"})
        self.assertEqual(response.status_code, 302)
        response = self.client.post("/todos", data={"title": "Prepare portfolio README", "due_date": "2026-11-01"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(db.session.scalar(db.select(Todo).filter_by(user_id=self.user_id)).title, "Prepare portfolio README")
        response = self.client.get("/applications")
        self.assertEqual(response.status_code, 200)

    def test_profile_can_be_saved_repeatedly_with_same_skill(self):
        profile_data = {
            "weekly_hours": "8", "daily_hours": "2", "session_minutes": "45",
            "timezone": "Asia/Kolkata", "study_start": "19:00", "study_end": "21:00",
            "study_days": ["0", "1", "2", "3", "4"], "skills": "Python | self-reported |",
            "target_roles": "Software Engineer, DevOps Engineer",
        }
        self.assertEqual(self.client.post("/profile", data=profile_data).status_code, 302)
        self.assertEqual(self.client.post("/profile", data=profile_data).status_code, 302)
        skills = db.session.scalars(db.select(Skill).filter_by(profile_id=db.session.get(User, self.user_id).profile.id)).all()
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].name, "python")

    def test_csrf_protection_rejects_post_without_token(self):
        secure_app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret-key-not-for-production",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
        })
        response = secure_app.test_client().post("/login", data={"email": "student@example.test", "password": "anything"})
        self.assertEqual(response.status_code, 400)

    def test_default_discovery_filters_roles_and_ranks_preferred_locations(self):
        now = datetime.utcnow()
        db.session.add_all([
            JobSearchFetch(query="software engineer", fetched_at=now),
            JobSearchFetch(query="devops engineer", fetched_at=now),
            Job(external_id="fixture:junior-hyderabad", title="Junior Software Engineer", company="Hyderabad Systems", location="Hyderabad, India", url="https://example.org/jobs/junior", source="Test", verified_at=now),
            Job(external_id="fixture:senior-remote", title="Senior Software Engineer", company="Global Remote", location="Worldwide", url="https://example.org/jobs/senior", source="Test", verified_at=now),
            Job(external_id="fixture:unrelated", title="Remote Office Assistant", company="Admin Co", location="Worldwide", url="https://example.org/jobs/admin", source="Test", verified_at=now),
        ])
        db.session.commit()
        profile = db.session.get(User, self.user_id).profile
        listings = cached_job_search(profile=profile)
        self.assertEqual({job.title for job in listings}, {"Junior Software Engineer", "Junior DevOps Engineer"})
        self.assertEqual(listings[0].title, "Junior Software Engineer")
        response = self.client.get("/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Remote Office Assistant", response.data)
        self.assertNotIn(b"Senior Software Engineer", response.data)
        self.assertIn(b"Preferred location listed", response.data)


if __name__ == "__main__":
    unittest.main()
