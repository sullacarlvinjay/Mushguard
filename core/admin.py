from django.contrib import admin
from .models import MushroomImage, UnknownMushroom

@admin.register(MushroomImage)
class MushroomImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'uploaded_at', 'is_edible', 'species', 'edibility_confidence', 'species_confidence')
    list_filter = ('is_edible', 'species', 'uploaded_at')
    search_fields = ('species',)
    readonly_fields = ('uploaded_at',)
    ordering = ('-uploaded_at',)

@admin.register(UnknownMushroom)
class UnknownMushroomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'scientific_name', 'description_short', 'origin_short', 'status', 'latitude', 'longitude', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def description_short(self, obj):
        """Return truncated description for list display."""
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    description_short.short_description = 'Description'

    def origin_short(self, obj):
        """Return truncated origin for list display."""
        if getattr(obj, 'origin', None):
            return obj.origin[:50] + '...' if len(obj.origin) > 50 else obj.origin
        return '-'
    origin_short.short_description = 'Origin'
