import secrets
import string

import base64
from os import getenv
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from functools import wraps
from flask import jsonify


def get_gmail_service():
    """Authenticates using environment variables and returns the Gmail service client."""
    creds = Credentials(
        token=None,
        refresh_token=getenv("GMAIL_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=getenv("GMAIL_CLIENT_ID"),
        client_secret=getenv("GMAIL_CLIENT_SECRET")
    )

    if not creds.valid:
        creds.refresh(Request())

    return build('gmail', 'v1', credentials=creds)


def send_email(subject, recipient, text_content, html_content=None):
    try:
        service = get_gmail_service()
        
        message = EmailMessage()
        message.set_content(text_content)
        if html_content:
            message.add_alternative(html_content, subtype="html")
        
        message['To'] = recipient
        message['From'] = 'me'
        message['Subject'] = subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        send_message = service.users().messages().send(userId="me", body=create_message).execute()
        
    except Exception as e:
        raise e
