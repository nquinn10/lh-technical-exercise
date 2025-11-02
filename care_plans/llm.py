"""
LLM integration for care plan generation using Claude API
"""
import anthropic
from decouple import config
from .models import Order, CarePlan


def generate_care_plan(order):
    """
    Generate care plan for an order using Claude API

    Args:
        order: Order instance with patient and clinical data

    Returns:
        CarePlan instance (saved to database)

    Raises:
        Exception: If API call fails
    """
    client = anthropic.Anthropic(api_key=config('ANTHROPIC_API_KEY'))

    # Build prompt with order data
    user_prompt = build_care_plan_prompt(order)

    # Call Claude API
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.7,
        system=get_system_prompt(),
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    # Extract care plan text from response
    care_plan_text = message.content[0].text

    # Save to database
    care_plan = CarePlan.objects.create(
        order=order,
        care_plan_text=care_plan_text
    )

    return care_plan


def get_system_prompt():
    """
    System prompt defining Claude's role and output format
    """
    return """You are an expert specialty pharmacist creating comprehensive care plans for patients requiring specialty medications.

Your care plans must be:
- Clinically accurate and evidence-based
- Clear and actionable for pharmacy staff and infusion centers
- Focused on patient safety, medication management, and monitoring
- Detailed with specific dosing calculations, monitoring parameters, and intervention protocols

IMPORTANT: Use plain text formatting only. Do NOT use markdown formatting (no **, no #, no formatting symbols).

Format your care plan with these sections:

1. Problem list / Drug therapy problems (DTPs)
   - List all relevant drug therapy problems including efficacy needs, safety risks, drug interactions, and patient education gaps
   - Number each problem clearly

2. Goals (SMART)
   - Primary clinical goal (efficacy)
   - Safety goals (specific adverse events to prevent)
   - Process goals (completion of therapy, monitoring documentation)

3. Pharmacist interventions / plan
   - Dosing & Administration (with calculations)
   - Premedication protocols
   - Infusion rates & titration protocols
   - Hydration & organ protection strategies
   - Risk mitigation for specific adverse events
   - Concomitant medication management
   - Monitoring during administration (with frequencies)
   - Adverse event management protocols (mild/moderate/severe)
   - Documentation & communication requirements

4. Monitoring plan & lab schedule
   - Pre-treatment baseline assessments
   - During-treatment monitoring (vitals, labs, symptoms)
   - Post-treatment follow-up timing and parameters

Write in a professional, clinical tone. Be specific about:
- Exact doses with calculations (e.g., "2.0 g/kg total for 72 kg = 144 g")
- Vital sign monitoring frequencies (e.g., "q15 min for first hour")
- Lab monitoring timing (e.g., "within 3-7 days post-completion")
- Specific adverse event protocols with escalation criteria

Use clinical abbreviations appropriately (e.g., PO, q6h, SCr, eGFR, FVC)."""


def build_care_plan_prompt(order):
    """
    Build user prompt with all order data

    Args:
        order: Order instance

    Returns:
        str: Formatted prompt with patient data
    """
    patient = order.patient
    provider = order.provider

    prompt = f"""Please generate a comprehensive pharmacist care plan for the following patient.

PATIENT & PROVIDER INFORMATION:
- Patient: {patient.first_name} {patient.last_name}
- MRN: {patient.mrn}
- Ordering Provider: {provider.name} (NPI: {provider.npi})
- Primary Diagnosis: {order.primary_diagnosis}
- Medication Prescribed: {order.medication_name}"""

    # Add optional fields if present
    if order.additional_diagnoses:
        prompt += f"\n- Additional Diagnoses: {order.additional_diagnoses}"

    if order.medication_history:
        prompt += f"\n- Medication History: {order.medication_history}"

    prompt += f"""

DETAILED PATIENT MEDICAL RECORDS:
{order.patient_records}

---

Based on the patient medical records above, generate a complete pharmacist care plan following the format specified in your instructions. Focus on:
- Identifying all drug therapy problems relevant to this patient and medication
- Creating specific, measurable goals
- Providing detailed, actionable interventions with exact dosing calculations and monitoring frequencies
- Establishing a comprehensive monitoring schedule with specific timing

The patient medical records contain the most important clinical context - use them as your primary source for clinical decision-making."""

    return prompt
