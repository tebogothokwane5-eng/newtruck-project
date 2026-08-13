"""
Push notification utility using Firebase Cloud Messaging (FCM).

Works for both Android and iOS clients, since FCM is a unified service
for both platforms.

Looks for the Firebase service account credentials in, in order:
  1. /etc/secrets/firebase-service-account.json  (Render Secret File, production)
  2. backend/secrets/firebase-service-account.json  (local dev)

If neither exists, push notifications are silently disabled (logged, not
raised) so the app keeps working even before Firebase is fully configured.
"""

import os
import firebase_admin
from firebase_admin import credentials, messaging

_CRED_PATHS = [
    "/etc/secrets/firebase-service-account.json",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "secrets",
        "firebase-service-account.json"
    ),
]

_firebase_app = None
_init_attempted = False


def _get_firebase_app():
    global _firebase_app, _init_attempted

    if _firebase_app is not None:
        return _firebase_app

    if _init_attempted:
        return None

    _init_attempted = True

    for path in _CRED_PATHS:
        if os.path.exists(path):
            try:
                cred = credentials.Certificate(path)
                _firebase_app = firebase_admin.initialize_app(cred)
                print(f"[FIREBASE] Initialized using credentials at {path}")
                return _firebase_app
            except Exception as e:
                print(f"[FIREBASE ERROR] Failed to initialize with {path}: {e}")
                return None

    print("[FIREBASE] No service account file found - push notifications disabled")
    return None


def send_push_notification(token: str, title: str, body: str, data: dict = None) -> bool:
    """
    Sends a push notification to a single device token.
    Returns True on success, False otherwise. Never raises.
    """

    if not token:
        return False

    app = _get_firebase_app()
    if not app:
        return False

    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
        )
        messaging.send(message, app=app)
        print(f"[PUSH SENT] -> {token[:12]}...")
        return True

    except Exception as e:
        print(f"[PUSH ERROR] {e}")
        return False
