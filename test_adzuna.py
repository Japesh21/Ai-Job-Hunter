import requests
from config.settings import ADZUNA_APP_ID, ADZUNA_APP_KEY

url = "https://api.adzuna.com/v1/api/jobs/in/search/1"

params = {
    "app_id": ADZUNA_APP_ID,
    "app_key": ADZUNA_APP_KEY,
    "what": "software engineer",
    "results_per_page": 5,
}

response = requests.get(url, params=params, timeout=20)

print("Status:", response.status_code)

if response.status_code == 200:
    data = response.json()

    print("Jobs Found:", len(data.get("results", [])))

    if data.get("results"):
        first = data["results"][0]

        print("Title:", first.get("title"))
        print("Company:", first.get("company", {}).get("display_name"))
        print("Location:", first.get("location", {}).get("display_name"))
else:
    print(response.text)