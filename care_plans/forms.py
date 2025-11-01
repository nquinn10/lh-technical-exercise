from django import forms
from django.core.validators import RegexValidator
from .models import Provider, Patient, Order
import re
from django.utils import timezone
import zoneinfo


class OrderForm(forms.Form):
    """
    Form for creating care plan orders

    Handles both patient/provider data and clinical information in a single submission.
    Uses hybrid validation: client-side for format, server-side for duplicates.
    """

    # Patient fields
    patient_first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    patient_last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    mrn = forms.CharField(
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '6-digit MRN',
            'maxlength': '6'
        })
    )

    # Provider fields
    provider_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Provider Name'})
    )
    provider_npi = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '10-digit NPI',
            'maxlength': '10'
        })
    )

    # Clinical fields
    primary_diagnosis = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ICD-10 code (e.g., E11.9)'
        })
    )
    medication_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Medication Name'})
    )
    additional_diagnoses = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Comma-separated ICD-10 codes (optional)'
        })
    )
    medication_history = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Comma-separated list of medications (optional)'
        })
    )
    patient_records = forms.CharField(
        max_length=50000,
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 15,
            'placeholder': 'Full patient medical history and clinical notes'
        })
    )

    def __init__(self, *args, **kwargs):
        """Initialize form and set up warnings storage"""
        super().__init__(*args, **kwargs)
        self.warnings = []

    def clean_mrn(self):
        """
        Validate MRN format
        - Must be exactly 6 digits
        """
        mrn = self.cleaned_data['mrn']
        if not re.match(r'^\d{6}$', mrn):
            raise forms.ValidationError("MRN must be exactly 6 digits")

        return mrn

    def clean_provider_npi(self):
        """
        Validate NPI format
        - Must be exactly 10 digits
        """
        npi = self.cleaned_data['provider_npi']
        if not re.match(r'^\d{10}$', npi):
            raise forms.ValidationError('NPI must be exactly 10 digits')

        return npi

    def clean(self):
        """
        Perform cross-field validation and duplicate checking
        """
        cleaned_data = super().clean()

        # Only check for duplicates if basic validation passed
        if not self.errors:
            self._check_patient_duplicate(cleaned_data)
            self._check_provider_duplicate(cleaned_data)
            self._check_order_duplicate(cleaned_data)

        return cleaned_data

    def _check_patient_duplicate(self, data):
        """
        Check if patient with same MRN exists
        - If MRN exists with same name: warning (potential duplicate)
        - If MRN exists with different name: warning (data mismatch)
        """
        mrn = data.get('mrn')
        first_name = data.get('patient_first_name')
        last_name = data.get('patient_last_name')

        if not mrn or not first_name or not last_name:
            return

        existing_patient = Patient.objects.filter(mrn=mrn).first()

        if existing_patient:
            # Check if names match
            if (existing_patient.first_name.lower() == first_name.lower() and
                existing_patient.last_name.lower() == last_name.lower()):
                # Same MRN, same name - likely duplicate
                self.warnings.append({
                    'type': 'patient_duplicate',
                    'message': f'A patient with MRN {mrn} and name "{first_name} {last_name}" already exists. This may be a duplicate order.'
                })
            else:
                # Same MRN, different name - data mismatch (more serious)
                self.warnings.append({
                    'type': 'patient_name_mismatch',
                    'message': f'MRN {mrn} belongs to "{existing_patient.first_name} {existing_patient.last_name}". You entered "{first_name} {last_name}". If you proceed, this order will be created for {existing_patient.first_name} {existing_patient.last_name}, NOT {first_name} {last_name}.'
                })

    def _check_provider_duplicate(self, data):
        """
        Check if NPI exists with a different provider name
        """
        npi = data.get('provider_npi')
        provider_name = data.get('provider_name')

        if not npi or not provider_name:
            return

        provider = Provider.objects.filter(npi=npi).first()

        if provider and provider.name.lower() != provider_name.lower():
            self.warnings.append({
                'type': 'provider_duplicate',
                'message': f'NPI {npi} belongs to "{provider.name}". You entered "{provider_name}". If you proceed, this order will use {provider.name}, NOT {provider_name}. Using inconsistent names can cause reporting issues.'
            })

    def _check_order_duplicate(self, data):
        """
        Check if similar order was created today
        """
        mrn = data.get('mrn')
        medication = data.get('medication_name')

        if not mrn or not medication:
            return

        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        duplicate_order = Order.objects.filter(
            patient__mrn=mrn,
            medication_name__iexact=medication,
            created_at__gte=today_start
        ).first()

        if duplicate_order:
            # Convert to local timezone for display
            local_tz = zoneinfo.ZoneInfo('America/Los_Angeles')
            local_time = duplicate_order.created_at.astimezone(local_tz)
            time_str = local_time.strftime('%I:%M %p %Z')
            self.warnings.append({
                'type': 'order_duplicate',
                'message': f'A similar order for this patient and medication was created today at {time_str}. This might be a duplicate or an edit.'
            })

    def has_warnings(self):
        """Check if form has any warnings"""
        return len(self.warnings) > 0

    def get_warnings(self):
        """Get all warnings"""
        return self.warnings
