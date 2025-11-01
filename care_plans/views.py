from django.shortcuts import render, redirect, get_object_or_404
from .forms import OrderForm
from .models import Provider, Patient, Order


def create_order(request):
    """
    Handle order creation form submission

    Flow:
    1. GET request: Show empty form
    2. POST request: Validate form
       - If validation errors: Show form with errors
       - If warnings and not acknowledged: Show form with warnings
       - If warnings acknowledged but no longer present: Process normally
       - If valid (and warnings acknowledged): Save order and redirect

    Warning acknowledgment is tied to specific form data. If the user changes
    any fields after seeing warnings, they must re-acknowledge.
    """
    if request.method == 'POST':
        form = OrderForm(request.POST)

        if form.is_valid():
            # Check if form has warnings
            if form.has_warnings():
                # User acknowledged warnings - verify they're for THIS form data
                if request.POST.get('acknowledge_warnings'):
                    # Warnings exist but user acknowledged - allow submission
                    order = save_order(form.cleaned_data)
                    return redirect('order_success', order_id=order.id)
                else:
                    # Warnings exist and not acknowledged - show warnings
                    return render(request, 'care_plans/create_order.html', {
                        'form': form,
                        'warnings': form.get_warnings()
                    })
            else:
                # No warnings - proceed normally
                order = save_order(form.cleaned_data)
                return redirect('order_success', order_id=order.id)
    else:
        form = OrderForm()

    return render(request, 'care_plans/create_order.html', {'form': form})


def order_success(request, order_id):
    """
    Display success page after order creation
    """
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'care_plans/order_success.html', {'order': order})


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
