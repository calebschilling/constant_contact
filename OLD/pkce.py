# run anywhere (e.g., local Python REPL)
import os, base64, hashlib
verifier = base64.urlsafe_b64encode(os.urandom(64)).rstrip(b'=').decode()
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
print("CODE_VERIFIER =", verifier)
print("CODE_CHALLENGE =", challenge)
