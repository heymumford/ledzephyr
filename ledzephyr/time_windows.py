"""Time window parsing functionality."""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo


def parse_windows(windows: List[str], tz: ZoneInfo, current_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Parse time windows like '24h' and '7d' into time ranges.
    
    Args:
        windows: List of time window strings (e.g., ['24h', '7d'])
        tz: Timezone info for the resulting datetime objects
        current_time: Current time to use as reference (for testing)
        
    Returns:
        List of dictionaries with 'start', 'end', and 'duration' keys
        
    Raises:
        ValueError: If window format is invalid or unsupported
    """
    if not windows:
        return []
    
    result = []
    now = current_time if current_time else datetime.now(tz)
    
    for window in windows:
        # Parse the time window format (e.g., "24h", "7d")
        match = re.match(r'^(\d+)([a-zA-Z]+)$', window)
        if not match:
            raise ValueError(f"Invalid time window format: {window}")
        
        amount, unit = match.groups()
        amount = int(amount)
        
        # Calculate the time delta based on unit
        if unit == 'h':
            delta = timedelta(hours=amount)
        elif unit == 'd':
            delta = timedelta(days=amount)
        else:
            raise ValueError(f"Unsupported time unit: {unit}")
        
        start = now - delta
        end = now
        
        result.append({
            'start': start,
            'end': end,
            'duration': window
        })
    
    return result