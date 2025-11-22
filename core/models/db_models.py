"""Models for the core app."""

from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

class MushroomImage(models.Model):
    """Model for storing mushroom images and their analysis results."""
    
    image = models.ImageField(
        _("mushroom image"),
        upload_to='mushroom_images/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        help_text=_("Upload a clear image of the mushroom (JPG, JPEG, or PNG)")
    )
    uploaded_at = models.DateTimeField(_("upload date"), auto_now_add=True)
    is_edible = models.BooleanField(_("is edible"), null=True)
    edibility_confidence = models.FloatField(_("edibility confidence"), null=True)
    species = models.CharField(_("species"), max_length=100, blank=True)
    species_confidence = models.FloatField(_("species confidence"), null=True)
    lifespan = models.TextField(_("lifespan"), blank=True)
    preservation = models.TextField(_("preservation"), blank=True)
    
    def __str__(self):
        return f"Mushroom Image {self.id} - {self.uploaded_at}"
    
    class Meta:
        verbose_name = _("mushroom image")
        verbose_name_plural = _("mushroom images")
        ordering = ['-uploaded_at']

class UnknownMushroom(models.Model):
    """User-reported mushroom not in dataset."""
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="mushroom_reports")
    name = models.CharField(max_length=150, help_text="Species name or common name")
    description = models.TextField(blank=True, help_text="Additional description or notes")
    scientific_name = models.CharField(max_length=150, blank=True)
    origin = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='unknown_mushrooms/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    STATUS_CHOICES = (
        ('mapped', 'Mapped'),        # blue
        ('edible', 'Edible'),        # green
        ('poisonous', 'Poisonous'),  # red
        ('unknown', 'Unknown'),      # yellow (Pending)
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    pin_color = models.CharField(max_length=20, default='#0d6efd')  # default bootstrap blue
    is_pending = models.BooleanField(
        default=True,
        help_text='Pending reports stay off the public map until approved'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} @ ({self.latitude}, {self.longitude})"

    @classmethod
    def get_grouped_by_name(cls):
        """Group mushrooms by name for card display."""
        from django.db.models import Count
        from collections import defaultdict
        
        grouped = defaultdict(list)
        mushrooms = cls.objects.all().order_by('-created_at')
        
        for mushroom in mushrooms:
            grouped[mushroom.name.lower().strip()].append(mushroom)
        
        return dict(grouped)

    class Meta:
        ordering = ['-created_at']
