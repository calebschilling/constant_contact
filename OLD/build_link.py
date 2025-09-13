import urllib.parse
client_id = "14140efd-c5c5-4240-996f-e58fc1089ee0"
redirect = "http://localhost:3000/oauth/callback"
challenge = "D0wy8HM9zFhvwBTgP-CpOwmCh9lBG1P5PGmN6M18Elo"
base = "https://authz.constantcontact.com/oauth2/default/v1/authorize"
qs = urllib.parse.urlencode({
    "client_id": client_id,
    "redirect_uri": redirect,
    "response_type": "code",
    "scope": "contact_data offline_access",
    "code_challenge": challenge,
    "code_challenge_method": "S256",
    "state": "xyz123",
})
print(f"{base}?{qs}")
