import datetime

def is_day_active(schedule):
    if not schedule.get("enabled", False):
        return True
    now = datetime.datetime.now()
    current_day = now.strftime("%A")
    return current_day in schedule.get("days", [])

def is_active(config):
    if not config.get("enabled", True):
        return False
        
    schedule = config.get("schedule", {})
    if not schedule.get("enabled", False):
        return True # If schedule is not enabled, blocks are always active

    if not is_day_active(schedule):
        return False

    if schedule.get("persist_all_day", False):
        return True

    start_time_str = schedule.get("start_time", "00:00")
    end_time_str = schedule.get("end_time", "23:59")

    try:
        start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
        end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()
        current_time = datetime.datetime.now().time()

        if start_time <= end_time:
            return start_time <= current_time <= end_time
        return current_time >= start_time or current_time <= end_time
    except ValueError:
        return False
