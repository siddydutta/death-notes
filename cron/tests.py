from datetime import datetime, timedelta
from typing import Callable
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.utils.timezone import now, timedelta

from accounts.models import User
from cron.models import Job
from cron.tasks import process_pending_jobs
from web.models import ActivityLog, Message


class TaskTests(TestCase):
    """Test the tasks in the cron app."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email='user@test.com', password='foobar')
        self.scheduled_at = now() + timedelta(days=10)

    @patch('cron.tasks.logger')
    def test_process_pending_jobs(self, mock_logger: Callable[[str], None]):
        """Test processing of pending jobs.

        Args:
            mock_logger (Callable[[str], None]): Mocked logger instance.
        """
        # Given
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            scheduled_at=self.scheduled_at,
        )
        job = Job.objects.get(message=message)
        job.scheduled_at = timezone.now() - timedelta(days=2)
        job.save()
        with patch('web.models.Message.send') as mock_send:
            mock_send.return_value = True
            # When
            process_pending_jobs()
            job.refresh_from_db()
            # Then
            self.assertTrue(job.is_completed)
            mock_logger.info.assert_called_with('Processed 1 jobs')

    @patch('cron.tasks.logger')
    def test_process_pending_jobs_failure(self, mock_logger: Callable[[str], None]):
        """Test handling of job processing failure.

        Args:
            mock_logger (Callable[[str], None]): Mocked logger instance.
        """
        # Given
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            scheduled_at=self.scheduled_at,
        )
        job = Job.objects.get(message=message)
        job.scheduled_at = timezone.now() - timedelta(days=2)
        job.save()
        with patch('web.models.Message.send') as mock_send:
            mock_send.side_effect = Exception('Sending failed')
            # When
            process_pending_jobs()
            job.refresh_from_db()
            # Then
            self.assertFalse(job.is_completed)
            mock_logger.exception.assert_called_with(f'Failed to process job {job.id}')


class SignalTests(TestCase):
    """Test the signals in the cron app."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email='user@test.com', password='foobar')
        self.scheduled_at = now() + timedelta(days=10)

    def test_update_jobs_on_checkin(self):
        """Test updating jobs on user check-in."""
        # Given
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
        # When
        updated_job = Job.objects.get(pk=initial_job.pk)
        # Then
        self.assertNotEqual(initial_job.scheduled_at, updated_job.scheduled_at)
        expected_schedule = timezone.now() + timedelta(days=30)
        self.assertAlmostEqual(
            updated_job.scheduled_at.timestamp(), expected_schedule.timestamp(), delta=5
        )

    def test_update_jobs_on_checkin_ignores_time_capsule(self):
        """Test that check-in does not update time capsule jobs."""
        # Given
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
        # When
        updated_job = Job.objects.get(pk=initial_job.pk)
        # Then
        self.assertEqual(initial_job.scheduled_at, updated_job.scheduled_at)

    def test_non_checkin_activity_doesnt_update_jobs(self):
        """Test that non-check-in activities do not update jobs."""
        # Given
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
        # When
        updated_job = Job.objects.get(pk=initial_job.pk)
        # Then
        self.assertEqual(initial_job.scheduled_at, updated_job.scheduled_at)

    def test_post_save_user_final_word(self):
        """Test post-save signal for user final word messages."""
        # Given
        self.user.interval = 10
        self.user.save()
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=30,
        )
        job = Job.objects.get(message=message)
        now = timezone.now()
        expected_schedule = now + timedelta(days=40)
        self.assertAlmostEqual(
            job.scheduled_at.timestamp(), expected_schedule.timestamp(), delta=5
        )
        # When
        self.user.interval = 20
        self.user.save()
        job.refresh_from_db()
        expected_schedule = now + timedelta(days=50)
        # Then
        self.assertAlmostEqual(
            job.scheduled_at.timestamp(), expected_schedule.timestamp(), delta=5
        )

    def test_post_save_message_time_capsule(self):
        """Test post-save signal for time capsule messages."""
        # Given
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
        # When
        message.scheduled_at = new_scheduled_at
        message.save()
        job.refresh_from_db()
        # Then
        self.assertEqual(job.scheduled_at, new_scheduled_at)

    def test_post_save_message_final_word(self):
        """Test post-save signal for final word messages."""
        # Given
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
        # When
        message.delay = 60
        message.save()
        job.refresh_from_db()
        expected_schedule = timezone.now() + timedelta(days=60)
        # Then
        self.assertAlmostEqual(
            job.scheduled_at.timestamp(), expected_schedule.timestamp(), delta=5
        )

    def test_job_completion_creates_activity_log(self):
        """Test that job completion creates an activity log."""
        # Given
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
        # When
        job.is_completed = True
        job.save()
        # Then
        delivery_log = ActivityLog.objects.filter(
            user=self.user, type=ActivityLog.Type.MESSAGE_DELIVERED
        ).first()
        self.assertIsNotNone(delivery_log)

    def test_job_deletion_creates_activity_log(self):
        """Test that job deletion creates an activity log."""
        # Given
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.TIME_CAPSULE,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            scheduled_at=self.scheduled_at,
        )
        job = Job.objects.get(message=message)
        # When
        job.delete()
        # Then
        deletion_log = ActivityLog.objects.filter(
            user=self.user, type=ActivityLog.Type.MESSAGE_DELETED
        ).first()
        self.assertIsNotNone(deletion_log)

    def test_job_incomplete_doesnt_create_activity_log(self):
        """Test that incomplete jobs do not create an activity log."""
        # Given
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
        # When
        job.scheduled_at = self.scheduled_at + timedelta(days=1)
        job.save()
        # Then
        self.assertEqual(ActivityLog.objects.count(), 2)
