"""
Model tests for care_plans app

Tests Patient, Provider, Order, and CarePlan models including:
- Model creation with valid data
- Unique constraints
- String representations
- Timestamps (auto_now_add, auto_now)
- Relationships and reverse accessors
"""

from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone
from care_plans.models import Patient, Provider, Order, CarePlan
import time


class PatientModelTests(TestCase):
    """Tests for Patient model"""

    def test_patient_creation(self):
        """Test patient can be created with valid data"""
        patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456"
        )
        self.assertEqual(patient.first_name, "John")
        self.assertEqual(patient.last_name, "Doe")
        self.assertEqual(patient.mrn, "123456")
        self.assertIsNotNone(patient.id)

    def test_patient_mrn_unique(self):
        """Test MRN uniqueness constraint"""
        Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456"
        )
        # Attempt to create another patient with same MRN
        with self.assertRaises(IntegrityError):
            Patient.objects.create(
                first_name="Jane",
                last_name="Smith",
                mrn="123456"
            )

    def test_patient_str_representation(self):
        """Test patient string representation"""
        patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456"
        )
        self.assertEqual(str(patient), "John Doe (MRN: 123456)")

    def test_patient_created_at_auto_populated(self):
        """Test created_at timestamp is automatically set"""
        before = timezone.now()
        patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456"
        )
        after = timezone.now()
        self.assertIsNotNone(patient.created_at)
        self.assertGreaterEqual(patient.created_at, before)
        self.assertLessEqual(patient.created_at, after)


class ProviderModelTests(TestCase):
    """Tests for Provider model"""

    def test_provider_creation(self):
        """Test provider can be created with valid data"""
        provider = Provider.objects.create(
            name="Dr. Jane Smith",
            npi="1234567890"
        )
        self.assertEqual(provider.name, "Dr. Jane Smith")
        self.assertEqual(provider.npi, "1234567890")
        self.assertIsNotNone(provider.id)

    def test_provider_npi_unique(self):
        """Test NPI uniqueness constraint"""
        Provider.objects.create(
            name="Dr. Jane Smith",
            npi="1234567890"
        )
        # Attempt to create another provider with same NPI
        with self.assertRaises(IntegrityError):
            Provider.objects.create(
                name="Dr. John Doe",
                npi="1234567890"
            )

    def test_provider_str_representation(self):
        """Test provider string representation"""
        provider = Provider.objects.create(
            name="Dr. Jane Smith",
            npi="1234567890"
        )
        self.assertEqual(str(provider), "Dr. Jane Smith (NPI: 1234567890)")

    def test_provider_created_at_auto_populated(self):
        """Test created_at timestamp is automatically set"""
        before = timezone.now()
        provider = Provider.objects.create(
            name="Dr. Jane Smith",
            npi="1234567890"
        )
        after = timezone.now()
        self.assertIsNotNone(provider.created_at)
        self.assertGreaterEqual(provider.created_at, before)
        self.assertLessEqual(provider.created_at, after)


class OrderModelTests(TestCase):
    """Tests for Order model"""

    def setUp(self):
        """Create patient and provider for order tests"""
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456"
        )
        self.provider = Provider.objects.create(
            name="Dr. Jane Smith",
            npi="1234567890"
        )

    def test_order_creation_with_relationships(self):
        """Test order can be created with foreign keys"""
        order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="E11.9",
            medication_name="Metformin",
            additional_diagnoses="I10, E78.5",
            medication_history="Aspirin, Lisinopril",
            patient_records="Patient has history of diabetes..."
        )
        self.assertEqual(order.patient, self.patient)
        self.assertEqual(order.provider, self.provider)
        self.assertEqual(order.primary_diagnosis, "E11.9")
        self.assertEqual(order.medication_name, "Metformin")
        self.assertIsNotNone(order.id)

    def test_order_required_fields(self):
        """Test all required fields are populated"""
        order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="E11.9",
            medication_name="Metformin",
            patient_records="Patient records..."
        )
        # Required fields should not be None
        self.assertIsNotNone(order.patient)
        self.assertIsNotNone(order.provider)
        self.assertIsNotNone(order.primary_diagnosis)
        self.assertIsNotNone(order.medication_name)
        self.assertIsNotNone(order.patient_records)

    def test_order_optional_fields_can_be_empty(self):
        """Test optional fields (additional_diagnoses, medication_history) can be empty"""
        order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="E11.9",
            medication_name="Metformin",
            patient_records="Patient records...",
            additional_diagnoses="",  # Empty optional field
            medication_history=""      # Empty optional field
        )
        self.assertEqual(order.additional_diagnoses, "")
        self.assertEqual(order.medication_history, "")

    def test_order_timestamps_auto_populated(self):
        """Test created_at and updated_at timestamps are set"""
        before = timezone.now()
        order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="E11.9",
            medication_name="Metformin",
            patient_records="Patient records..."
        )
        after = timezone.now()

        self.assertIsNotNone(order.created_at)
        self.assertIsNotNone(order.updated_at)
        self.assertGreaterEqual(order.created_at, before)
        self.assertLessEqual(order.created_at, after)

    def test_order_relationship_to_patient(self):
        """Test order foreign key relationship to patient"""
        order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="E11.9",
            medication_name="Metformin",
            patient_records="Patient records..."
        )
        # Can access patient from order
        self.assertEqual(order.patient.first_name, "John")
        self.assertEqual(order.patient.mrn, "123456")

    def test_order_relationship_to_provider(self):
        """Test order foreign key relationship to provider"""
        order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="E11.9",
            medication_name="Metformin",
            patient_records="Patient records..."
        )
        # Can access provider from order
        self.assertEqual(order.provider.name, "Dr. Jane Smith")
        self.assertEqual(order.provider.npi, "1234567890")


class CarePlanModelTests(TestCase):
    """Tests for CarePlan model"""

    def setUp(self):
        """Create order for care plan tests"""
        patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456"
        )
        provider = Provider.objects.create(
            name="Dr. Jane Smith",
            npi="1234567890"
        )
        self.order = Order.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis="E11.9",
            medication_name="Metformin",
            patient_records="Patient records..."
        )

    def test_care_plan_creation(self):
        """Test care plan can be created with valid data"""
        care_plan = CarePlan.objects.create(
            order=self.order,
            care_plan_text="This is a test care plan..."
        )
        self.assertEqual(care_plan.order, self.order)
        self.assertEqual(care_plan.care_plan_text, "This is a test care plan...")
        self.assertIsNotNone(care_plan.id)

    def test_care_plan_one_to_one_relationship(self):
        """Test OneToOne relationship - only one care plan per order"""
        CarePlan.objects.create(
            order=self.order,
            care_plan_text="First care plan"
        )
        # Attempt to create another care plan for same order
        with self.assertRaises(IntegrityError):
            CarePlan.objects.create(
                order=self.order,
                care_plan_text="Second care plan"
            )

    def test_care_plan_timestamps_auto_populated(self):
        """Test generated_at and updated_at timestamps are set"""
        before = timezone.now()
        care_plan = CarePlan.objects.create(
            order=self.order,
            care_plan_text="Test care plan"
        )
        after = timezone.now()

        self.assertIsNotNone(care_plan.generated_at)
        self.assertIsNotNone(care_plan.updated_at)
        self.assertGreaterEqual(care_plan.generated_at, before)
        self.assertLessEqual(care_plan.generated_at, after)

    def test_care_plan_updated_at_changes_on_save(self):
        """Test updated_at timestamp changes when care plan is saved"""
        care_plan = CarePlan.objects.create(
            order=self.order,
            care_plan_text="Original text"
        )
        original_updated_at = care_plan.updated_at

        # Wait a small amount to ensure timestamp difference
        time.sleep(0.01)

        # Update and save
        care_plan.care_plan_text = "Updated text"
        care_plan.save()

        # updated_at should have changed
        self.assertGreater(care_plan.updated_at, original_updated_at)

    def test_care_plan_generated_at_does_not_change_on_save(self):
        """Test generated_at timestamp does NOT change when care plan is saved"""
        care_plan = CarePlan.objects.create(
            order=self.order,
            care_plan_text="Original text"
        )
        original_generated_at = care_plan.generated_at

        # Wait a small amount
        time.sleep(0.01)

        # Update and save
        care_plan.care_plan_text = "Updated text"
        care_plan.save()

        # generated_at should NOT have changed
        self.assertEqual(care_plan.generated_at, original_generated_at)

    def test_care_plan_reverse_accessor(self):
        """Test reverse accessor from order to care plan (order.care_plan)"""
        care_plan = CarePlan.objects.create(
            order=self.order,
            care_plan_text="Test care plan"
        )
        # Can access care plan from order using related_name
        self.assertEqual(self.order.care_plan, care_plan)
        self.assertEqual(self.order.care_plan.care_plan_text, "Test care plan")

    def test_care_plan_reverse_accessor_does_not_exist(self):
        """Test reverse accessor raises DoesNotExist if no care plan exists"""
        # Order exists but no care plan created
        with self.assertRaises(CarePlan.DoesNotExist):
            _ = self.order.care_plan

    def test_care_plan_initially_updated_at_equals_generated_at(self):
        """Test that initially updated_at equals generated_at"""
        care_plan = CarePlan.objects.create(
            order=self.order,
            care_plan_text="Test care plan"
        )
        # On first save, updated_at should equal generated_at (or very close)
        time_diff = abs((care_plan.updated_at - care_plan.generated_at).total_seconds())
        self.assertLess(time_diff, 1)  # Less than 1 second difference
