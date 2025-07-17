"""
apps.py
"""


from django.apps import AppConfig

class EmployeeConfig(AppConfig):
    """
    AppConfig for the 'employee' app.
    This connects signals when the app is ready.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "employee"

    def ready(self):
        import employee.signals