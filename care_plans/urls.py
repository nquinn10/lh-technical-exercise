from django.urls import path
from . import views

urlpatterns = [
    path('', views.create_order, name='create_order'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
]
