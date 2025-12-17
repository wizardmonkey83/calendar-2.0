from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
from .models import Slot, Booking, VolunteerProfile, Task, Category
from .forms import LoginForm, SignupForm, CreateSlotForm


def login_view(request):
    """Login page."""
    if request.user.is_authenticated:
        return redirect('calendar')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('calendar')
            else:
                form.add_error(None, 'Invalid username or password')
    else:
        form = LoginForm()
    
    return render(request, 'assistance/login.html', {'form': form})


def signup_view(request):
    """Signup page."""
    if request.user.is_authenticated:
        return redirect('calendar')
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            role = form.cleaned_data['role']
            
            # Check if user exists
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'Username already exists')
            elif User.objects.filter(email=email).exists():
                form.add_error('email', 'Email already exists')
            else:
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )
                # Create volunteer profile with role
                VolunteerProfile.objects.create(
                    user=user,
                    role=role,
                    display_name=username
                )
                # Log them in
                login(request, user)
                return redirect('calendar')
    else:
        form = SignupForm()
    
    return render(request, 'assistance/signup.html', {'form': form})


def logout_view(request):
    """Logout user."""
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def calendar_view(request):
    """
    Calendar page showing all slots.
    - Volunteers see slots they can book
    - Patients see all slots (to monitor)
    """
    # Get upcoming slots (next 30 days)
    now = timezone.now()
    slots = Slot.objects.filter(
        start_ts__gte=now,
        start_ts__lte=now + timedelta(days=30),
        status='open'
    ).select_related('task__category').prefetch_related('bookings')
    
    # Get user's bookings
    user_bookings = Booking.objects.filter(
        volunteer=request.user,
        status__in=['pending', 'confirmed']
    ).values_list('slot_id', flat=True)
    
    # Try to get user's role
    try:
        profile = request.user.volunteer_profile
        is_volunteer = profile.role == 'volunteer'
        is_patient = profile.role == 'patient'
    except VolunteerProfile.DoesNotExist:
        is_volunteer = True
        is_patient = False
    
    # Build slot data with booking info
    slot_data = []
    for slot in slots:
        available_spots = slot.capacity - slot.bookings_count
        is_booked = slot.id in user_bookings
        booked_by = [b.volunteer.username for b in slot.bookings.all() if b.volunteer]
        
        slot_data.append({
            'id': slot.id,
            'task': slot.task.title,
            'category': slot.task.category.name if slot.task.category else 'N/A',
            'start': slot.start_ts,
            'end': slot.end_ts,
            'location': slot.location,
            'capacity': slot.capacity,
            'available': available_spots,
            'booked': is_booked,
            'booked_by': booked_by,
            'is_full': available_spots == 0,
        })
    
    context = {
        'slots': slot_data,
        'is_volunteer': is_volunteer,
        'is_patient': is_patient,
    }
    
    return render(request, 'assistance/calendar.html', context)


@login_required(login_url='login')
def book_slot(request, slot_id):
    """Book a slot (for volunteers)."""
    slot = get_object_or_404(Slot, id=slot_id)
    
    # Check if slot is full
    if slot.bookings_count >= slot.capacity:
        return JsonResponse({'error': 'Slot is full'}, status=400)
    
    # Check if already booked
    existing = Booking.objects.filter(slot=slot, volunteer=request.user).exists()
    if existing:
        return JsonResponse({'error': 'Already booked'}, status=400)
    
    # Use transaction to prevent race conditions
    try:
        with transaction.atomic():
            # Re-check with lock
            slot = Slot.objects.select_for_update().get(id=slot_id)
            
            if slot.bookings_count >= slot.capacity:
                return JsonResponse({'error': 'Slot is full'}, status=400)
            
            # Create booking
            booking = Booking.objects.create(
                slot=slot,
                volunteer=request.user,
                status='confirmed'
            )
            
            # Update bookings count
            slot.bookings_count += 1
            slot.save(update_fields=['bookings_count'])
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    return redirect('calendar')


@login_required(login_url='login')
def cancel_booking(request, booking_id):
    """Cancel a booking."""
    booking = get_object_or_404(Booking, id=booking_id, volunteer=request.user)
    
    # Delete booking and decrement count
    slot = booking.slot
    booking.delete()
    slot.bookings_count = max(0, slot.bookings_count - 1)
    slot.save(update_fields=['bookings_count'])
    
    return redirect('calendar')


@login_required(login_url='login')
def create_slot(request):
    """Create a new slot (for patients)."""
    try:
        profile = request.user.volunteer_profile
        if profile.role != 'patient':
            return redirect('calendar')
    except VolunteerProfile.DoesNotExist:
        return redirect('calendar')
    
    if request.method == 'POST':
        form = CreateSlotForm(request.POST)
        if form.is_valid():
            start_ts = form.cleaned_data['start_ts']
            end_ts = form.cleaned_data['end_ts']
            if end_ts <= start_ts:
                form.add_error('end_ts', 'End time must be after start time')
            else:
                # Resolve category string to Category instance (or None)
                category_name = form.cleaned_data.get('category') or ''
                category_obj = None
                if category_name.strip():
                    cat_slug = slugify(category_name)
                    category_obj, _ = Category.objects.get_or_create(
                        slug=cat_slug,
                        defaults={'name': category_name, 'color': ''}
                    )

                # Create or get task
                task, _ = Task.objects.get_or_create(
                    title=form.cleaned_data['title'],
                    created_by=request.user,
                    defaults={
                        'description': form.cleaned_data.get('description', ''),
                        'category': category_obj,
                    }
                )

                # Create slot
                slot = Slot.objects.create(
                    task=task,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    capacity=form.cleaned_data['capacity'],
                    location=form.cleaned_data.get('location', ''),
                )

                return redirect('calendar')
    else:
        form = CreateSlotForm()
    
    return render(request, 'assistance/create_slot.html', {'form': form})


@login_required(login_url='login')
def profile_view(request):
    """User profile page."""
    try:
        profile = request.user.volunteer_profile
    except VolunteerProfile.DoesNotExist:
        profile = VolunteerProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        profile.display_name = request.POST.get('display_name', profile.display_name)
        profile.phone = request.POST.get('phone', profile.phone)
        profile.timezone = request.POST.get('timezone', profile.timezone)
        profile.save()
        
        # Update user email if provided
        if request.POST.get('email'):
            request.user.email = request.POST['email']
            request.user.save()
        
        return redirect('profile')
    
    context = {
        'profile': profile,
        'email': request.user.email,
        'username': request.user.username,
    }
    
    return render(request, 'assistance/profile.html', context)
