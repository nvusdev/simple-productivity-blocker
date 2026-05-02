import datetime

def is_active(config):
    schedule = config.get("schedule", {})
    if not schedule.get("enabled", False):
        return True # If schedule is not enabled, blocks are always active
        
    if schedule.get("persist_all_day", False):
        return True
        
    now = datetime.datetime.now()
    current_day = now.strftime("%A")
    
    if current_day not in schedule.get("days", []):
        return False
        
    start_time_str = schedule.get("start_time", "00:00")
    end_time_str = schedule.get("end_time", "23:59")
    
    try:
        start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
        end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()
        current_time = now.time()
        
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:
            return current_time >= start_time or current_time <= end_time
    except ValueError:
        return False
