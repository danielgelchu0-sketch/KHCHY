from django.urls import path
from . import views

app_name = "discussions"

urlpatterns = [
    path("", views.TopicListView.as_view(), name="topic_list"),
    path("topic/<slug:slug>/", views.TopicDetailView.as_view(), name="topic_detail"),
    path("topic/<slug:topic_slug>/ask/", views.DiscussionCreateView.as_view(), name="discussion_create"),
    path("topic/<slug:topic_slug>/<int:pk>/", views.DiscussionDetailView.as_view(), name="discussion_detail"),
    path("topic/<slug:topic_slug>/<int:pk>/reply/", views.ReplyCreateView.as_view(), name="reply_create"),
    path("topic/<slug:topic_slug>/<int:pk>/edit/", views.DiscussionEditView.as_view(), name="discussion_edit"),
    path("topic/<slug:topic_slug>/<int:pk>/delete/", views.DiscussionDeleteView.as_view(), name="discussion_delete"),
    path("reply/<int:pk>/edit/", views.ReplyEditView.as_view(), name="reply_edit"),
    path("reply/<int:pk>/delete/", views.ReplyDeleteView.as_view(), name="reply_delete"),
    path("discussion/<int:pk>/bookmark/", views.BookmarkToggleView.as_view(), name="bookmark_toggle"),
]
