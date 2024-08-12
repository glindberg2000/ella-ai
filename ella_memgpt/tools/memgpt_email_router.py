# File: memgpt_email_router.py

import logging
import json
from typing import Optional, Dict, List, Union
from memgpt.client.client import RESTClient, UserMessageResponse
from ella_memgpt.tools.google_utils import GoogleEmailUtils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

logger = logging.getLogger(__name__)

class MemGPTEmailRouter:
    def __init__(self, base_url: str, gmail_token_path: str, google_credentials_path: str):
        self.base_url = base_url
        self.gmail_token_path = gmail_token_path
        self.google_credentials_path = google_credentials_path
        self.email_utils = GoogleEmailUtils(self.gmail_token_path, self.google_credentials_path)

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
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['To'] = to_email
        msg['From'] = self.email_utils.auth_email

        # Add plain text body
        msg.attach(MIMEText(body, 'plain'))

        # Add HTML content if provided
        if html_content:
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

        return self.email_utils.send_email_mime(msg)

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


# class MemGPTEmailRouter:
#     def __init__(self, base_url: str, gmail_token_path: str, google_credentials_path: str):
#         self.base_url = base_url
#         self.gmail_token_path = gmail_token_path
#         self.google_credentials_path = google_credentials_path

#     async def route_reply_to_memgpt_api(self, body: str, subject: str, message_id: str, from_email: str, memgpt_user_api_key: str, agent_key: str) -> None:
#         client = RESTClient(base_url=self.base_url, token=memgpt_user_api_key)
        
#         sender_name = from_email.split('@')[0].replace('.', ' ').title()
        
#         formatted_message = (
#             f"[EMAIL MESSAGE NOTIFICATION - Generate a personalized reply to the following email] "
#             f"[message_id: {message_id}] "
#             f"[subject: {subject}] "
#             f"[from email: {sender_name}] "
#             f"[message: {body}] "
#             f"Please generate a thoughtful reply to this email. Address the sender by name, not their email address, and respond directly to their question or comment. Do not include a subject line or any email sending instructions in your reply."
#         )

#         try:
#             response = client.user_message(agent_id=agent_key, message=formatted_message)
#             logger.info(f"MemGPT API response received: {response}")

#             email_content = self.extract_email_content(response)

#             if email_content:
#                 reply_subject = f"Re: {subject}"

#                 email_utils = GoogleEmailUtils(self.gmail_token_path, self.google_credentials_path)
#                 result = email_utils.send_email(
#                     recipient_email=from_email,
#                     subject=reply_subject,
#                     body=email_content,
#                     message_id=message_id
#                 )

#                 if result['status'] == 'success':
#                     logger.info(f"Reply email sent successfully. Message ID: {result['message_id']}")
#                 else:
#                     logger.error(f"Failed to send reply email: {result['message']}")
#             else:
#                 logger.error("Failed to extract email content from LLM response")

#         except Exception as e:
#             logger.error(f"Error in processing or sending reply email: {str(e)}", exc_info=True)

    
#     def extract_email_content(self, response: Union[UserMessageResponse, dict]) -> Optional[str]:
#         logger.info(f"Attempting to extract email content from response type: {type(response)}")
        
#         if isinstance(response, UserMessageResponse):
#             messages = response.messages
#         elif isinstance(response, dict):
#             messages = response.get('messages', [])
#         else:
#             logger.error(f"Unexpected response type: {type(response)}")
#             return None

#         for message in messages:
#             if isinstance(message, dict) and 'function_call' in message:
#                 function_call = message['function_call']
#                 if function_call.get('name') == 'send_message':
#                     try:
#                         arguments = json.loads(function_call['arguments'])
#                         content = arguments.get('message')
#                         logger.info(f"Extracted email content:\n{content}")
#                         return content
#                     except json.JSONDecodeError:
#                         logger.error("Failed to parse function call arguments as JSON")
        
#         logger.error(f"Failed to extract content. Full response: {response}")
#         return None