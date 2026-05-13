"""Run this once locally to get your Google refresh token."""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=8080, open_browser=False)

print("\n=== COPY THIS REFRESH TOKEN ===")
print(creds.refresh_token)
print("================================\n")
