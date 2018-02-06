from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from api import views

urlpatterns = [
    url(r'^get_match_timeline/$', views.get_match_timeline),
    url(r'^get_summoner/$', views.get_summoner),
    url(r'^get_match_history/$', views.get_match_history),
    url(r'^get_user_champion_stats_by_id/$', views.get_user_champion_stats_by_id),
    url(r'^get_user_champion_stats_by_name/$', views.get_user_champion_stats_by_name),
    url(r'^get_current_match/$', views.get_current_match),
    url(r'^get_current_match_details_by_id/$', views.get_current_match_details_by_id),
    url(r'^get_current_match_details_by_batch/$', views.get_current_match_details_by_batch),
    url(r'^update_summoner/$', views.update_summoner),
    url(r'^get_static_data/$', views.get_static_data),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
