from google.oauth2.service_account import Credentials
import gspread

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

try:
    creds = Credentials.from_service_account_file("credentials/credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    print("✅ Авторизация прошла успешно!")
except Exception as e:
    print("❌ Ошибка:", e)