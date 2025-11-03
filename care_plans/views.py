from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .forms import OrderForm
from .models import Provider, Patient, Order, CarePlan
from .llm import generate_care_plan
import logging
import csv
from datetime import datetime

logger = logging.getLogger(__name__)


def create_order(request):
    """
    Handle order creation form submission with duplicate warnings

    Flow:
    1. GET request: Show empty form
    2. POST request: Validate form
       - If validation errors: Show form with errors
       - If warnings and not acknowledged: Show warnings
       - If warnings and acknowledged: Save order
       - If no warnings: Save order
    """
    if request.method == 'POST':
        form = OrderForm(request.POST)

        if form.is_valid():
            if form.has_warnings():
                # Check if user acknowledged warnings
                if request.POST.get('acknowledge_warnings'):
                    # User acknowledged - proceed
                    order = save_order(form.cleaned_data)
                    logger.info(f"Order created with warnings acknowledged: {order.id}")
                    return redirect('order_success', order_id=order.id)
                else:
                    # Show warnings for acknowledgment
                    logger.info("Warnings detected - displaying to user")
                    return render(request, 'care_plans/create_order.html', {
                        'form': form,
                        'warnings': form.get_warnings()
                    })
            else:
                # No warnings - proceed normally
                order = save_order(form.cleaned_data)
                logger.info(f"Order created without warnings: {order.id}")
                return redirect('order_success', order_id=order.id)
    else:
        # GET request - show empty form
        form = OrderForm()

    return render(request, 'care_plans/create_order.html', {'form': form})


def order_success(request, order_id):
    """
    Display success page after order creation

    Attempts to generate care plan via Claude API. If care plan already exists
    or API fails, shows order details with appropriate messaging.
    """
    order = get_object_or_404(Order, id=order_id)
    care_plan = None
    error_message = None

    # Check if care plan already exists
    try:
        care_plan = order.care_plan
    except CarePlan.DoesNotExist:
        # Generate new care plan
        try:
            care_plan = generate_care_plan(order)
            logger.info(f"Successfully generated care plan for order {order_id}")
        except Exception as e:
            # Log error but don't crash - order is already saved
            logger.error(f"Failed to generate care plan for order {order_id}: {str(e)}")
            error_message = "Unable to generate care plan at this time. The order has been saved successfully. You can retry generation later."

    return render(request, 'care_plans/order_success.html', {
        'order': order,
        'care_plan': care_plan,
        'error_message': error_message
    })


def save_order(cleaned_data):
    """
    Create Order with Patient and Provider

    Gets or creates Patient and Provider, then creates the Order.
    """
    patient, _ = Patient.objects.get_or_create(
        mrn=cleaned_data['mrn'],
        defaults={
            'first_name': cleaned_data['patient_first_name'],
            'last_name': cleaned_data['patient_last_name']
        }
    )

    provider, _ = Provider.objects.get_or_create(
        npi=cleaned_data['provider_npi'],
        defaults={
            'name': cleaned_data['provider_name']
        }
    )

    order = Order.objects.create(
        patient=patient,
        provider=provider,
        primary_diagnosis=cleaned_data['primary_diagnosis'],
        medication_name=cleaned_data['medication_name'],
        additional_diagnoses=cleaned_data.get('additional_diagnoses', ''),
        medication_history=cleaned_data.get('medication_history', ''),
        patient_records=cleaned_data['patient_records']
    )

    return order


def update_care_plan(request, order_id):
    """
    Update care plan text after pharmacist review/edits

    Allows pharmacists to modify AI-generated care plans before finalizing.
    """
    if request.method != 'POST':
        return redirect('order_success', order_id=order_id)

    order = get_object_or_404(Order, id=order_id)
    care_plan = get_object_or_404(CarePlan, order=order)

    # Update care plan text with edited content
    updated_text = request.POST.get('care_plan_text', '')
    if updated_text:
        care_plan.care_plan_text = updated_text
        care_plan.save()
        logger.info(f"Care plan updated for order {order_id}")

    # Redirect back to success page with success message
    from django.contrib import messages
    messages.success(request, 'Care plan changes saved successfully!')
    return redirect('order_success', order_id=order_id)


def download_care_plan(request, order_id):
    """
    Download care plan as text file

    Filename format: care_plan_MRN{mrn}_{timestamp}.txt
    """
    order = get_object_or_404(Order, id=order_id)
    care_plan = get_object_or_404(CarePlan, order=order)

    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"care_plan_MRN{order.patient.mrn}_{timestamp}.txt"

    # Create response with text file
    response = HttpResponse(care_plan.care_plan_text, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


def orders_list(request):
    """
    Display all orders in a table format

    Shows Order ID, Date, Patient, MRN, Medication, and Provider.
    Orders are sorted by most recent first.
    """
    orders = Order.objects.select_related('patient', 'provider').all().order_by('-created_at')

    return render(request, 'care_plans/orders_list.html', {
        'orders': orders
    })


def export_csv(request):
    """
    Export all orders to CSV for pharma reporting

    CSV includes: order_id, order_date, patient_mrn, patient_first_name,
    patient_last_name, provider_name, provider_npi, primary_diagnosis,
    medication_name, additional_diagnoses, medication_history, care_plan_text
    """
    # Create response with CSV content type
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="orders_export_{timestamp}.csv"'

    # Create CSV writer
    writer = csv.writer(response)

    # Write header row
    writer.writerow([
        'Order ID',
        'Order Date',
        'Patient MRN',
        'Patient First Name',
        'Patient Last Name',
        'Provider Name',
        'Provider NPI',
        'Primary Diagnosis',
        'Medication Name',
        'Additional Diagnoses',
        'Medication History',
        'Care Plan Text'
    ])

    # Write data rows
    orders = Order.objects.select_related('patient', 'provider').all().order_by('-created_at')

    for order in orders:
        # Get care plan text if it exists
        try:
            care_plan_text = order.care_plan.care_plan_text
        except CarePlan.DoesNotExist:
            care_plan_text = ''

        writer.writerow([
            order.id,
            order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            order.patient.mrn,
            order.patient.first_name,
            order.patient.last_name,
            order.provider.name,
            order.provider.npi,
            order.primary_diagnosis,
            order.medication_name,
            order.additional_diagnoses,
            order.medication_history,
            care_plan_text
        ])

    logger.info(f"CSV export generated with {orders.count()} orders")
    return response
