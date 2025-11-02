from django.urls import path
from . import views

urlpatterns = [
    path('', views.create_order, name='create_order'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path('update/<int:order_id>/', views.update_care_plan, name='update_care_plan'),
    path('download/<int:order_id>/', views.download_care_plan, name='download_care_plan'),
]
