import urllib.request
import urllib.error
import urllib.parse
import json

base = "http://127.0.0.1:8000/api"

# 1. register
try:
    req = urllib.request.Request(f"{base}/auth/register", method="POST", data=json.dumps({
        "username": "test_app_fail_user",
        "email": "test_app_fail@test.com",
        "password": "password",
        "full_name": "Test Fail"
    }).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)
except Exception: pass

# 2. login
try:
    req = urllib.request.Request(f"{base}/auth/login", method="POST", data=urllib.parse.urlencode({
        "username": "test_app_fail_user",
        "password": "password"
    }).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
    res = urllib.request.urlopen(req)
    token = json.loads(res.read())["access_token"]
except Exception as e:
    print("Login failed:", e)
    exit(1)

# 3. apply
try:
    req = urllib.request.Request(f"{base}/consultants/apply", method="POST", data=json.dumps({
        "display_name": "Dr. Test Fail",
        "consultant_type": "clinical",
        "highest_qualification": "MD",
        "graduation_institution": "Harvard",
        "registration_body": "AMA",
        "registration_number": "12345"
    }).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    res = urllib.request.urlopen(req)
    print("Success:", res.read())
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print(e.read().decode())
except Exception as e:
    print("Other Error:", e)

