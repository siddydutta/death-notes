from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager to use email instead of username"""

    def create_user(self, email: str, password: str = None, **extra_fields):
        """Override the default create_user method to use email instead of username.

        Args:
            email (str): Email of the user.
            password (str, optional): Password for the user. Defaults to None.

        Raises:
            ValueError: If the email field is not passed.

        Returns:
            _type_: The created user object.
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str = None, **extra_fields):
        """Override the default create_user method to use email instead of username.

        Args:
            email (str): Email of the superuser.
            password (str, optional): Password for the superuser. Defaults to None.

        Returns:
            _type_: The created superuser object.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model that uses email instead of username for authentication.

    Attributes:
        email (EmailField): Unique email address for the user.
        first_name (CharField): Optional first name of the user.
        last_name (CharField): Optional last name of the user.
        interval (PositiveSmallIntegerField): Interval in days after which the user is considered inactive.
        last_checkin (DateTimeField): Timestamp of the last check-in by the user.
    """

    username = None  # remove the username field
    email = models.EmailField(unique=True)
    first_name = models.CharField(null=True, blank=True, max_length=30)
    last_name = models.CharField(null=True, blank=True, max_length=30)
    interval = models.PositiveSmallIntegerField(
        default=0,
        blank=True,
        help_text='Interval after which user is considered inactive (in days)',
    )
    last_checkin = models.DateTimeField(
        auto_now_add=True,
        help_text='Last timestamp user checked in at',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()  # custom user manager

    def __str__(self) -> str:
        """String representation of the user object."""
        return self.email
