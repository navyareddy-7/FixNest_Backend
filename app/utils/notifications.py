import httpx
from typing import Dict, Any, List

async def send_expo_push_notification(push_token: str, title: str, body: str, data: Dict[str, Any] = None):
    """
    Sends a push notification using the Expo Push API.
    Does not require EAS configuration on the backend side; works on any valid Expo push token.
    """
    if not push_token or not push_token.startswith("ExponentPushToken"):
        return False
        
    url = "https://exp.host/--/api/v2/push/send"
    payload = {
        "to": push_token,
        "title": title,
        "body": body,
        "sound": "default",
        "data": data or {}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=5.0)
            if response.status_code == 200:
                result = response.json()
                # Check for errors in the individual notification delivery
                if "data" in result:
                    return True
            return False
    except Exception as e:
        print(f"Error sending Expo push notification: {e}")
        return False
