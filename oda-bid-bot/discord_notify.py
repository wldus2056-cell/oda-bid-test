# discord_notify.py
import requests

def send_discord(webhook_url: str, content: str | None = None, embeds: list[dict] | None = None):
    payload = {}
    if content:
        payload["content"] = content
    if embeds:
        payload["embeds"] = embeds

    r = requests.post(webhook_url, json=payload, timeout=30)
    r.raise_for_status()