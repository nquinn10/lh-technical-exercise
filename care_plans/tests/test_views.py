"""
View tests for care_plans app

Tests all views including:
- Order creation (GET, POST with valid/invalid data, warnings)
- Order success (with/without care plan, retry scenarios)
- Update care plan
- Download care plan
- Orders list
- CSV export
"""

from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from care_plans.models import Patient, Provider, Order, CarePlan
from care_plans.llm import generate_care_plan
import csv
from io import StringIO


class OrderCreationViewTests(TestCase):
    """Tests for create_order view"""

    def setUp(self):
        """Set up test client"""
        self.client = Client()
        self.url = reverse('create_order')

    def get_valid_form_data(self):
        """Helper to get valid form data"""
        return {
            'patient_first_name': 'John',
            'patient_last_name': 'Doe',
            'mrn': '123456',
            'provider_name': 'Dr. Jane Smith',
            'provider_npi': '1234567890',
            'primary_diagnosis': 'E11.9',
            'medication_name': 'Metformin',
            'additional_diagnoses': 'I10, E78.5',
            'medication_history': 'Aspirin',
            'patient_records': 'Patient has history of diabetes...'
        }

    def test_create_order_get_request(self):
        """Test GET request returns form"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'care_plans/create_order.html')
        self.assertIn('form', response.context)
        # Should not have warnings on initial GET
        self.assertNotIn('warnings', response.context)

    def test_create_order_post_valid_no_warnings(self):
        """Test POST with valid data and no warnings creates order and redirects"""
        data = self.get_valid_form_data()
        response = self.client.post(self.url, data=data)

        # Should redirect to success page
        self.assertEqual(response.status_code, 302)

        # Order should be created
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.patient.mrn, '123456')
        self.assertEqual(order.medication_name, 'Metformin')

        # Should redirect to order success page
        self.assertRedirects(response, reverse('order_success', kwargs={'order_id': order.id}))

    def test_create_order_post_valid_with_warnings_not_acknowledged(self):
        """Test POST with warnings but not acknowledged shows warnings"""
        # Create existing patient to trigger warning
        Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )

        data = self.get_valid_form_data()
        response = self.client.post(self.url, data=data)

        # Should NOT create order
        self.assertEqual(Order.objects.count(), 0)

        # Should re-render form with warnings
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'care_plans/create_order.html')
        self.assertIn('warnings', response.context)
        self.assertGreater(len(response.context['warnings']), 0)

    def test_create_order_post_valid_with_warnings_acknowledged(self):
        """Test POST with warnings acknowledged creates order"""
        # Create existing patient to trigger warning
        Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )

        data = self.get_valid_form_data()
        data['acknowledge_warnings'] = 'on'
        response = self.client.post(self.url, data=data)

        # Order should be created despite warnings
        self.assertEqual(Order.objects.count(), 1)

        # Should redirect to success page
        self.assertEqual(response.status_code, 302)

    def test_create_order_post_invalid_data(self):
        """Test POST with invalid data shows errors"""
        data = self.get_valid_form_data()
        data['mrn'] = '12345'  # Invalid - only 5 digits
        response = self.client.post(self.url, data=data)

        # Should NOT create order
        self.assertEqual(Order.objects.count(), 0)

        # Should re-render form with errors
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'care_plans/create_order.html')
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)


class OrderSuccessViewTests(TestCase):
    """Tests for order_success view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )
        self.provider = Provider.objects.create(
            name='Dr. Jane Smith',
            npi='1234567890'
        )
        self.order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            patient_records='Patient records...'
        )

    @patch('care_plans.views.generate_care_plan')
    def test_order_success_with_care_plan_generated(self, mock_generate):
        """Test success page when care plan is successfully generated"""
        # Mock successful care plan generation
        mock_care_plan = CarePlan.objects.create(
            order=self.order,
            care_plan_text='Generated care plan text'
        )
        mock_generate.return_value = mock_care_plan

        url = reverse('order_success', kwargs={'order_id': self.order.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'care_plans/order_success.html')
        self.assertEqual(response.context['order'], self.order)
        self.assertEqual(response.context['care_plan'], mock_care_plan)
        self.assertIsNone(response.context['error_message'])

    @patch('care_plans.views.generate_care_plan')
    def test_order_success_without_care_plan_generation_failed(self, mock_generate):
        """Test success page when care plan generation fails"""
        # Mock failed care plan generation
        mock_generate.side_effect = Exception('API Error')

        url = reverse('order_success', kwargs={'order_id': self.order.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'care_plans/order_success.html')
        self.assertEqual(response.context['order'], self.order)
        self.assertIsNone(response.context['care_plan'])
        self.assertIsNotNone(response.context['error_message'])
        self.assertIn('Unable to generate', response.context['error_message'])

    def test_order_success_care_plan_already_exists(self):
        """Test success page when care plan already exists (no regeneration)"""
        # Create existing care plan
        existing_care_plan = CarePlan.objects.create(
            order=self.order,
            care_plan_text='Existing care plan'
        )

        url = reverse('order_success', kwargs={'order_id': self.order.id})

        with patch('care_plans.views.generate_care_plan') as mock_generate:
            response = self.client.get(url)

            # generate_care_plan should NOT be called (care plan exists)
            mock_generate.assert_not_called()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['care_plan'], existing_care_plan)
            self.assertIsNone(response.context['error_message'])

    def test_order_success_invalid_order_id(self):
        """Test 404 when order ID does not exist"""
        url = reverse('order_success', kwargs={'order_id': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class UpdateCarePlanViewTests(TestCase):
    """Tests for update_care_plan view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )
        provider = Provider.objects.create(
            name='Dr. Jane Smith',
            npi='1234567890'
        )
        self.order = Order.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            patient_records='Patient records...'
        )
        self.care_plan = CarePlan.objects.create(
            order=self.order,
            care_plan_text='Original care plan text'
        )

    def test_update_care_plan_valid_post(self):
        """Test updating care plan with valid POST data"""
        url = reverse('update_care_plan', kwargs={'order_id': self.order.id})
        updated_text = 'Updated care plan text with edits'

        response = self.client.post(url, data={'care_plan_text': updated_text})

        # Should redirect back to order success page
        self.assertRedirects(response, reverse('order_success', kwargs={'order_id': self.order.id}))

        # Care plan should be updated in database
        self.care_plan.refresh_from_db()
        self.assertEqual(self.care_plan.care_plan_text, updated_text)

    def test_update_care_plan_invalid_order_id(self):
        """Test 404 when order ID does not exist"""
        url = reverse('update_care_plan', kwargs={'order_id': 99999})
        response = self.client.post(url, data={'care_plan_text': 'New text'})
        self.assertEqual(response.status_code, 404)


class DownloadCarePlanViewTests(TestCase):
    """Tests for download_care_plan view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )
        provider = Provider.objects.create(
            name='Dr. Jane Smith',
            npi='1234567890'
        )
        self.order = Order.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            patient_records='Patient records...'
        )
        self.care_plan = CarePlan.objects.create(
            order=self.order,
            care_plan_text='This is the care plan content for download.'
        )

    def test_download_care_plan_valid(self):
        """Test downloading care plan returns file response"""
        url = reverse('download_care_plan', kwargs={'order_id': self.order.id})
        response = self.client.get(url)

        # Should return file download response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertIn('attachment', response['Content-Disposition'])
        # Check filename contains MRN and .txt extension
        self.assertIn('MRN123456', response['Content-Disposition'])
        self.assertIn('.txt', response['Content-Disposition'])

        # Should contain care plan text
        content = response.content.decode('utf-8')
        self.assertIn('This is the care plan content', content)

    def test_download_care_plan_no_care_plan(self):
        """Test download fails when no care plan exists"""
        # Create order without care plan
        patient = Patient.objects.create(
            first_name='Jane',
            last_name='Smith',
            mrn='999999'
        )
        provider = Provider.objects.create(
            name='Dr. John Doe',
            npi='9999999999'
        )
        order = Order.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis='I10',
            medication_name='Lisinopril',
            patient_records='Records...'
        )

        url = reverse('download_care_plan', kwargs={'order_id': order.id})
        response = self.client.get(url)

        # Should return 404 or error (care plan doesn't exist)
        self.assertEqual(response.status_code, 404)


class OrdersListViewTests(TestCase):
    """Tests for orders_list view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.url = reverse('orders_list')

    def test_orders_list_get_request(self):
        """Test GET request returns orders list page"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'care_plans/orders_list.html')
        self.assertIn('orders', response.context)

    def test_orders_list_with_orders(self):
        """Test orders list displays all orders"""
        # Create multiple orders
        patient1 = Patient.objects.create(first_name='John', last_name='Doe', mrn='123456')
        patient2 = Patient.objects.create(first_name='Jane', last_name='Smith', mrn='999999')
        provider = Provider.objects.create(name='Dr. Test', npi='1234567890')

        order1 = Order.objects.create(
            patient=patient1,
            provider=provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            patient_records='Records 1'
        )
        order2 = Order.objects.create(
            patient=patient2,
            provider=provider,
            primary_diagnosis='I10',
            medication_name='Lisinopril',
            patient_records='Records 2'
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        orders = response.context['orders']
        self.assertEqual(orders.count(), 2)
        # Orders should be sorted by created_at descending (newest first)
        self.assertEqual(orders[0].id, order2.id)
        self.assertEqual(orders[1].id, order1.id)

    def test_orders_list_empty_database(self):
        """Test orders list with no orders shows empty state"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['orders'].count(), 0)


class CSVExportViewTests(TestCase):
    """Tests for export_csv view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.url = reverse('export_csv')

    def test_export_csv_returns_csv_response(self):
        """Test CSV export returns correct content type and headers"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('orders_export_', response['Content-Disposition'])
        self.assertIn('.csv', response['Content-Disposition'])

    def test_export_csv_with_orders(self):
        """Test CSV export contains all order data"""
        # Create test data
        patient = Patient.objects.create(first_name='John', last_name='Doe', mrn='123456')
        provider = Provider.objects.create(name='Dr. Jane Smith', npi='1234567890')
        order = Order.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            additional_diagnoses='I10, E78.5',
            medication_history='Aspirin',
            patient_records='Patient records...'
        )
        care_plan = CarePlan.objects.create(
            order=order,
            care_plan_text='Care plan text'
        )

        response = self.client.get(self.url)

        # Parse CSV content
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(StringIO(content))
        rows = list(csv_reader)

        # Should have header row + 1 data row
        self.assertEqual(len(rows), 2)

        # Check header
        header = rows[0]
        self.assertIn('Order ID', header)
        self.assertIn('Patient MRN', header)
        self.assertIn('Medication Name', header)
        self.assertIn('Care Plan Text', header)

        # Check data row
        data_row = rows[1]
        self.assertIn(str(order.id), data_row)
        self.assertIn('123456', data_row)
        self.assertIn('Metformin', data_row)
        self.assertIn('Care plan text', data_row)

    def test_export_csv_order_without_care_plan(self):
        """Test CSV export handles orders without care plans"""
        # Create order without care plan
        patient = Patient.objects.create(first_name='John', last_name='Doe', mrn='123456')
        provider = Provider.objects.create(name='Dr. Jane Smith', npi='1234567890')
        order = Order.objects.create(
            patient=patient,
            provider=provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            patient_records='Patient records...'
        )

        response = self.client.get(self.url)

        # Parse CSV content
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(StringIO(content))
        rows = list(csv_reader)

        # Should have header + 1 data row
        self.assertEqual(len(rows), 2)

        # Care plan text should be empty string (not cause error)
        data_row = rows[1]
        self.assertIn(str(order.id), data_row)
        # Last column (care plan text) should be empty
        self.assertEqual(data_row[-1], '')

    def test_export_csv_multiple_orders(self):
        """Test CSV export includes all orders"""
        # Create multiple orders
        patient1 = Patient.objects.create(first_name='John', last_name='Doe', mrn='123456')
        patient2 = Patient.objects.create(first_name='Jane', last_name='Smith', mrn='999999')
        provider = Provider.objects.create(name='Dr. Test', npi='1234567890')

        Order.objects.create(
            patient=patient1,
            provider=provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            patient_records='Records 1'
        )
        Order.objects.create(
            patient=patient2,
            provider=provider,
            primary_diagnosis='I10',
            medication_name='Lisinopril',
            patient_records='Records 2'
        )

        response = self.client.get(self.url)

        # Parse CSV content
        content = response.content.decode('utf-8')
        csv_reader = csv.reader(StringIO(content))
        rows = list(csv_reader)

        # Should have header + 2 data rows
        self.assertEqual(len(rows), 3)
