from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("ORS_API_KEY")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")