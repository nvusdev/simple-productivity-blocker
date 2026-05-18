import datetime

def is_day_active(schedule, date_context=None):
    if not schedule.get("enabled", False):
        return True
    if schedule.get("always", False):
        return True
    now = date_context or datetime.datetime.now()
    current_day = now.strftime("%A")
    
    # Handle list format (used by GUI)
    days = schedule.get("days", [])
    if isinstance(days, list) and current_day in days:
        return True
        
    # Handle boolean keys format (fallback)
    return schedule.get(current_day, False)

def is_active(config, date_context=None):
    if not config.get("enabled", True):
        return False
        
    schedule = config.get("schedule", {})
    if not schedule.get("enabled", False):
        return False # If schedule is not enabled, the group blocks are turned off

    if schedule.get("persist_all_day", False):
        return is_day_active(schedule, date_context=date_context)

    start_time_str = schedule.get("start_time", schedule.get("start", "00:00"))
    end_time_str = schedule.get("end_time", schedule.get("end", "23:59"))

    try:
        start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
        end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()
        now = date_context or datetime.datetime.now()
        current_time = now.time()

        if start_time <= end_time:
            return is_day_active(schedule, date_context=now) and start_time <= current_time <= end_time

        if current_time >= start_time:
            return is_day_active(schedule, date_context=now)
        if current_time <= end_time:
            yesterday = now - datetime.timedelta(days=1)
            return is_day_active(schedule, date_context=yesterday)
        return False
    except ValueError:
        return False
