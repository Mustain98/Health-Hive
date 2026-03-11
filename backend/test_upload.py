import requests

login_res = requests.post(
    "http://127.0.0.1:8000/api/auth/login", 
    data={"username": "admin@example.com", "password": "password"}
)
token = login_res.json().get("access_token")

res = requests.get("http://127.0.0.1:8000/api/admin/meals", headers={"Authorization": f"Bearer {token}"})
meals = res.json()
if "items" in meals and len(meals["items"]) > 0:
    meal_id = meals["items"][0]["id"]
elif type(meals) == list and len(meals) > 0:
    meal_id = meals[0]["id"]
else:
    print(meals)
    exit(1)


print(f"Uploading image for meal {meal_id}...")
with open("../frontend/public/next.svg", "rb") as f:
    upload_res = requests.post(
        f"http://127.0.0.1:8000/api/meals/{meal_id}/upload-image",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("next.svg", f, "image/svg+xml")}
    )

print(upload_res.status_code)
print(upload_res.text)
