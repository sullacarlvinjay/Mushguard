"""URL configuration for the core app."""

from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('login/', views.VerifiedLoginView.as_view(), name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('verify/<uuid:token>/', views.verify_email, name='verify_email'),
    path('account/', views.account_view, name='account'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('analyze/', views.home, name='analyze'),
    path('predict/', views.predict_mushroom, name='predict'),
    path('report/', views.report_unknown, name='report_unknown'),
    path('admin-panel/', views.admin_manage_reports, name='admin_manage_reports'),
    path('mushroom/<str:mushroom_name>/', views.mushroom_detail, name='mushroom_detail'),
    path('advertisements/', views.advertisements, name='advertisements'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap_xml'),
    path('sw.js', views.service_worker, name='service_worker'),
]