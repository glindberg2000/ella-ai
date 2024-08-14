# File: memgpt_email_router.py
import os
import logging
import json
from typing import Any, Optional, Dict, List, Union
from dotenv import load_dotenv
from memgpt.client.client import RESTClient, UserMessageResponse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import html
import re
import asyncio
import base64
from google_service_manager import google_service_manager

# Load environment variables
load_dotenv()

# Constants
BASE_URL = os.getenv("MEMGPT_API_URL", "http://localhost:8080")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemGPTEmailRouter:
    """
    A class for handling email generation and sending using MemGPT and Gmail API.
    
    This class is responsible for generating email content using MemGPT and sending
    emails via Gmail API. It uses the GoogleServiceManager for Gmail service access.
    """

    def __init__(self):
        """
        Initialize the MemGPTEmailRouter using the GoogleServiceManager.
        """
        self.base_url = BASE_URL
        self.service = google_service_manager.get_gmail_service()
        self.auth_email = google_service_manager.get_auth_email()

    async def generate_reminder_content(self, context: dict, memgpt_user_api_key: str, agent_key: str, instruction_template: str) -> Optional[str]:
        logger.debug(f"Generating reminder content for context: {context}")
        try:
            client = RESTClient(base_url=self.base_url, token=memgpt_user_api_key)
            formatted_message = instruction_template.format(**context)
            logger.debug(f"Formatted message: {formatted_message}")
            response = client.user_message(agent_id=agent_key, message=formatted_message)
            logger.debug(f"Raw response from MemGPT: {response}")
            content = self.extract_email_content(response)
            logger.debug(f"Extracted content: {content}")
            return content
        except Exception as e:
            logger.error(f"Error in generating reminder content: {str(e)}", exc_info=True)
            return None

    async def send_reminder(self, to_email: str, subject: str, reminder_content: str, memgpt_user_api_key: str, agent_key: str) -> Dict[str, Any]:
        logger.debug(f"Sending reminder to {to_email}")
        try:
            result = await self.generate_and_send_email(
                to_email=to_email,
                subject=subject,
                context={"body": reminder_content},
                memgpt_user_api_key=memgpt_user_api_key,
                agent_key=agent_key,
                is_reply=False
            )
            logger.debug(f"Reminder sending result: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to send reminder: {str(e)}", exc_info=True)
            return {"status": "failed", "message": str(e)}

    async def generate_and_send_email(self, 
                                      to_email: str, 
                                      subject: str, 
                                      context: Dict[str, str], 
                                      memgpt_user_api_key: str, 
                                      agent_key: str, 
                                      message_id: Optional[str] = None,
                                      instruction_template: Optional[str] = None,
                                      html_content: Optional[str] = None,
                                      attachments: Optional[List[str]] = None,
                                      is_reply: bool = True) -> None:
        if is_reply or instruction_template:
            email_content = await self._generate_content(context, memgpt_user_api_key, agent_key, instruction_template)
            if not email_content:
                logger.error("Failed to generate email content")
                return
        else:
            email_content = context.get('body', '')

        result = self._send_email(
            to_email=to_email,
            subject=subject,
            body=email_content,
            message_id=message_id,
            html_content=html_content,
            attachments=attachments
        )

        if result['status'] == 'success':
            logger.info(f"Email sent successfully. Message ID: {result['message_id']}")
        else:
            logger.error(f"Failed to send email: {result['message']}")

        return result

    async def _generate_content(self, context: Dict[str, str], memgpt_user_api_key: str, agent_key: str, instruction_template: Optional[str] = None) -> Optional[str]:
        client = RESTClient(base_url=self.base_url, token=memgpt_user_api_key)
        formatted_message = self._format_message(context, instruction_template)

        try:
            response = client.user_message(agent_id=agent_key, message=formatted_message)
            logger.info(f"MemGPT API response received: {response}")
            return self.extract_email_content(response)
        except Exception as e:
            logger.error(f"Error in generating email content: {str(e)}")
            return None

    def _send_email(self, to_email: str, subject: str, body: str, message_id: Optional[str] = None,
                    html_content: Optional[str] = None, attachments: Optional[List[str]] = None) -> Dict[str, str]:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['To'] = to_email
        msg['From'] = self.auth_email

        # Convert plain text to HTML if no HTML content is provided
        if not html_content:
            html_content = self._plain_text_to_html(body)

        # Add plain text body
        msg.attach(MIMEText(body, 'plain'))

        # Add HTML content
        msg.attach(MIMEText(html_content, 'html'))

        # Add attachments if provided
        if attachments:
            for file_path in attachments:
                with open(file_path, 'rb') as file:
                    part = MIMEApplication(file.read(), Name=os.path.basename(file_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                    msg.attach(part)

        if message_id:
            msg['In-Reply-To'] = message_id
            msg['References'] = message_id

        try:
            message = {'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode()}
            sent_message = self.service.users().messages().send(userId='me', body=message).execute()
            return {"status": "success", "message_id": sent_message['id']}
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return {"status": "failed", "message": str(e)}

    def _plain_text_to_html(self, text: str) -> str:
        # Escape HTML special characters
        text = html.escape(text)
        
        # Convert Markdown-style formatting to HTML
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)  # Italic
        
        # Split the text into paragraphs
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []
        
        for paragraph in paragraphs:
            if re.match(r'^\d+\.', paragraph):  # Check if paragraph starts with a number
                # It's a numbered list
                items = re.split(r'\n(?=\d+\.)', paragraph)
                list_html = '<ol>\n'
                for item in items:
                    item = re.sub(r'^\d+\.\s*', '', item.strip())  # Remove the number
                    list_html += f'  <li>{item}</li>\n'
                list_html += '</ol>'
                formatted_paragraphs.append(list_html)
            else:
                # Regular paragraph
                formatted_paragraphs.append(f'<p>{paragraph.replace(chr(10), "<br>")}</p>')
        
        return f'''
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    p {{ margin-bottom: 16px; }}
                    ol {{ margin-bottom: 16px; padding-left: 20px; }}
                    li {{ margin-bottom: 8px; }}
                </style>
            </head>
            <body>
                {''.join(formatted_paragraphs)}
            </body>
        </html>
        '''


    def _format_message(self, context: Dict[str, str], instruction_template: Optional[str] = None) -> str:
        if instruction_template:
            return instruction_template.format(**context)
        else:
            # Default template for email replies
            return (
                f"[EMAIL MESSAGE NOTIFICATION - Generate a personalized reply to the following email] "
                f"[message_id: {context.get('message_id', '')}] "
                f"[subject: {context.get('subject', '')}] "
                f"[from: {context.get('from', '')}] "
                f"[message: {context.get('body', '')}] "
                f"Please generate a personalized and professional reply to this email. "
                f"Address the sender by name and respond directly to their question or comment. "
                f"Do not include a subject line or any email sending instructions in your reply."
            )

    def extract_email_content(self, response: Union[UserMessageResponse, dict]) -> Optional[str]:
        logger.info(f"Attempting to extract email content from response type: {type(response)}")
        
        if isinstance(response, UserMessageResponse):
            messages = response.messages
        elif isinstance(response, dict):
            messages = response.get('messages', [])
        else:
            logger.error(f"Unexpected response type: {type(response)}")
            return None

        for message in messages:
            if isinstance(message, dict) and 'function_call' in message:
                function_call = message['function_call']
                if function_call.get('name') == 'send_message':
                    try:
                        arguments = json.loads(function_call['arguments'])
                        content = arguments.get('message')
                        logger.info(f"Extracted email content:\n{content}")
                        return content
                    except json.JSONDecodeError:
                        logger.error("Failed to parse function call arguments as JSON")

        logger.error(f"Failed to extract content. Full response: {response}")
        return None


    def generate_and_send_email_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Synchronous version of generate_and_send_email.
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.generate_and_send_email(**kwargs))
    

# Initialize the MemGPTEmailRouter
email_router = MemGPTEmailRouter()