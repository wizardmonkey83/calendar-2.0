from django.contrib import admin
from . import models


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'color')


@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'created_by', 'is_public', 'active')
    list_filter = ('is_public', 'active', 'category')


@admin.register(models.Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'start_ts', 'end_ts', 'capacity', 'bookings_count', 'status')
    list_filter = ('status', 'task')


@admin.register(models.Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'slot', 'volunteer', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(models.VolunteerProfile)
class VolunteerProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'display_name', 'phone')


@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'kind', 'channel', 'sent_at', 'delivered')


@admin.register(models.ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'user', 'created_at')
