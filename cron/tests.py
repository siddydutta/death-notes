from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.utils.timezone import make_aware

from accounts.models import User
from cron.models import Job
from cron.tasks import process_pending_jobs
from web.models import ActivityLog, Message


class TaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@test.com', password='foobar')
        self.scheduled_at = make_aware(
            datetime.strptime('2025-02-10 10:00:00', '%Y-%m-%d %H:%M:%S')
        )

    @patch('cron.tasks.logger')
    def test_process_pending_jobs(self, mock_logger):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            scheduled_at=self.scheduled_at,
        )
        job = Job.objects.get(message=message)

        with patch('web.models.Message.send') as mock_send:
            mock_send.return_value = True
            process_pending_jobs()
            job.refresh_from_db()
            self.assertTrue(job.is_completed)
            mock_logger.info.assert_called_with('Processed 1 jobs')

    @patch('cron.tasks.logger')
    def test_process_pending_jobs_failure(self, mock_logger):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            scheduled_at=self.scheduled_at,
        )
        job = Job.objects.get(message=message)

        with patch('web.models.Message.send') as mock_send:
            mock_send.side_effect = Exception('Sending failed')
            process_pending_jobs()
            job.refresh_from_db()
            self.assertFalse(job.is_completed)
            mock_logger.exception.assert_called_with(f'Failed to process job {job.id}')


class SignalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@test.com', password='foobar')
        self.scheduled_at = make_aware(
            datetime.strptime('2025-02-10 10:00:00', '%Y-%m-%d %H:%M:%S')
        )

    def test_update_jobs_on_checkin(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=30,
        )
        initial_job = Job.objects.get(message=message)
        ActivityLog.objects.create(
            user=self.user,
            type=ActivityLog.Type.CHECKED_IN,
        )
        updated_job = Job.objects.get(pk=initial_job.pk)
        self.assertNotEqual(initial_job.scheduled_at, updated_job.scheduled_at)
        expected_schedule = timezone.now() + timedelta(days=30)
        self.assertAlmostEqual(
            updated_job.scheduled_at.timestamp(), expected_schedule.timestamp(), delta=5
        )

    def test_update_jobs_on_checkin_ignores_time_capsule(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            scheduled_at=self.scheduled_at,
        )
        initial_job = Job.objects.get(message=message)
        ActivityLog.objects.create(
            user=self.user,
            type=ActivityLog.Type.CHECKED_IN,
        )
        updated_job = Job.objects.get(pk=initial_job.pk)
        self.assertEqual(initial_job.scheduled_at, updated_job.scheduled_at)

    def test_non_checkin_activity_doesnt_update_jobs(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=30,
        )
        initial_job = Job.objects.get(message=message)
        ActivityLog.objects.create(
            user=self.user,
            type=ActivityLog.Type.MESSAGE_CREATED,
        )
        updated_job = Job.objects.get(pk=initial_job.pk)
        self.assertEqual(initial_job.scheduled_at, updated_job.scheduled_at)

    def test_post_save_message_time_capsule(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            scheduled_at=self.scheduled_at,
        )
        job = Job.objects.get(message=message)
        self.assertEqual(job.scheduled_at, self.scheduled_at)
        new_scheduled_at = self.scheduled_at + timedelta(days=1)
        message.scheduled_at = new_scheduled_at
        message.save()
        job.refresh_from_db()
        self.assertEqual(job.scheduled_at, new_scheduled_at)

    def test_post_save_message_final_word(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=30,
        )
        job = Job.objects.get(message=message)
        expected_schedule = timezone.now() + timedelta(days=30)
        self.assertAlmostEqual(
            job.scheduled_at.timestamp(), expected_schedule.timestamp(), delta=5
        )
        message.delay = 60
        message.save()
        job.refresh_from_db()
        expected_schedule = timezone.now() + timedelta(days=60)
        self.assertAlmostEqual(
            job.scheduled_at.timestamp(), expected_schedule.timestamp(), delta=5
        )

    def test_job_completion_creates_activity_log(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            scheduled_at=self.scheduled_at,
        )
        job = Job.objects.get(message=message)
        creation_log = ActivityLog.objects.filter(
            user=self.user, type=ActivityLog.Type.MESSAGE_CREATED
        ).first()
        self.assertIsNotNone(creation_log)
        job.is_completed = True
        job.save()
        delivery_log = ActivityLog.objects.filter(
            user=self.user, type=ActivityLog.Type.MESSAGE_DELIVERED
        ).first()
        self.assertIsNotNone(delivery_log)

    def test_job_deletion_creates_activity_log(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            scheduled_at=self.scheduled_at,
        )
        job = Job.objects.get(message=message)
        job.delete()
        deletion_log = ActivityLog.objects.filter(
            user=self.user, type=ActivityLog.Type.MESSAGE_DELETED
        ).first()
        self.assertIsNotNone(deletion_log)

    def test_job_incomplete_doesnt_create_activity_log(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=30,
        )
        job = Job.objects.get(message=message)
        job.is_completed = True
        job.save()
        job.refresh_from_db()
        job.scheduled_at = self.scheduled_at + timedelta(days=1)
        job.save()
        self.assertEqual(ActivityLog.objects.count(), 2)
