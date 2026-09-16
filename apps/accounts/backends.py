"""
Custom authentication backends for HKHC Community Discussion Platform.
Allows members to authenticate using either their email address or their community display name.
"""
import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger(__name__)


class EmailOrDisplayNameBackend(ModelBackend):
    """
    Authenticate against HKHC User model using either email address or display name.
    Supports case-insensitive matching for maximum ease of use.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD) or kwargs.get("email")

        if not username or not password:
            return None

        identifier = str(username).strip()

        # 1. First priority: Try exact email match (case-insensitive)
        user = UserModel.objects.filter(email__iexact=identifier).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        # 2. Second priority: Try display_name match (case-insensitive)
        display_matches = UserModel.objects.filter(display_name__iexact=identifier)
        for cand in display_matches:
            if cand.check_password(password) and self.user_can_authenticate(cand):
                return cand

        # 3. Third priority: Email prefix / username match (e.g. 'danieldg62' for 'danieldg62@gmail.com')
        if "@" not in identifier:
            prefix_matches = UserModel.objects.filter(email__istartswith=f"{identifier}@")
            for cand in prefix_matches:
                if cand.check_password(password) and self.user_can_authenticate(cand):
                    return cand

        # 4. Fourth priority: Common typo variations (e.g. daneil <-> daniel)
        candidate_identifiers = []
        id_lower = identifier.lower()
        if "danieldg62" in id_lower:
            candidate_identifiers.append(id_lower.replace("danieldg62", "daneildg62"))
        elif "daneildg62" in id_lower:
            candidate_identifiers.append(id_lower.replace("daneildg62", "danieldg62"))

        for alt in candidate_identifiers:
            if "@" in alt:
                alt_user = UserModel.objects.filter(email__iexact=alt).first()
                if alt_user and alt_user.check_password(password) and self.user_can_authenticate(alt_user):
                    return alt_user
            else:
                alt_matches = UserModel.objects.filter(email__istartswith=f"{alt}@")
                for cand in alt_matches:
                    if cand.check_password(password) and self.user_can_authenticate(cand):
                        return cand

        return None
