# Updated handlers.py to add spoiler support for valentine messages

def handle_valentine_message(message):
    if "valentine" in message.lower():
        return f"||{message}||"  # Spoiler support
    return message
