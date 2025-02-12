from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.test import RequestFactory, TestCase

from web.models import ActivityLog, Message
from web.signals import add_login_activitylog

User = get_user_model()


class SignalTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email='user@test.com', password='foobar')

    def test_add_login_activitylog(self):
        request = self.factory.get('/some/path/')
        add_login_activitylog(sender=None, request=request, user=self.user)

        self.assertTrue(
            ActivityLog.objects.filter(
                user=self.user, type=ActivityLog.Type.CHECKED_IN
            ).exists()
        )

    def test_add_login_activitylog_admin_path(self):
        request = self.factory.get('/admin/some/path/')
        add_login_activitylog(sender=None, request=request, user=self.user)

        self.assertFalse(
            ActivityLog.objects.filter(
                user=self.user, type=ActivityLog.Type.CHECKED_IN
            ).exists()
        )

    def test_pre_save_message(self):
        message = Message.objects.create(
            user=self.user,
            type=Message.Type.FINAL_WORD,
            recipients='user1@test.com',
            subject='Test Subject',
            text='Test text',
            delay=10,
        )
        message.delay = 20

        pre_save.send(sender=Message, instance=message)

        self.assertTrue(hasattr(message, '__previous_delay'))
        self.assertEqual(getattr(message, '__previous_delay'), 10)
