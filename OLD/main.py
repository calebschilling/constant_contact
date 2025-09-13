import os, time, json, requests
from dotenv import load_dotenv

load_dotenv()  # loads CC_CLIENT_ID and CC_REFRESH_TOKEN from .env

CLIENT_ID = os.getenv("CC_CLIENT_ID")
REFRESH_TOKEN = os.getenv("CC_REFRESH_TOKEN")

_access_token = None
_expiry = 0

def get_access_token():
    global _access_token, _expiry, REFRESH_TOKEN
    if _access_token and time.time() < _expiry:
        return _access_token

    r = requests.post(
        "https://authz.constantcontact.com/oauth2/default/v1/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": REFRESH_TOKEN,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    _access_token = data["access_token"]
    _expiry = time.time() + data.get("expires_in", 3600) * 0.9
    REFRESH_TOKEN = data["refresh_token"]

    # Update .env with the latest refresh token
    lines = []
    with open(".env", "r") as f:
        lines = f.readlines()
    with open(".env", "w") as f:
        for line in lines:
            if line.startswith("CC_REFRESH_TOKEN="):
                f.write(f"CC_REFRESH_TOKEN={REFRESH_TOKEN}\n")
            else:
                f.write(line)

    return _access_token

def get_contact_lists():
    token = get_access_token()
    resp = requests.get(
        "https://api.cc.email/v3/contact_lists",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    if __name__ == "__main__":
    lists = get_contact_lists()

    # Pretty-print to terminal
    print(json.dumps(lists, indent=2))

    # Save to a JSON file
    with open("audience_lists.json", "w", encoding="utf-8") as f:
        json.dump(lists, f, indent=2)

    print("\n✅ Saved lists to audience_lists.json")
