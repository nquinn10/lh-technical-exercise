"""
Form tests for care_plans app

Tests OrderForm including:
- Format validation (MRN exactly 6 digits, NPI exactly 10 digits)
- Required field validation
- Optional field handling
- Duplicate detection (patient, provider, order)
- Warning acknowledgment flow
- Warning utility methods
"""

from django.test import TestCase
from django.utils import timezone
from care_plans.forms import OrderForm
from care_plans.models import Patient, Provider, Order
from datetime import timedelta


class OrderFormFormatValidationTests(TestCase):
    """Tests for format validation (MRN, NPI, required fields)"""

    def get_valid_form_data(self):
        """Helper method to get valid form data"""
        return {
            'patient_first_name': 'John',
            'patient_last_name': 'Doe',
            'mrn': '123456',
            'provider_name': 'Dr. Jane Smith',
            'provider_npi': '1234567890',
            'primary_diagnosis': 'E11.9',
            'medication_name': 'Metformin',
            'additional_diagnoses': 'I10, E78.5',
            'medication_history': 'Aspirin, Lisinopril',
            'patient_records': 'Patient has history of diabetes...'
        }

    def test_form_valid_with_all_data(self):
        """Test form is valid with all required and optional fields"""
        form = OrderForm(data=self.get_valid_form_data())
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)

    def test_mrn_exactly_six_digits_valid(self):
        """Test MRN with exactly 6 digits is valid"""
        data = self.get_valid_form_data()
        data['mrn'] = '123456'
        form = OrderForm(data=data)
        self.assertTrue(form.is_valid())

    def test_mrn_less_than_six_digits_invalid(self):
        """Test MRN with less than 6 digits is invalid"""
        data = self.get_valid_form_data()
        data['mrn'] = '12345'  # Only 5 digits
        form = OrderForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('mrn', form.errors)
        self.assertIn('exactly 6 digits', str(form.errors['mrn']))

    def test_mrn_more_than_six_digits_invalid(self):
        """Test MRN with more than 6 digits is invalid"""
        data = self.get_valid_form_data()
        data['mrn'] = '1234567'  # 7 digits
        form = OrderForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('mrn', form.errors)
        # Check for either regex error or maxlength error
        error_msg = str(form.errors['mrn'])
        self.assertTrue('6' in error_msg or 'exactly 6 digits' in error_msg)

    def test_mrn_contains_letters_invalid(self):
        """Test MRN with letters is invalid"""
        data = self.get_valid_form_data()
        data['mrn'] = '12345A'
        form = OrderForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('mrn', form.errors)

    def test_mrn_contains_special_characters_invalid(self):
        """Test MRN with special characters is invalid"""
        data = self.get_valid_form_data()
        data['mrn'] = '123-456'
        form = OrderForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('mrn', form.errors)

    def test_npi_exactly_ten_digits_valid(self):
        """Test NPI with exactly 10 digits is valid"""
        data = self.get_valid_form_data()
        data['provider_npi'] = '1234567890'
        form = OrderForm(data=data)
        self.assertTrue(form.is_valid())

    def test_npi_less_than_ten_digits_invalid(self):
        """Test NPI with less than 10 digits is invalid"""
        data = self.get_valid_form_data()
        data['provider_npi'] = '123456789'  # Only 9 digits
        form = OrderForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('provider_npi', form.errors)
        self.assertIn('exactly 10 digits', str(form.errors['provider_npi']))

    def test_npi_more_than_ten_digits_invalid(self):
        """Test NPI with more than 10 digits is invalid"""
        data = self.get_valid_form_data()
        data['provider_npi'] = '12345678901'  # 11 digits
        form = OrderForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('provider_npi', form.errors)
        # Check for either regex error or maxlength error
        error_msg = str(form.errors['provider_npi'])
        self.assertTrue('10' in error_msg or 'exactly 10 digits' in error_msg)

    def test_npi_contains_letters_invalid(self):
        """Test NPI with letters is invalid"""
        data = self.get_valid_form_data()
        data['provider_npi'] = '123456789A'
        form = OrderForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('provider_npi', form.errors)

    def test_required_field_patient_first_name_missing(self):
        """Test form invalid when patient_first_name is missing"""
        data = self.get_valid_form_data()
        del data['patient_first_name']
        form = OrderForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('patient_first_name', form.errors)

    def test_required_field_mrn_missing(self):
        """Test form invalid when mrn is missing"""
        data = self.get_valid_form_data()
        del data['mrn']
        form = OrderForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('mrn', form.errors)

    def test_required_field_primary_diagnosis_missing(self):
        """Test form invalid when primary_diagnosis is missing"""
        data = self.get_valid_form_data()
        del data['primary_diagnosis']
        form = OrderForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('primary_diagnosis', form.errors)

    def test_required_field_patient_records_missing(self):
        """Test form invalid when patient_records is missing"""
        data = self.get_valid_form_data()
        del data['patient_records']
        form = OrderForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('patient_records', form.errors)

    def test_optional_fields_can_be_empty(self):
        """Test optional fields (additional_diagnoses, medication_history) can be empty"""
        data = self.get_valid_form_data()
        data['additional_diagnoses'] = ''
        data['medication_history'] = ''
        form = OrderForm(data=data)
        self.assertTrue(form.is_valid())


class OrderFormPatientDuplicateTests(TestCase):
    """Tests for patient duplicate detection"""

    def get_valid_form_data(self):
        """Helper method to get valid form data"""
        return {
            'patient_first_name': 'John',
            'patient_last_name': 'Doe',
            'mrn': '123456',
            'provider_name': 'Dr. Jane Smith',
            'provider_npi': '1234567890',
            'primary_diagnosis': 'E11.9',
            'medication_name': 'Metformin',
            'additional_diagnoses': '',
            'medication_history': '',
            'patient_records': 'Patient records...'
        }

    def test_patient_duplicate_same_mrn_same_name(self):
        """Test warning shown when patient with same MRN and name exists"""
        # Create existing patient
        Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )

        # Submit form with same MRN and name
        data = self.get_valid_form_data()
        form = OrderForm(data=data)

        # Form should be valid but have warnings
        self.assertTrue(form.is_valid())
        self.assertTrue(form.has_warnings())
        warnings = form.get_warnings()
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]['type'], 'patient_duplicate')
        self.assertIn('123456', warnings[0]['message'])
        self.assertIn('John Doe', warnings[0]['message'])

    def test_patient_duplicate_same_mrn_different_name(self):
        """Test warning shown when MRN exists with different patient name"""
        # Create existing patient
        Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            mrn='123456'
        )

        # Submit form with same MRN but different name
        data = self.get_valid_form_data()
        data['patient_first_name'] = 'John'
        data['patient_last_name'] = 'Doe'
        form = OrderForm(data=data)

        # Form should be valid but have warnings
        self.assertTrue(form.is_valid())
        self.assertTrue(form.has_warnings())
        warnings = form.get_warnings()
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]['type'], 'patient_name_mismatch')
        self.assertIn('123456', warnings[0]['message'])
        self.assertIn('Jane Smith', warnings[0]['message'])
        self.assertIn('John Doe', warnings[0]['message'])

    def test_no_patient_duplicate_warning_for_new_mrn(self):
        """Test no warning when MRN does not exist"""
        # Create patient with different MRN
        Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            mrn='999999'
        )

        # Submit form with new MRN
        data = self.get_valid_form_data()
        data['mrn'] = '123456'
        form = OrderForm(data=data)

        # Form should be valid with no warnings
        self.assertTrue(form.is_valid())
        self.assertFalse(form.has_warnings())


class OrderFormProviderDuplicateTests(TestCase):
    """Tests for provider duplicate detection"""

    def get_valid_form_data(self):
        """Helper method to get valid form data"""
        return {
            'patient_first_name': 'John',
            'patient_last_name': 'Doe',
            'mrn': '123456',
            'provider_name': 'Dr. Jane Smith',
            'provider_npi': '1234567890',
            'primary_diagnosis': 'E11.9',
            'medication_name': 'Metformin',
            'additional_diagnoses': '',
            'medication_history': '',
            'patient_records': 'Patient records...'
        }

    def test_provider_duplicate_same_npi_different_name(self):
        """Test warning shown when NPI exists with different provider name"""
        # Create existing provider
        Provider.objects.create(
            name='Dr. John Doe',
            npi='1234567890'
        )

        # Submit form with same NPI but different name
        data = self.get_valid_form_data()
        data['provider_name'] = 'Dr. Jane Smith'
        data['provider_npi'] = '1234567890'
        form = OrderForm(data=data)

        # Form should be valid but have warnings
        self.assertTrue(form.is_valid())
        self.assertTrue(form.has_warnings())
        warnings = form.get_warnings()
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]['type'], 'provider_duplicate')
        self.assertIn('1234567890', warnings[0]['message'])
        self.assertIn('Dr. John Doe', warnings[0]['message'])
        self.assertIn('Dr. Jane Smith', warnings[0]['message'])

    def test_no_provider_warning_same_npi_same_name(self):
        """Test no warning when NPI exists with same provider name"""
        # Create existing provider
        Provider.objects.create(
            name='Dr. Jane Smith',
            npi='1234567890'
        )

        # Submit form with same NPI and same name
        data = self.get_valid_form_data()
        form = OrderForm(data=data)

        # Form should be valid with no warnings (provider will be reused)
        self.assertTrue(form.is_valid())
        self.assertFalse(form.has_warnings())

    def test_no_provider_warning_new_npi(self):
        """Test no warning when NPI does not exist"""
        # Create provider with different NPI
        Provider.objects.create(
            name='Dr. John Doe',
            npi='9999999999'
        )

        # Submit form with new NPI
        data = self.get_valid_form_data()
        data['provider_npi'] = '1234567890'
        form = OrderForm(data=data)

        # Form should be valid with no warnings
        self.assertTrue(form.is_valid())
        self.assertFalse(form.has_warnings())


class OrderFormOrderDuplicateTests(TestCase):
    """Tests for order duplicate detection"""

    def get_valid_form_data(self):
        """Helper method to get valid form data"""
        return {
            'patient_first_name': 'John',
            'patient_last_name': 'Doe',
            'mrn': '123456',
            'provider_name': 'Dr. Jane Smith',
            'provider_npi': '1234567890',
            'primary_diagnosis': 'E11.9',
            'medication_name': 'Metformin',
            'additional_diagnoses': '',
            'medication_history': '',
            'patient_records': 'Patient records...'
        }

    def test_order_duplicate_same_patient_medication_day(self):
        """Test warning shown when similar order created today"""
        # Create patient and provider
        patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )
        provider = Provider.objects.create(
            name='Dr. Jane Smith',
            npi='1234567890'
        )

        # Create existing order today
        Order.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            patient_records='Patient records...'
        )

        # Submit form with same patient and medication
        data = self.get_valid_form_data()
        form = OrderForm(data=data)

        # Form should be valid but have warnings
        self.assertTrue(form.is_valid())
        self.assertTrue(form.has_warnings())
        warnings = form.get_warnings()
        # Should have patient_duplicate AND order_duplicate warnings
        self.assertGreaterEqual(len(warnings), 1)
        warning_types = [w['type'] for w in warnings]
        self.assertIn('order_duplicate', warning_types)
        # Find the order duplicate warning
        order_warning = next(w for w in warnings if w['type'] == 'order_duplicate')
        self.assertIn('similar order', order_warning['message'].lower())
        self.assertIn('today', order_warning['message'].lower())

    def test_no_order_warning_different_day(self):
        """Test no warning when order created on different day"""
        # Create patient and provider
        patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )
        provider = Provider.objects.create(
            name='Dr. Jane Smith',
            npi='1234567890'
        )

        # Create order from yesterday
        yesterday_order = Order.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            patient_records='Patient records...'
        )
        # Manually set created_at to yesterday
        yesterday_order.created_at = timezone.now() - timedelta(days=1)
        yesterday_order.save()

        # Submit form today
        data = self.get_valid_form_data()
        form = OrderForm(data=data)

        # Form should be valid - may have patient_duplicate warning but NOT order_duplicate
        self.assertTrue(form.is_valid())
        warnings = form.get_warnings()
        warning_types = [w['type'] for w in warnings]
        # Should NOT have order_duplicate warning (order was yesterday)
        self.assertNotIn('order_duplicate', warning_types)

    def test_no_order_warning_different_medication(self):
        """Test no warning when same patient but different medication"""
        # Create patient and provider
        patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )
        provider = Provider.objects.create(
            name='Dr. Jane Smith',
            npi='1234567890'
        )

        # Create order with different medication
        Order.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis='E11.9',
            medication_name='Insulin',  # Different medication
            patient_records='Patient records...'
        )

        # Submit form with different medication
        data = self.get_valid_form_data()
        data['medication_name'] = 'Metformin'
        form = OrderForm(data=data)

        # Form should be valid - may have patient_duplicate warning but NOT order_duplicate
        self.assertTrue(form.is_valid())
        warnings = form.get_warnings()
        warning_types = [w['type'] for w in warnings]
        # Should NOT have order_duplicate warning (different medication)
        self.assertNotIn('order_duplicate', warning_types)

    def test_no_order_warning_different_patient(self):
        """Test no warning when different patient with same medication"""
        # Create different patient
        different_patient = Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            mrn='999999'
        )
        provider = Provider.objects.create(
            name='Dr. Jane Smith',
            npi='1234567890'
        )

        # Create order for different patient
        Order.objects.create(
            patient=different_patient,
            provider=provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            patient_records='Patient records...'
        )

        # Submit form for different patient (MRN 123456)
        data = self.get_valid_form_data()
        form = OrderForm(data=data)

        # Form should be valid with no warnings
        self.assertTrue(form.is_valid())
        self.assertFalse(form.has_warnings())


class OrderFormWarningUtilityTests(TestCase):
    """Tests for warning utility methods"""

    def get_valid_form_data(self):
        """Helper method to get valid form data"""
        return {
            'patient_first_name': 'John',
            'patient_last_name': 'Doe',
            'mrn': '123456',
            'provider_name': 'Dr. Jane Smith',
            'provider_npi': '1234567890',
            'primary_diagnosis': 'E11.9',
            'medication_name': 'Metformin',
            'additional_diagnoses': '',
            'medication_history': '',
            'patient_records': 'Patient records...'
        }

    def test_has_warnings_returns_true_when_warnings_exist(self):
        """Test has_warnings() returns True when warnings present"""
        # Create existing patient to trigger warning
        Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )

        data = self.get_valid_form_data()
        form = OrderForm(data=data)
        form.is_valid()  # Trigger validation

        self.assertTrue(form.has_warnings())

    def test_has_warnings_returns_false_when_no_warnings(self):
        """Test has_warnings() returns False when no warnings"""
        data = self.get_valid_form_data()
        form = OrderForm(data=data)
        form.is_valid()  # Trigger validation

        self.assertFalse(form.has_warnings())

    def test_get_warnings_returns_all_warnings(self):
        """Test get_warnings() returns all warnings when multiple exist"""
        # Create existing patient
        Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )

        # Create existing provider with different name
        Provider.objects.create(
            name='Dr. John Doe',
            npi='1234567890'
        )

        data = self.get_valid_form_data()
        data['provider_name'] = 'Dr. Jane Smith'  # Different name
        form = OrderForm(data=data)
        form.is_valid()  # Trigger validation

        warnings = form.get_warnings()
        self.assertEqual(len(warnings), 2)  # Patient + Provider warnings
        warning_types = [w['type'] for w in warnings]
        self.assertIn('patient_duplicate', warning_types)
        self.assertIn('provider_duplicate', warning_types)

    def test_get_warnings_returns_empty_list_when_no_warnings(self):
        """Test get_warnings() returns empty list when no warnings"""
        data = self.get_valid_form_data()
        form = OrderForm(data=data)
        form.is_valid()  # Trigger validation

        warnings = form.get_warnings()
        self.assertEqual(len(warnings), 0)
        self.assertEqual(warnings, [])
