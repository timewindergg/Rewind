from django.conf import settings
from django.urls import path
from django.conf.urls.static import static
from api import views

urlpatterns = [
    path('get_match_timeline/', views.get_match_timeline),
    path('get_summoner/', views.get_summoner),
    path('get_match_history/', views.get_match_history),
    path('get_user_champion_stats_by_id/', views.get_user_champion_stats_by_id),
    path('get_user_champion_stats_by_name/', views.get_user_champion_stats_by_name),
    path('get_current_match/', views.get_current_match),
    path('get_current_match_details_by_id/', views.get_current_match_details_by_id),
    path('get_current_match_details_by_batch/', views.get_current_match_details_by_batch),
    path('update_summoner/', views.update_summoner),
    path('get_static_data/<region>/', views.get_static_data),
    path('test/', views.tt),
] + static(settings.STATIC_URL, document_root=settings.DEV_STATIC_ROOT)
