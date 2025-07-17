from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from employee.models import Employee
import logging

logger = logging.getLogger(__name__)  # Set up a logger

@receiver(post_save, sender=User)
def create_employee_for_superuser(sender, instance, created, **kwargs):
    if created and instance.is_superuser:
        try:    
            # Ensure employee doesn't already exist for this superuser
            if not Employee.objects.filter(employee_user_id=instance).exists():
                Employee.objects.create(
                    employee_user_id=instance,
                    employee_first_name=instance.first_name or instance.username,
                    employee_last_name=instance.last_name or '',
                    email=instance.email or f"{instance.username}@example.com",
                )
                logger.info(f"Employee record created for superuser: {instance.username}")
        except Exception as e:
            logger.error(f"[Signal Error] Failed to create Employee for superuser '{instance.username}': {e}")
