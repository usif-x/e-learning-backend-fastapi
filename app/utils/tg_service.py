# app/utils/tg_service.py
import logging
from typing import List, Optional, Union

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramService:
    """Service for handling Telegram bot operations"""

    def __init__(self, bot_token: str):
        """
        Initialize Telegram service with bot token

        Args:
            bot_token: Telegram bot token from @BotFather
        """
        self.bot = Bot(token=bot_token)

    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
        buttons: Optional[List[List[InlineKeyboardButton]]] = None,
    ) -> Optional["Message"]:
        """
        Send a message to a chat with optional inline buttons.
        """
        try:
            reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

            message = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id,
                disable_web_page_preview=disable_web_page_preview,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
            )

            logger.info(f"Message sent successfully to chat {chat_id}")
            return message

        except TelegramError as e:
            logger.error(f"Failed to send message to chat {chat_id}: {e}")
            return None

    async def edit_message(
        self,
        chat_id: Union[int, str],
        message_id: int,
        text: str,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: bool = False,
    ) -> Optional[Message]:
        """
        Edit text of a message

        Args:
            chat_id: Unique identifier for the target chat
            message_id: Identifier of the message to edit
            text: New text of the message
            parse_mode: Send Markdown or HTML
            disable_web_page_preview: Disables link previews for links in this message

        Returns:
            Message object on success, None on failure
        """
        try:
            message = await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
            logger.info(f"Message {message_id} edited successfully in chat {chat_id}")
            return message
        except TelegramError as e:
            logger.error(f"Failed to edit message {message_id} in chat {chat_id}: {e}")
            return None

    async def reply_message(
        self,
        chat_id: Union[int, str],
        reply_to_message_id: int,
        text: str,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
    ) -> Optional[Message]:
        """
        Reply to a message

        Args:
            chat_id: Unique identifier for the target chat
            reply_to_message_id: Identifier of the message to reply to
            text: Text of the reply
            parse_mode: Send Markdown or HTML
            disable_web_page_preview: Disables link previews for links in this message
            disable_notification: Sends the message silently

        Returns:
            Message object on success, None on failure
        """
        return await self.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
        )

    async def delete_message(
        self,
        chat_id: Union[int, str],
        message_id: int,
    ) -> bool:
        """
        Delete a message

        Args:
            chat_id: Unique identifier for the target chat
            message_id: Identifier of the message to delete

        Returns:
            True on success, False on failure
        """
        try:
            await self.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id,
            )
            logger.info(
                f"Message {message_id} deleted successfully from chat {chat_id}"
            )
            return True
        except TelegramError as e:
            logger.error(
                f"Failed to delete message {message_id} from chat {chat_id}: {e}"
            )
            return False

    async def send_photo(
        self,
        chat_id: Union[int, str],
        photo: Union[str, bytes],
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
        disable_notification: bool = False,
    ) -> Optional[Message]:
        """
        Send a photo

        Args:
            chat_id: Unique identifier for the target chat
            photo: Photo to send. Pass a file_id as String to send a photo that exists on the Telegram servers, pass an HTTP URL as a String for Telegram to get a photo from the Internet, or upload a new photo using multipart/form-data
            caption: Photo caption
            parse_mode: Send Markdown or HTML
            reply_to_message_id: If the message is a reply, ID of the original message
            disable_notification: Sends the message silently

        Returns:
            Message object on success, None on failure
        """
        try:
            message = await self.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id,
                disable_notification=disable_notification,
            )
            logger.info(f"Photo sent successfully to chat {chat_id}")
            return message
        except TelegramError as e:
            logger.error(f"Failed to send photo to chat {chat_id}: {e}")
            return None

    async def send_document(
        self,
        chat_id: Union[int, str],
        document: Union[str, bytes],
        filename: Optional[str] = None,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
        disable_notification: bool = False,
    ) -> Optional[Message]:
        """
        Send a document

        Args:
            chat_id: Unique identifier for the target chat
            document: File to send. Pass a file_id as String to send a file that exists on the Telegram servers, pass an HTTP URL as a String for Telegram to get a file from the Internet, or upload a new one using multipart/form-data
            filename: Document filename
            caption: Document caption
            parse_mode: Send Markdown or HTML
            reply_to_message_id: If the message is a reply, ID of the original message
            disable_notification: Sends the message silently

        Returns:
            Message object on success, None on failure
        """
        try:
            message = await self.bot.send_document(
                chat_id=chat_id,
                document=document,
                filename=filename,
                caption=caption,
                parse_mode=parse_mode,
                reply_to_message_id=reply_to_message_id,
                disable_notification=disable_notification,
            )
            logger.info(f"Document sent successfully to chat {chat_id}")
            return message
        except TelegramError as e:
            logger.error(f"Failed to send document to chat {chat_id}: {e}")
            return None
