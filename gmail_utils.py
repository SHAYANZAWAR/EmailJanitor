# gmail_utils.py (update this existing file)
import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from datetime import datetime, timedelta # New import
from typing import Optional

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"] # Keep this scope for marking as read and labels

def get_gmail_service():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        # print("Gmail API service created successfully.") # Keep this silent for agent flow
        return service
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def get_email_body(msg_payload):
    """Extracts the plain text body from a Gmail message payload."""
    if 'parts' in msg_payload:
        for part in msg_payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'body' in part and 'data' in part['body']:
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            elif 'parts' in part:
                body = get_email_body(part)
                if body:
                    return body
    elif 'body' in msg_payload and 'data' in msg_payload['body']:
        return base64.urlsafe_b64decode(msg_payload['body']['data']).decode('utf-8')
    return None

def get_emails(service, query="is:unread", date_after: Optional[str] = None): # Added date_after param
    """Fetches emails from Gmail based on a query.

    Args:
        service: The authenticated Gmail API service object.
        query: Gmail search query string (e.g., "is:unread").
        date_after: Optional date string in YYYY/MM/DD format to filter emails after this date.

    Returns:
        A list of dictionaries, each containing parsed email details.
    """
    emails_data = []
    
    # Construct the full query string
    full_query = query
    if date_after:
        full_query = f"{query} after:{date_after}"

    try:
        results = service.users().messages().list(userId='me', q=full_query).execute()
        messages = results.get('messages', [])

        if not messages:
            # print(f"No messages found for query: '{full_query}'") # Keep this silent for agent flow
            return []

        print(f"Found {len(messages)} messages for query: '{full_query}'")

        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            
            headers = msg['payload']['headers']
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
            sender = next((header['value'] for header in headers if header['name'] == 'From'), 'No Sender')
            date = next((header['value'] for header in headers if header['name'] == 'Date'), 'No Date')

            body = get_email_body(msg['payload'])

            emails_data.append({
                'id': msg['id'],
                'threadId': msg['threadId'],
                'subject': subject,
                'sender': sender,
                'date': date,
                'body': body if body else 'No plain text body found.',
                'raw_payload': msg
            })
        return emails_data

    except HttpError as error:
        print(f"An error occurred while fetching emails: {error}")
        return []

def mark_email_as_read(service, msg_id):
    """Marks an email as read."""
    try:
        service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
        # print(f"Email ID: {msg_id} marked as read.") # Keep silent for agent flow
    except HttpError as error:
        print(f"An error occurred while marking email as read: {error}")

def apply_label_to_email(service, msg_id, label_name):
    """Applies a custom label to an email."""
    try:
        labels = service.users().labels().list(userId='me').execute().get('labels', [])
        label_id = None
        for label in labels:
            if label['name'] == label_name:
                label_id = label['id']
                break
        
        if not label_id:
            print(f"Label '{label_name}' not found. Creating it...")
            created_label = service.users().labels().create(userId='me', body={'name': label_name}).execute()
            label_id = created_label['id']
            print(f"Label '{label_name}' created with ID: {label_id}")

        service.users().messages().modify(userId='me', id=msg_id, body={'addLabelIds': [label_id]}).execute()
        # print(f"Email ID: {msg_id} labeled with '{label_name}'.") # Keep silent for agent flow

    except HttpError as error:
        print(f"An error occurred while applying label: {error}")