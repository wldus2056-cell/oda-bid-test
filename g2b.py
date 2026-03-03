# g2b.py
import requests

def fetch_all_pages(url: str, params: dict, page_size: int = 999) -> list[dict]:
    all_data = []
    page_no = 1

    while True:
        params["pageNo"] = page_no
        params["numOfRows"] = page_size

        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()

        data = r.json()
        body = data.get("response", {}).get("body", {})
        items = body.get("items") or []

        if not items:
            break

        all_data.extend(items)

        if len(items) < page_size:
            break
        page_no += 1

    return all_data


def fetch_bid_list(api_key: str, start_dt: str, end_dt: str) -> list[dict]:
    url = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"
    params = {
        "inqryDiv": 1,
        "serviceKey": api_key,
        "inqryBgnDt": start_dt,
        "inqryEndDt": end_dt,
        "type": "json",
    }
    return fetch_all_pages(url, params)


def fetch_prebid_list(api_key: str, start_dt: str, end_dt: str) -> list[dict]:
    url = "http://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService/getPublicPrcureThngInfoServc"
    params = {
        "inqryDiv": 1,
        "serviceKey": api_key,
        "inqryBgnDt": start_dt,
        "inqryEndDt": end_dt,
        "type": "json",
    }
    return fetch_all_pages(url, params)