# payroll/utils/attendance_utils.py
from datetime import timedelta
from attendance.models import Attendance
def get_attendance_days(employee, start_date, end_date):
    """
    Count total present days by checking attendance_clock_in is not null.
    """
    if not employee or not start_date or not end_date:
        return 0
    return Attendance.objects.filter(
        employee_id=employee,
        attendance_date__range=[start_date, end_date],
        attendance_clock_in__isnull=False
    ).count()
def get_weekend_work_days(employee, start_date, end_date):
    """
    Count number of Saturdays and Sundays worked (clocked in).
    """
    if not employee or not start_date or not end_date:
        return 0
    weekend_workdays = 0
    all_attendance = Attendance.objects.filter(
        employee_id=employee,
        attendance_date__range=[start_date, end_date],
        attendance_clock_in__isnull=False
    )
    for record in all_attendance:
        weekday = record.attendance_date.weekday()  # 5 = Saturday, 6 = Sunday
        if weekday in [5, 6]:
            weekend_workdays += 1
    return weekend_workdays
def get_absent_days(employee, start_date, end_date):
    """
    Returns the number of absent days for an employee in a given date range.
    Option A: Counts records where there is an Attendance row but no clock-in.
    Option B: Calculates total calendar days minus present days (incl. weekends).
    """
    if not employee or not start_date or not end_date:
        return 0
    # OPTION A: Count any Attendance records with no clock-in
    absent_via_record = Attendance.objects.filter(
        employee_id=employee,
        attendance_date__range=[start_date, end_date],
        attendance_clock_in__isnull=True
    ).count()
    # OPTION B: Total calendar days in range minus present days
    total_days = (end_date - start_date).days + 1
    present_days = get_attendance_days(employee, start_date, end_date)
    absent_via_calc = total_days - present_days
    # Choose whichever makes sense in your workflow.
    # If every absent day has a record, use absent_via_record.
    # Otherwise, use absent_via_calc.
    return absent_via_calc  # or return absent_via_calc