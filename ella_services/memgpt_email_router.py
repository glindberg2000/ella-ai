
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
from datetime import datetime
from google_service_manager import google_service_manager
import time
from tenacity import retry, stop_after_attempt, wait_fixed

# Load environment variables
load_dotenv()

# Constants
BASE_URL = os.getenv("MEMGPT_API_URL", "http://localhost:8080")

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemGPTEmailRouter:
    def __init__(self):
        self.base_url = BASE_URL
        self.service = google_service_manager.get_gmail_service()
        self.auth_email = google_service_manager.get_auth_email()
        logger.info(f"MemGPTEmailRouter initialized with base_url: {self.base_url}")

    async def send_direct_email(self, to_email: str, subject: str, body: str, message_id: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Preparing to send direct email to: {to_email}")
        try:
            # Convert plain text to HTML
            html_content = self._plain_text_to_html(body)

            # Prepare email parts
            text_part = MIMEText(body, 'plain')
            html_part = MIMEText(html_content, 'html')

            # Create multipart message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['To'] = to_email
            msg['From'] = self.auth_email

            # Add text and HTML parts to the message
            msg.attach(text_part)
            msg.attach(html_part)

            if message_id:
                msg['In-Reply-To'] = message_id
                msg['References'] = message_id

            # Encode the message
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

            # Send the email
            result = await asyncio.to_thread(
                self.service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute
            )

            logger.info(f"Email sent successfully. Details:")
            logger.info(f"  From: {self.auth_email}")
            logger.info(f"  To: {to_email}")
            logger.info(f"  Subject: {subject}")
            logger.info(f"  Message ID: {result['id']}")
            logger.info(f"  Timestamp: {datetime.now().isoformat()}")
            logger.info(f"  Body preview: {body[:100]}...")

            return {"status": "success", "message_id": result['id'], "to_email": to_email}
        except Exception as e:
            logger.error(f"Error in send_direct_email: {str(e)}", exc_info=True)
            return {"status": "failed", "message": str(e), "to_email": to_email}

    async def send_reminder(self, to_email: str, subject: str, reminder_content: dict, memgpt_user_api_key: str, agent_key: str) -> Dict[str, Any]:
        logger.info(f"Entering send_reminder method")
        logger.info(f"Preparing to send reminder email to: {to_email}")
        try:
            result = await self.generate_and_send_email(
                to_email=to_email,
                subject=subject,
                context=reminder_content,
                memgpt_user_api_key=memgpt_user_api_key,
                agent_key=agent_key,
                is_reminder=True
            )
            result['to_email'] = to_email  # Ensure to_email is always in the result
            if result['status'] == 'success':
                logger.info(f"Reminder email successfully sent to: {to_email}")
            else:
                logger.error(f"Failed to send reminder email to: {to_email}. Error: {result['message']}")
            return result
        except Exception as e:
            logger.error(f"Exception in send_reminder for {to_email}: {str(e)}", exc_info=True)
            return {"status": "failed", "message": str(e), "to_email": to_email}
 
    async def generate_and_send_email(self, to_email: str, subject: str, context: Dict[str, Any], memgpt_user_api_key: str, agent_key: str, is_reminder: bool = False, message_id: Optional[str] = None, html_content: Optional[str] = None, attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        logger.info(f"Generating and sending email to: {to_email}")
        try:
            # Generate email content using LLM
            email_content = await self._generate_content(context, memgpt_user_api_key, agent_key, is_reminder)
            if not email_content:
                logger.error("Failed to generate email content")
                return {"status": "failed", "message": "Failed to generate email content", "to_email": to_email}

            # Send the email
            result = await self._send_email(
                to_email=to_email,
                subject=subject,
                body=email_content,
                message_id=message_id,
                html_content=html_content,
                attachments=attachments
            )
            logger.info(f"Email sending result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in generate_and_send_email: {str(e)}", exc_info=True)
            return {"status": "failed", "message": str(e), "to_email": to_email}

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def _call_memgpt_api(self, client, agent_key, instruction):
        logger.info(f"Calling MemGPT API with agent_key: {agent_key}")
        response = await asyncio.to_thread(client.user_message, agent_id=agent_key, message=instruction)
        logger.info("MemGPT API response received")
        return response

    async def _generate_content(self, context: Dict[str, Any], memgpt_user_api_key: str, agent_key: str, is_reminder: bool) -> Optional[str]:
        logger.info(f"Entering _generate_content method")
        logger.info(f"Generating content with context: {context}")
        logger.debug(f"memgpt_user_api_key: {memgpt_user_api_key[:5]}... (truncated)")
        logger.debug(f"agent_key: {agent_key}")
        logger.debug(f"is_reminder: {is_reminder}")

        try:
            client = RESTClient(base_url=self.base_url, token=memgpt_user_api_key)
            logger.info(f"RESTClient initialized with base_url: {self.base_url}")
            
            if is_reminder:
                instruction = (
                    "Generate a reminder email for an upcoming event. Use the following details:\n"
                    f"Event: {context['event_summary']}\n"
                    f"Start time: {context['event_start']}\n"
                    f"End time: {context['event_end']}\n"
                    f"Description: {context.get('event_description', 'No description provided')}\n"
                    f"Reminder: {context['minutes_before']} minutes before the event\n\n"
                    "Write a friendly and informative email reminding the recipient about this event."
                )
            else:
                instruction = f"Generate the content of an email reply based on the following context:\n{json.dumps(context)}\n\nWrite a professional and appropriate email response. Do not send the email; just return the text of the email."
            logger.debug(f"Instruction for LLM: {instruction}")

            try:
                response = await self._call_memgpt_api(client, agent_key, instruction)
            except Exception as api_error:
                logger.error(f"Error calling MemGPT API: {str(api_error)}", exc_info=True)
                raise ValueError(f"Failed to get response from MemGPT API: {str(api_error)}")

            logger.debug(f"Raw MemGPT API response: {response}")
            
            content = self.extract_email_content(response)
            if content:
                logger.info("Successfully extracted email content")
                logger.debug(f"Extracted content: {content[:100]}... (truncated)")
                return content
            else:
                logger.error("Failed to extract email content from MemGPT API response")
                raise ValueError("Failed to extract email content from MemGPT API response")
        
        except Exception as e:
            logger.error(f"Error in _generate_content: {str(e)}", exc_info=True)
            raise

    def extract_email_content(self, response: Union[UserMessageResponse, dict]) -> Optional[str]:
        logger.info(f"Entering extract_email_content method")
        logger.info(f"Extracting email content from response type: {type(response)}")
        
        if isinstance(response, UserMessageResponse):
            messages = response.messages
            logger.debug("Response is of type UserMessageResponse")
        elif isinstance(response, dict):
            messages = response.get('messages', [])
            logger.debug("Response is of type dict")
        else:
            logger.error(f"Unexpected response type: {type(response)}")
            return None

        logger.debug(f"Number of messages in response: {len(messages)}")

        for i, message in enumerate(messages):
            logger.debug(f"Processing message {i+1}")
            logger.debug(f"Message type: {type(message)}")
            logger.debug(f"Message content: {message}")
            
            if isinstance(message, dict):
                if 'function_call' in message:
                    function_call = message['function_call']
                    logger.debug(f"Found function call: {function_call.get('name')}")
                    if function_call.get('name') == 'send_message':
                        try:
                            arguments = json.loads(function_call['arguments'])
                            logger.debug(f"Function call arguments: {arguments}")
                            content = arguments.get('message')
                            if content:
                                logger.info(f"Extracted email content (first 100 chars):\n{content[:100]}...")
                                return content
                            else:
                                logger.warning("'message' key not found in function call arguments")
                        except json.JSONDecodeError:
                            logger.error("Failed to parse function call arguments as JSON")
                else:
                    logger.debug("Message does not contain a function call")
            else:
                logger.warning(f"Message {i+1} is not a dictionary: {type(message)}")

        logger.error(f"Failed to extract content. Full response: {response}")
        return None
    
    async def _send_email(self, to_email: str, subject: str, body: str, message_id: Optional[str] = None,
                          html_content: Optional[str] = None, attachments: Optional[List[str]] = None) -> Dict[str, str]:
        logger.info(f"Sending email to: {to_email}")
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['To'] = to_email
        msg['From'] = self.auth_email

        if not html_content:
            html_content = self._plain_text_to_html(body)

        msg.attach(MIMEText(body, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

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
            sent_message = await asyncio.to_thread(
                self.service.users().messages().send(userId='me', body=message).execute
            )
            logger.info(f"Email sent successfully. Details:")
            logger.info(f"  From: {self.auth_email}")
            logger.info(f"  To: {to_email}")
            logger.info(f"  Subject: {subject}")
            logger.info(f"  Message ID: {sent_message['id']}")
            logger.info(f"  Timestamp: {datetime.now().isoformat()}")
            logger.info(f"  Body preview: {body[:100]}...")
            return {"status": "success", "message_id": sent_message['id'], "to_email": to_email}
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}", exc_info=True)
            return {"status": "failed", "message": str(e), "to_email": to_email}



        
    async def generate_reminder_content(self, context: dict, memgpt_user_api_key: str, agent_key: str, instruction_template: str) -> Optional[str]:
        logger.debug(f"Generating reminder content for context: {context}")
        try:
            client = RESTClient(base_url=self.base_url, token=memgpt_user_api_key)
            formatted_message = instruction_template.format(**context)
            logger.debug(f"Formatted message: {formatted_message}")
            response = await asyncio.to_thread(client.user_message, agent_id=agent_key, message=formatted_message)
            logger.debug(f"Raw response from MemGPT: {response}")
            content = self.extract_email_content(response)
            logger.debug(f"Extracted content: {content}")
            return content
        except Exception as e:
            logger.error(f"Error in generating reminder content: {str(e)}", exc_info=True)
            return None


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


    def generate_and_send_email_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Synchronous version of generate_and_send_email.
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.generate_and_send_email(**kwargs))
    

# Initialize the MemGPTEmailRouter
email_router = MemGPTEmailRouter()