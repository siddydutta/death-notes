from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils.timezone import make_aware

from cron.models import Job
from web.models import Message
from cron.tasks import process_pending_jobs
from accounts.models import User


class ProcessPendingJobsTests(TestCase):
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
