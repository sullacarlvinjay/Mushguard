from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail
from .forms import MushroomImageForm, UnknownMushroomForm, UnknownMushroomAdminForm, UserRegistrationForm
from .models import UnknownMushroom, UserProfile
from .model_utils import analyze_mushroom
import logging
from PIL import Image, UnidentifiedImageError
import io
from typing import Optional, Dict, Any
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

# Set up logging
logger = logging.getLogger(__name__)

def landing(request):
    """Render the simple landing page with greeting and analyze button."""
    APPROVED_UNKNOWN_COLOR = '#ffc107'
    approved_filter = (~Q(status='unknown')) | Q(status='unknown', pin_color=APPROVED_UNKNOWN_COLOR)
    approved_reports = UnknownMushroom.objects.filter(approved_filter)
    counts = {
        'total': approved_reports.count(),
        'mapped': approved_reports.count(),
        'edible': approved_reports.filter(status='edible').count(),
        'poisonous': approved_reports.filter(status='poisonous').count(),
        'unknown': approved_reports.filter(status='unknown').count(),
        'species': approved_reports.values_list('name', flat=True).distinct().count(),
    }
    # Group confirmed mushrooms by name (simple grouping)
    from collections import defaultdict
    grouped_mushrooms = defaultdict(list)
    for m in approved_reports.order_by('-created_at'):
        grouped_mushrooms[m.name.lower().strip()].append(m)
    grouped_mushrooms = dict(grouped_mushrooms)

    return render(request, 'core/new_homepage.html', { 
        'reports': approved_reports, 
        'counts': counts,
        'grouped_mushrooms': grouped_mushrooms
    })


def robots_txt(request):
    """Serve a simple robots.txt that allows all crawling and points to sitemap."""
    sitemap_url = request.build_absolute_uri('/sitemap.xml')
    content = f"""User-agent: *
Disallow:

Sitemap: {sitemap_url}
"""
    return HttpResponse(content, content_type='text/plain')


def sitemap_xml(request):
    """Serve a basic XML sitemap listing key public URLs."""
    urls = [
        request.build_absolute_uri('/'),
        request.build_absolute_uri('/analyze/'),
        request.build_absolute_uri('/advertisements/'),
    ]
    xml_items = "".join(f"<url><loc>{loc}</loc></url>" for loc in urls)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_items}
</urlset>
"""
    return HttpResponse(xml, content_type='application/xml')


def service_worker(request):
    """Serve the service worker JavaScript at the root path /sw.js."""
    sw_path = settings.BASE_DIR / 'static' / 'sw.js'
    try:
        with open(sw_path, 'rb') as f:
            content = f.read()
    except FileNotFoundError:
        return HttpResponse('// Service worker not found', content_type='application/javascript', status=404)
    return HttpResponse(content, content_type='application/javascript')


def advertisements(request):
    """Simple page showing logo, poster, and advertisement video."""
    return render(request, 'core/advertisements.html')


class VerifiedLoginView(LoginView):
    """Custom login view that only allows login if email is verified.

    If the user's email is not verified, log them back out, resend the
    verification email, and show an error message.
    """
    template_name = 'core/user_login.html'

    def form_valid(self, form):
        # First let Django authenticate and log the user in
        response = super().form_valid(form)
        user = self.request.user
        profile = getattr(user, 'profile', None)

        # If this is an admin/staff account, bypass email verification
        # and send them directly to the admin dashboard.
        if user.is_staff or user.is_superuser:
            return redirect('/admin-panel/')

        # If there is a profile and email is not verified, block login
        if profile and not profile.email_verified:
            # Resend verification email
            verify_url = self.request.build_absolute_uri(
                reverse('core:verify_email', args=[profile.verification_token])
            )
            subject = 'Verify your MushGuard account'
            message = f'Please verify your email by clicking this link: {verify_url}'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=True)
            except Exception:
                logger.exception('Error re-sending verification email on login')

            # Log user back out and show message
            logout(self.request)
            messages.error(
                self.request,
                'Your email is not verified yet. We have sent a new verification link to your email.'
            )
            return redirect('core:login')

        # No profile or already verified -> allow normal login
        return response

# about and map merged into new_homepage.html sections

def validate_image(image_file):
    """Validate and convert uploaded image to PIL Image."""
    try:
        # Read image data
        image_data = image_file.read()
        # Convert to PIL Image
        image = Image.open(io.BytesIO(image_data))
        # Verify it's a valid image
        image.load()
        return image
    except Exception as e:
        logger.error(f"Error validating image: {str(e)}")
        raise ValidationError(f"Invalid image file: {str(e)}")

@login_required
def home(request):
    """Render the home page with the mushroom classifier interface."""
    result = None
    if request.method == 'POST':
        form = MushroomImageForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Get and validate the image
                image_file = request.FILES['image']
                pil_image = validate_image(image_file)
                
                try:
                    # Analyze the mushroom
                    result = analyze_mushroom(pil_image)
                finally:
                    pil_image.close()
                
            except Exception as e:
                logger.error(f"Error processing image: {str(e)}")
                result = {'error': str(e)}
    else:
        form = MushroomImageForm()
    
    return render(request, 'core/home.html', {
        'form': form,
        'result': result,
        'unknown_form': UnknownMushroomForm()
    })

@login_required
def report_unknown(request):
    """Allow users to submit a report for mushrooms not in dataset."""
    if request.method == 'POST':
        form = UnknownMushroomForm(request.POST, request.FILES)
        if form.is_valid():
            form.instance.is_pending = True
            form.instance.user = request.user
            form.save()
            # Return JSON response for modal popup
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Your mushroom report has been submitted successfully!'})
            return render(request, 'core/report_unknown.html', { 
                'form': UnknownMushroomForm(),
                'success': True,
                'message': 'Your mushroom report has been submitted successfully!'
            })
        # show errors on the same form page when invalid
        return render(request, 'core/report_unknown.html', { 'form': form })
    else:
        form = UnknownMushroomForm()
    return render(request, 'core/report_unknown.html', { 'form': form })

def mushroom_detail(request, mushroom_name):
    """Show detailed view of a specific mushroom species with all locations."""
    # Get all mushrooms with this name (case-insensitive)
    mushrooms = UnknownMushroom.objects.filter(name__iexact=mushroom_name).order_by('-created_at')
    
    if not mushrooms.exists():
        # Try to find by ID if name doesn't work
        try:
            mushroom_id = int(mushroom_name)
            single_mushroom = get_object_or_404(UnknownMushroom, id=mushroom_id)
            mushrooms = UnknownMushroom.objects.filter(name__iexact=single_mushroom.name)
        except (ValueError, UnknownMushroom.DoesNotExist):
            return render(request, 'core/mushroom_detail.html', {'error': 'Mushroom not found'})
    
    # Prefer approved entries for the primary display, fall back to latest overall
    approved_for_display = mushrooms.exclude(status='unknown')
    primary_mushroom = approved_for_display.first() if approved_for_display.exists() else mushrooms.first()
    locations_count = mushrooms.count()

    return render(request, 'core/mushroom_detail.html', {
        'mushrooms': mushrooms,
        'primary_mushroom': primary_mushroom,
        'locations_count': locations_count,
        'mushroom_name': primary_mushroom.name
    })


def admin_login_view(request):
    """Custom login view that handles authentication and redirects to admin panel."""
    # If already logged in and staff, go directly to admin panel
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('/admin-panel/')
    
    # Handle login form submission
    if request.method == 'POST':
        username = request.POST.get('admin_username')
        password = request.POST.get('admin_password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            # Redirect to admin panel after successful login
            return redirect('/admin-panel/')
        else:
            # Show error on login page
            return render(request, 'core/login.html', {
                'form': {'errors': True},
                'error_message': 'Invalid credentials or you do not have admin access.'
            })
    
    # Show login page
    return render(request, 'core/login.html')


def signup_view(request):
    """Handle user registration and send email verification link."""
    if request.user.is_authenticated:
        return redirect('core:landing')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile = UserProfile.objects.create(user=user)

            verify_url = request.build_absolute_uri(
                reverse('core:verify_email', args=[profile.verification_token])
            )

            subject = 'Verify your MushGuard account'
            message = f'Welcome to MushGuard! Please verify your email by clicking this link: {verify_url}'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [user.email]
            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=True)
            except Exception:
                logger.exception('Error sending verification email')

            # Show a page telling the user to check their email for the verification link
            return render(request, 'core/signup_pending.html', {
                'email': user.email,
            })
    else:
        form = UserRegistrationForm()

    return render(request, 'core/signup.html', {'form': form})


def verify_email(request, token):
    """Verify user's email using the unique token."""
    profile = UserProfile.objects.filter(verification_token=token).first()
    if not profile:
        messages.error(request, 'Invalid or expired verification link.')
        return redirect('core:login')

    just_verified = False
    if not profile.email_verified:
        profile.email_verified = True
        profile.save(update_fields=['email_verified'])
        just_verified = True

    # Show a confirmation page; from there user can go to login
    return render(request, 'core/verify_success.html', {
        'just_verified': just_verified,
        'email': profile.user.email,
    })


@login_required
def account_view(request):
    """Show user account details and history of their mushroom reports."""
    reports = UnknownMushroom.objects.filter(user=request.user).order_by('-created_at')
    profile = getattr(request.user, 'profile', None)
    context = {
        'reports': reports,
        'profile': profile,
    }
    return render(request, 'core/account.html', context)


def admin_manage_reports(request):
    """Custom admin page to manage reported mushrooms.
    Shows Pending (status='unknown') and Confirmed (others). Supports approve action.
    """
    # Check if user is authenticated and is staff
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/login/')

    STATUS_COLOR_MAP = {
        'mapped': '#0d6efd',     # bootstrap blue
        'edible': '#28a745',     # legend green
        'poisonous': '#dc3545',  # bootstrap red
        'unknown': '#ffc107',    # bootstrap yellow
    }

    # Approve action: set status and auto pin color
    if request.method == 'POST' and request.POST.get('action') == 'approve':
        approve_id = request.POST.get('id')
        new_status = request.POST.get('status')
        item = UnknownMushroom.objects.filter(id=approve_id).first()
        if item and new_status in STATUS_COLOR_MAP and new_status != 'unknown':
            item.status = new_status
            item.pin_color = STATUS_COLOR_MAP[new_status]
            item.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})

    # Reject action: delete a pending item
    if request.method == 'POST' and request.POST.get('action') == 'reject':
        reject_id = request.POST.get('id')
        item = UnknownMushroom.objects.filter(id=reject_id, status='unknown').first()
        if item:
            item.delete()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})

    # Remove action: delete a confirmed item
    if request.method == 'POST' and request.POST.get('action') == 'remove':
        remove_id = request.POST.get('id')
        item = UnknownMushroom.objects.filter(id=remove_id).exclude(status='unknown').first()
        if item:
            item.delete()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})

    # Regular create/update via form
    if request.method == 'POST' and request.POST.get('action') != 'approve':
        report_id = request.POST.get('id')
        instance = UnknownMushroom.objects.filter(id=report_id).first() if report_id else None
        form = UnknownMushroomAdminForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            status = getattr(obj, 'status', None)
            if status in STATUS_COLOR_MAP:
                obj.pin_color = STATUS_COLOR_MAP[status]
            obj.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})

    # GET or on invalid POST -> render dashboard
    form = UnknownMushroomAdminForm()
    approved_unknown_q = Q(status='unknown', pin_color=STATUS_COLOR_MAP['unknown'])
    confirmed_filter = (~Q(status='unknown')) | approved_unknown_q
    pending = UnknownMushroom.objects.filter(status='unknown').exclude(pin_color=STATUS_COLOR_MAP['unknown']).order_by('-created_at')
    confirmed = UnknownMushroom.objects.filter(confirmed_filter).order_by('-created_at')
    return render(request, 'core/admin_dashboard.html', {
        'form': form,
        'pending_reports': pending,
        'confirmed_reports': confirmed,
        'STATUS_COLOR_MAP': STATUS_COLOR_MAP,
    })

@csrf_exempt
def predict_mushroom(request):
    """Handle image upload and return prediction results."""
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            # Get and validate the image
            image_file = request.FILES['image']
            pil_image = validate_image(image_file)
            
            try:
                # Analyze the mushroom
                result = analyze_mushroom(pil_image)
                
                return JsonResponse({
                    'success': True,
                    'result': result
                })
                
            finally:
                pil_image.close()
            
        except Exception as e:
            logger.error(f"Error in prediction: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'No image provided'
    })

@csrf_exempt
def analyze_mushroom_view(request):
    """Handle image upload and analysis."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
    
    try:
        # Get the image from the request
        image_file = request.FILES.get('image')
        if not image_file:
            return JsonResponse({'error': 'No image provided'}, status=400)
        
        # Read and process the image
        image_data = image_file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Analyze the mushroom
        result = analyze_mushroom(image)
        
        if 'error' in result:
            return JsonResponse({'error': result['error']}, status=500)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in analyze_mushroom: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
