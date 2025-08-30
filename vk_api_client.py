import time, requests
from typing import Dict, Any, List
from config import load_config
cfg = load_config()

API = "https://api.vk.com/method/"
VER = "5.199"

def call(method: str, **params) -> Dict[str, Any]:
    base = dict(v=VER, access_token=cfg.VK_SERVICE_TOKEN)
    base.update(params)
    r = requests.post(API+method, data=base, timeout=15)
    data = r.json()
    if 'error' in data:
        raise RuntimeError(data['error'])
    return data['response']

def get_group_posts(count=5) -> List[Dict[str,Any]]:
    owner_id = f"-{cfg.VK_GROUP_ID}"
    resp = call("wall.get", owner_id=owner_id, count=count)
    return resp.get("items", [])

# TODO: add groups.removeUser, groups.ban, wall.getComments, likes.getList wrappers, etc.
