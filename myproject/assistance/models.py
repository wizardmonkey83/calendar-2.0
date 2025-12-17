from django.conf import settings
from django.db import models
from django.utils.timezone import now as timezone_now


class VolunteerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='volunteer_profile')
    display_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    timezone = models.CharField(max_length=64, default='UTC')
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)

    def __str__(self):
        return self.display_name or str(self.user)


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    color = models.CharField(max_length=20, blank=True)
    default_duration_minutes = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_tasks')
    default_duration_minutes = models.IntegerField(null=True, blank=True)
    default_capacity = models.IntegerField(default=1)
    recurrence_rule = models.TextField(blank=True, help_text='Optional RRULE or JSON scheduling rule')
    timezone = models.CharField(max_length=64, default='UTC')
    is_public = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone_now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class SlotStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    FILLED = 'filled', 'Filled'
    CANCELLED = 'cancelled', 'Cancelled'


class Slot(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='slots')
    start_ts = models.DateTimeField()
    end_ts = models.DateTimeField()
    capacity = models.IntegerField(default=1)
    bookings_count = models.IntegerField(default=0)
    requires_confirmation = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=SlotStatus.choices, default=SlotStatus.OPEN)
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone_now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['start_ts']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.task.title}: {self.start_ts.isoformat()} - {self.end_ts.isoformat()}"


class BookingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class Booking(models.Model):
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, related_name='bookings')
    volunteer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='bookings')
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    notes = models.TextField(blank=True)
    contact_info = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone_now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('slot', 'volunteer')

    def __str__(self):
        return f"Booking {self.id} - {self.volunteer or 'anonymous'} -> {self.slot}"


class Availability(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='availabilities')
    # simple weekly availability
    weekday = models.IntegerField(choices=[(i, i) for i in range(7)])
    start_time = models.TimeField()
    end_time = models.TimeField()
    timezone = models.CharField(max_length=64, default='UTC')

    def __str__(self):
        return f"{self.user} - {self.weekday}: {self.start_time}-{self.end_time}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    booking = models.ForeignKey(Booking, null=True, blank=True, on_delete=models.SET_NULL)
    channel = models.CharField(max_length=20, choices=[('email', 'Email'), ('sms', 'SMS')])
    kind = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification {self.kind} -> {self.user}"


class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone_now)

    def __str__(self):
        return f"{self.created_at.isoformat()} - {self.action}"
