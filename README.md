# Care Plan Generator

A Django web application that enables pharmacists to generate AI-powered care plans for patients. Built for Lamar Health's technical assessment.

## Overview

This application streamlines the care plan creation process by:
- Capturing patient demographics, diagnoses, and medical history
- Detecting potential duplicate entries before submission
- Generating comprehensive care plans using Claude AI
- Enabling pharmacist review and editing before finalization
- Exporting data for pharmaceutical company reporting

**Tech Stack:** Django 5.1, SQLite, Anthropic Claude API, Bootstrap 5

## Features

- **Smart Form Validation**: Real-time validation for MRN (6 digits) and NPI (10 digits) with duplicate detection
- **Warning System**: Alerts for potential duplicates (patients, providers, orders) with acknowledgment workflow
- **AI Care Plan Generation**: Claude API integration generates detailed care plans from patient records
- **Pharmacist Review**: Edit and refine AI-generated content before finalization
- **Order Management**: View order history and download individual care plans
- **CSV Export**: Bulk export for pharma company reporting requirements

## Quick Start

### Prerequisites
- Python 3.11+
- Anthropic API key

### Installation

```bash
# Clone repository
git clone <repository-url>
cd lh-technical-exercise

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

Visit http://localhost:8000/orders/create/

### Running Tests

```bash
python manage.py test
```

All 82 tests should pass, covering:
- Form validation and duplicate detection (29 tests)
- Model relationships and constraints (20 tests)
- View logic and workflows (20 tests)
- LLM integration and error handling (13 tests)

## Application Structure

```
care_plans/
├── models.py          # Patient, Provider, Order, CarePlan models
├── forms.py           # OrderForm with validation and warning logic
├── views.py           # Request handlers for order creation, review, export
├── llm.py             # Claude API integration
├── templates/         # HTML templates
└── tests/             # Comprehensive test suite
```

## Key Design Decisions

**Warnings vs Hard Blocks**: Duplicate detection shows warnings rather than preventing submission. Allows pharmacists to proceed with legitimate duplicates (e.g., new medication for existing patient) while maintaining awareness.

**MRN + Name Duplicate Detection**: When an MRN already exists in the system, the behavior differs based on the submitted name:
- Same MRN + Same name → Warning (potential duplicate order for existing patient)
- Same MRN + Different name → Warning (data mismatch - existing patient record will be used, not the submitted name)

This prevents duplicate patient records while alerting users to potential data entry errors.

**Clinical Data in Orders**: Patient diagnoses and records are stored in the Order table (point-in-time snapshot) rather than the Patient table. Orders are transactional, not a longitudinal EMR.

**OneToOne CarePlan Relationship**: Each order generates exactly one care plan, enforced at the database level to prevent duplicate generation.

**Hybrid Validation**: Client-side validation for instant feedback (format checks), server-side validation for security and duplicate detection.

## API Integration

Uses Anthropic's **Claude 3.5 Sonnet** (claude-3-5-sonnet-20241022). While Claude Opus 4.5 offers enhanced capabilities, Sonnet provides excellent quality for care plan generation at better speed and cost efficiency - appropriate for a prototype demonstrating core functionality.

System prompt instructs Claude to act as a clinical pharmacist consultant, generating structured care plans with medication reviews, monitoring plans, and patient education.

Error handling: Connection failures, rate limits, authentication errors, invalid responses.

## Questions for Stakeholder Discussion

**Access & Permissions:**
- What level of admin privileges will be available to pharmacists vs supervisors?
- Should certain actions (e.g., patient data corrections) require elevated permissions?

**Error Correction Workflow:**
- If mistakes in submitted orders are discovered, what is the desired correction flow?
- Should we allow order editing, or only cancellation + recreation?

**Validation Rules:**
- Are we blocking anything we shouldn't? (Currently: invalid format, missing required fields)
- Are there duplicates we should hard-block instead of warn? (Currently: all duplicates are warnings)

**Audit & Compliance:**
- What audit trail is required when warnings are overridden?
- Do we need to log who acknowledged which warnings and when?
- Are there regulatory requirements for care plan version history?

**Scope Validation:**
- Have we over-engineered anything that isn't a concern in practice?
- What features are "nice to have" vs actually needed for daily workflow?

## Potential Improvements

**Based on prototype experience:**
- Warning acknowledgment history (track what users acknowledged and when)
- Search/filter functionality on orders list page
- Patient and provider lookup before creating order (avoid typos)
- More robust error handling for edge cases in care plan generation

## Deployment

[Live deployment information will be added here]

---

Built with Django • Powered by Claude AI
