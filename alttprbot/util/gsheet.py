from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import config

def get_creds():
    return ServiceAccountCredentials.from_json_keyfile_dict(
        config.GSHEET_API_OAUTH,
        [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
    )

drive_service = build('drive', 'v3', credentials=get_creds())