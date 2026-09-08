from django import template

register = template.Library()


@register.filter(name="display_author")
def display_author(obj, viewing_user):
    """Safely return display author string according to anonymity rules."""
    if hasattr(obj, "get_display_author_for"):
        return obj.get_display_author_for(viewing_user)
    return ""


@register.filter(name="is_author_visible")
def is_author_visible(obj, viewing_user):
    """Check if author's public identity is visible to the viewing user."""
    if hasattr(obj, "is_author_visible_for"):
        return obj.is_author_visible_for(viewing_user)
    return False


@register.filter(name="can_reply")
def can_reply(discussion, user):
    """Check if user is authorized to reply to discussion."""
    if hasattr(discussion, "can_user_reply"):
        return discussion.can_user_reply(user)
    return False


@register.filter(name="can_edit")
def can_edit(obj, user):
    """Check if user is authorized to edit discussion or reply."""
    if hasattr(obj, "can_user_edit"):
        return obj.can_user_edit(user)
    return False


@register.filter(name="can_delete")
def can_delete(obj, user):
    """Check if user is authorized to delete discussion or reply."""
    if hasattr(obj, "can_user_delete"):
        return obj.can_user_delete(user)
    return False
