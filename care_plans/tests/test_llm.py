"""
LLM integration tests for care_plans app

Tests the Claude API integration with mocked API calls:
- Successful care plan generation
- API connection errors
- Invalid API responses
- Rate limiting
- Prompt construction with all order data
"""

from django.test import TestCase
from unittest.mock import patch, MagicMock
from care_plans.models import Patient, Provider, Order, CarePlan
from care_plans.llm import generate_care_plan
import anthropic


class LLMSuccessfulGenerationTests(TestCase):
    """Tests for successful care plan generation"""

    def setUp(self):
        """Set up test data"""
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
            primary_diagnosis='E11.9 - Type 2 Diabetes',
            medication_name='Metformin',
            additional_diagnoses='I10 - Hypertension, E78.5 - Hyperlipidemia',
            medication_history='Aspirin 81mg daily, Lisinopril 10mg daily',
            patient_records='Patient is a 65-year-old male with history of type 2 diabetes...'
        )

    @patch('care_plans.llm.anthropic.Anthropic')
    def test_generate_care_plan_success(self, mock_anthropic_class):
        """Test successful care plan generation via mocked API"""
        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock the API response
        mock_response = MagicMock()
        mock_content_block = MagicMock()
        mock_content_block.text = "Generated care plan text with treatment recommendations"
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        # Call generate_care_plan
        care_plan = generate_care_plan(self.order)

        # Verify care plan was created
        self.assertIsNotNone(care_plan)
        self.assertIsInstance(care_plan, CarePlan)
        self.assertEqual(care_plan.order, self.order)
        self.assertEqual(care_plan.care_plan_text, "Generated care plan text with treatment recommendations")
        self.assertIsNotNone(care_plan.generated_at)

        # Verify API was called correctly
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args

        # Verify model parameter
        self.assertEqual(call_args.kwargs['model'], 'claude-sonnet-4-20250514')

        # Verify max_tokens
        self.assertEqual(call_args.kwargs['max_tokens'], 4096)

        # Verify messages structure
        messages = call_args.kwargs['messages']
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['role'], 'user')
        self.assertIn('content', messages[0])

    @patch('care_plans.llm.anthropic.Anthropic')
    def test_generate_care_plan_saves_to_database(self, mock_anthropic_class):
        """Test care plan is saved to database"""
        # Mock the API
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_content_block = MagicMock()
        mock_content_block.text = "Care plan content"
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        # Generate care plan
        care_plan = generate_care_plan(self.order)

        # Verify it's in database
        self.assertEqual(CarePlan.objects.count(), 1)
        db_care_plan = CarePlan.objects.first()
        self.assertEqual(db_care_plan.id, care_plan.id)
        self.assertEqual(db_care_plan.care_plan_text, "Care plan content")

    @patch('care_plans.llm.anthropic.Anthropic')
    def test_generate_care_plan_returns_careplan_object(self, mock_anthropic_class):
        """Test generate_care_plan returns CarePlan instance"""
        # Mock the API
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_content_block = MagicMock()
        mock_content_block.text = "Care plan"
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        # Generate care plan
        result = generate_care_plan(self.order)

        # Verify return type
        self.assertIsInstance(result, CarePlan)
        self.assertEqual(result.order, self.order)


class LLMAPIErrorHandlingTests(TestCase):
    """Tests for API error handling"""

    def setUp(self):
        """Set up test data"""
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

    @patch('care_plans.llm.anthropic.Anthropic')
    def test_generate_care_plan_api_connection_error(self, mock_anthropic_class):
        """Test API connection error raises exception"""
        # Mock connection error
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("Connection error")

        # Should raise exception
        with self.assertRaises(Exception) as context:
            generate_care_plan(self.order)

        self.assertIn("Connection error", str(context.exception))

        # No care plan should be created
        self.assertEqual(CarePlan.objects.count(), 0)

    @patch('care_plans.llm.anthropic.Anthropic')
    def test_generate_care_plan_api_rate_limit_error(self, mock_anthropic_class):
        """Test rate limit error raises exception"""
        # Mock rate limit error (429)
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        # Use generic Exception instead of specific Anthropic error (requires response/body)
        mock_client.messages.create.side_effect = Exception("Rate limit exceeded - 429")

        # Should raise exception
        with self.assertRaises(Exception) as context:
            generate_care_plan(self.order)

        self.assertIn("Rate limit", str(context.exception))

        # No care plan should be created
        self.assertEqual(CarePlan.objects.count(), 0)

    @patch('care_plans.llm.anthropic.Anthropic')
    def test_generate_care_plan_api_authentication_error(self, mock_anthropic_class):
        """Test authentication error raises exception"""
        # Mock authentication error
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        # Use generic Exception instead of specific Anthropic error (requires response/body)
        mock_client.messages.create.side_effect = Exception("Invalid API key - 401")

        # Should raise exception
        with self.assertRaises(Exception) as context:
            generate_care_plan(self.order)

        self.assertIn("API key", str(context.exception))

        # No care plan should be created
        self.assertEqual(CarePlan.objects.count(), 0)

    @patch('care_plans.llm.anthropic.Anthropic')
    def test_generate_care_plan_invalid_response(self, mock_anthropic_class):
        """Test invalid API response format raises exception"""
        # Mock invalid response (missing content)
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = []  # Empty content
        mock_client.messages.create.return_value = mock_response

        # Should raise exception (IndexError when accessing content[0])
        with self.assertRaises(IndexError):
            generate_care_plan(self.order)

        # No care plan should be created
        self.assertEqual(CarePlan.objects.count(), 0)


class LLMPromptConstructionTests(TestCase):
    """Tests for prompt construction with order data"""

    def setUp(self):
        """Set up test data"""
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            mrn='123456'
        )
        self.provider = Provider.objects.create(
            name='Dr. Jane Smith',
            npi='1234567890'
        )

    @patch('care_plans.llm.anthropic.Anthropic')
    def test_prompt_includes_all_order_data(self, mock_anthropic_class):
        """Test prompt includes all order fields"""
        # Create order with all fields
        order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis='E11.9 - Type 2 Diabetes',
            medication_name='Metformin 500mg',
            additional_diagnoses='I10 - Hypertension, E78.5 - Hyperlipidemia',
            medication_history='Aspirin 81mg, Lisinopril 10mg',
            patient_records='Patient is 65yo male with T2DM for 10 years...'
        )

        # Mock the API
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_content_block = MagicMock()
        mock_content_block.text = "Care plan"
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        # Generate care plan
        generate_care_plan(order)

        # Verify API was called
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs['messages']
        prompt = messages[0]['content']

        # Verify all data is in prompt
        self.assertIn('John', prompt)
        self.assertIn('Doe', prompt)
        self.assertIn('123456', prompt)
        self.assertIn('Dr. Jane Smith', prompt)
        self.assertIn('1234567890', prompt)
        self.assertIn('E11.9', prompt)
        self.assertIn('Metformin 500mg', prompt)
        self.assertIn('I10', prompt)
        self.assertIn('Aspirin 81mg', prompt)
        self.assertIn('65yo male', prompt)

    @patch('care_plans.llm.anthropic.Anthropic')
    def test_prompt_handles_optional_fields_empty(self, mock_anthropic_class):
        """Test prompt handles empty optional fields correctly"""
        # Create order with empty optional fields
        order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            additional_diagnoses='',  # Empty
            medication_history='',     # Empty
            patient_records='Patient records...'
        )

        # Mock the API
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_content_block = MagicMock()
        mock_content_block.text = "Care plan"
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        # Generate care plan
        generate_care_plan(order)

        # Verify API was called
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs['messages']
        prompt = messages[0]['content']

        # Prompt should be valid (not contain "None" or fail)
        self.assertIsInstance(prompt, str)
        self.assertNotIn('None', prompt)
        # Required fields should still be present
        self.assertIn('E11.9', prompt)
        self.assertIn('Metformin', prompt)

    @patch('care_plans.llm.anthropic.Anthropic')
    def test_prompt_includes_system_message(self, mock_anthropic_class):
        """Test API call includes system message"""
        order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis='E11.9',
            medication_name='Metformin',
            patient_records='Records...'
        )

        # Mock the API
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_content_block = MagicMock()
        mock_content_block.text = "Care plan"
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        # Generate care plan
        generate_care_plan(order)

        # Verify system message
        call_args = mock_client.messages.create.call_args
        system_message = call_args.kwargs.get('system')

        self.assertIsNotNone(system_message)
        self.assertIn('pharmacist', system_message.lower())


class LLMCarePlanUniquenessTests(TestCase):
    """Tests for care plan uniqueness constraint"""

    def setUp(self):
        """Set up test data"""
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

    @patch('care_plans.llm.anthropic.Anthropic')
    def test_cannot_create_duplicate_care_plan_for_order(self, mock_anthropic_class):
        """Test OneToOne constraint prevents duplicate care plans"""
        from django.db import IntegrityError, transaction

        # Create first care plan
        CarePlan.objects.create(
            order=self.order,
            care_plan_text='First care plan'
        )

        # Mock the API
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_content_block = MagicMock()
        mock_content_block.text = "Second care plan"
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        # Attempt to generate another care plan for same order
        # Should raise IntegrityError due to OneToOne constraint
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                generate_care_plan(self.order)

        # Should still have only 1 care plan
        self.assertEqual(CarePlan.objects.count(), 1)
