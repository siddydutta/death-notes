import logging

from django.utils import timezone

from cron.models import Job
from web.models import Message


logger = logging.getLogger('django_q')


def process_pending_jobs():
    """Send messages for all non-complete pending jobs."""
    # fetch jobs and join relevant table data in chunks for performance
    pending_jobs = (
        Job.objects.select_related('message', 'message__user')
        .filter(
            message__status=Message.Status.SCHEDULED,
            scheduled_at__lte=timezone.now(),
            is_completed=False,
        )
        .iterator(chunk_size=10)
    )
    count = 0
    for job in pending_jobs:
        try:
            logger.debug(f'Processing job #{job.id}')
            job.is_completed = job.message.send()
            # save relevant fields triggering signals
            job.save(update_fields=['is_completed', 'updated_at'])
            logger.debug(f'Processed job #{job.id}')
            count += 1
        except Exception:
            logger.exception(f'Failed to process job {job.id}')
    logger.info(f'Processed {count} jobs')
