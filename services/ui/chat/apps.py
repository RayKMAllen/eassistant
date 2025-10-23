from django.apps import AppConfig


class ChatConfig(AppConfig):  # type: ignore
    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "chat"
