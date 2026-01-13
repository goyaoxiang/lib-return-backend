from datetime import datetime
import pytz

# GMT+8 timezone (Malaysia/Singapore)
GMT8 = pytz.timezone('Asia/Kuala_Lumpur')

def now_gmt8() -> datetime:
    """Get current datetime in GMT+8 timezone."""
    return datetime.now(GMT8)
