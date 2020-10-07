from typing import Optional

def is_true(value: 'Optional[str]') -> bool:
    if value is None:
        return False

    return value.lower() in ['1', 'yes', 'true', 'y', 't']
