from django.contrib import admin
from .models import Bookmark, Discussion, Reply, Topic


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_archived", "created_at")
    list_editable = ("order", "is_archived")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "author", "is_anonymous", "status", "is_deleted", "views_count", "created_at")
    list_filter = ("topic", "is_anonymous", "status", "is_deleted")
    search_fields = ("title", "content", "author__email", "author__display_name")
    raw_id_fields = ("author", "deleted_by")


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ("id", "discussion", "author", "parent", "is_anonymous", "status", "is_deleted", "created_at")
    list_filter = ("is_anonymous", "status", "is_deleted")
    search_fields = ("content", "author__email", "author__display_name")
    raw_id_fields = ("discussion", "parent", "author", "deleted_by")


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "discussion", "created_at")
    raw_id_fields = ("user", "discussion")
