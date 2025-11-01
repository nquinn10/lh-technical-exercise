from django.contrib import admin
from .models import Provider, Patient, Order, CarePlan


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    """Admin interface for Provider model"""
    list_display = ['name', 'npi', 'created_at']
    search_fields = ['name', 'npi']
    readonly_fields = ['created_at']
    list_per_page = 25


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Admin interface for Patient model"""
    list_display = ['first_name', 'last_name', 'mrn', 'created_at']
    search_fields = ['first_name', 'last_name', 'mrn']
    readonly_fields = ['created_at']
    list_per_page = 25


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for Order model"""
    list_display = ['id', 'patient', 'medication_name', 'provider', 'created_at']
    list_filter = ['created_at', 'medication_name']
    search_fields = ['patient__mrn', 'patient__last_name', 'medication_name']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25

    fieldsets = (
        ('Patient & Provider', {
            'fields': ('patient', 'provider')
        }),
        ('Clinical Information', {
            'fields': (
                'primary_diagnosis',
                'medication_name',
                'additional_diagnoses',
                'medication_history',
                'patient_records'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CarePlan)
class CarePlanAdmin(admin.ModelAdmin):
    """Admin interface for CarePlan model"""
    list_display = ['id', 'order', 'generated_at']
    search_fields = ['order__patient__mrn', 'order__id']
    readonly_fields = ['generated_at']
    list_per_page = 25

    fieldsets = (
        ('Associated Order', {
            'fields': ('order',)
        }),
        ('Generated Care Plan', {
            'fields': ('care_plan_text',)
        }),
        ('Metadata', {
            'fields': ('generated_at',),
            'classes': ('collapse',)
        }),
    )
