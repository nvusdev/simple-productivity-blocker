import datetime
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from core.scheduler import is_active

def test_scheduler_cases():
    print("--- Verifying Scheduler Edge Cases ---")
    
    # 1. Normal daytime range
    config = {
        "enabled": True,
        "schedule": {
            "enabled": True,
            "start": "09:00",
            "end": "17:00",
            "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        }
    }
    
    monday_noon = datetime.datetime(2026, 5, 11, 12, 0) # Monday
    monday_night = datetime.datetime(2026, 5, 11, 20, 0)
    sunday_noon = datetime.datetime(2026, 5, 10, 12, 0) # Sunday
    
    assert is_active(config, date_context=monday_noon) == True
    assert is_active(config, date_context=monday_night) == False
    assert is_active(config, date_context=sunday_noon) == False
    print("Pass: Normal daytime range")

    # 2. Midnight crossing (22:00 to 04:00)
    config_midnight = {
        "enabled": True,
        "schedule": {
            "enabled": True,
            "start": "22:00",
            "end": "04:00",
            "days": ["Monday"] # Active Monday night into Tuesday morning
        }
    }
    
    mon_23 = datetime.datetime(2026, 5, 11, 23, 0)
    tue_02 = datetime.datetime(2026, 5, 12, 2, 0)
    tue_05 = datetime.datetime(2026, 5, 12, 5, 0)
    mon_21 = datetime.datetime(2026, 5, 11, 21, 0)
    
    assert is_active(config_midnight, date_context=mon_23) == True
    assert is_active(config_midnight, date_context=tue_02) == True
    assert is_active(config_midnight, date_context=tue_05) == False
    assert is_active(config_midnight, date_context=mon_21) == False
    print("Pass: Midnight crossing")

    # 3. Always active
    config_always = {
        "enabled": True,
        "schedule": {
            "enabled": True,
            "always": True
        }
    }
    assert is_active(config_always) == True
    print("Pass: Always active")

    # 4. Disabled group
    config_disabled = {
        "enabled": False,
        "schedule": {"enabled": True, "always": True}
    }
    assert is_active(config_disabled) == False
    print("Pass: Disabled group")

    # 5. Persist all day
    config_persist = {
        "enabled": True,
        "schedule": {
            "enabled": True,
            "persist_all_day": True,
            "days": ["Monday"]
        }
    }
    assert is_active(config_persist, date_context=monday_noon) == True
    assert is_active(config_persist, date_context=monday_night) == True
    assert is_active(config_persist, date_context=sunday_noon) == False
    print("Pass: Persist all day")

    print("--- ALL SCHEDULER CASES PASSED ---")

if __name__ == "__main__":
    test_scheduler_cases()
