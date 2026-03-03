# g2b.py
import requests
from urllib.parse import quote

def fetch_all_pages(url: str, params: dict) -> list[dict]:
    all_items = []
    page = 1
    while True:
        params["pageNo"] = page
        params["numOfRows"] = 999
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        items = data.get("response", {}).get("body", {}).get("items") or []
        if not items:
            break
        all_items.extend(items)
        if len(items) < 999:
            break
        page += 1
    return all_items

def fetch_bid_list(api_key: str, start_dt: str, end_dt: str) -> list[dict]:
    url = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"
    params = {
        "inqryDiv": 1,
        "serviceKey": quote(api_key.strip(), safe=""),
        "inqryBgnDt": start_dt,
        "inqryEndDt": end_dt,
        "type": "json",
    }
    return fetch_all_pages(url, params)

def fetch_prebid_list(api_key: str, start_dt: str, end_dt: str) -> list[dict]:
    url = "http://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService/getPublicPrcureThngInfoServc"
    params = {
        "inqryDiv": 1,
        "serviceKey": quote(api_key.strip(), safe=""),
        "inqryBgnDt": start_dt,
        "inqryEndDt": end_dt,
        "type": "json",
    }
    return fetch_all_pages(url, params)
