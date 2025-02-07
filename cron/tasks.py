import logging

from cron.models import Job
from django.utils import timezone


logger = logging.getLogger('django_q')


def process_pending_jobs():
    pending_jobs = Job.objects.filter(
        scheduled_at__lte=timezone.now(), is_completed=False
    ).iterator(chunk_size=10)
    count = 0
    for job in pending_jobs:
        try:
            # TODO Implement Job Processing Logic
            logger.debug(f'Processing job #{job.id}')
            job.is_completed = True
            job.save(update_fields=['is_completed'])
            logger.debug(f'Processed job #{job.id}')
            count += 1
        except Exception:
            logger.exception(f'Failed to process job {job.id}')
    logger.info(f'Processed {count} jobs')
