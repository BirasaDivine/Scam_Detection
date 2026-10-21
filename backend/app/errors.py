# Every message is fixed text. None of them may include anything the user sent.

EMPTY = "The chat is empty. Add some messages and try again."
NO_MESSAGES = "We found no messages to check in this chat."
TOO_SHORT = "This chat is too short to check. Add more messages, or choose Single SMS for one message."
NOT_WHATSAPP = "This does not look like a WhatsApp export. Try Plain text as the chat source."
UNREADABLE = "We could not read this file. Save it as plain UTF-8 text and try again."
BAD_REQUEST_BODY = "The request could not be read."
FILE_TOO_LARGE = "This file is larger than 1 MB. Try a shorter chat."
TEXT_TOO_LARGE = "This text is larger than 1 MB. Try a shorter chat."
TOO_MANY_MESSAGES = "This chat has more than 2,000 messages. Try a shorter part of it."
WRONG_FILE_TYPE = "Only .txt files are supported."
WRONG_CONTENT_TYPE = "Send the chat as a .txt file or as text."
INVALID = "Some details are missing or not valid."
TIMEOUT = "The check took too long. Try a shorter chat."
INTERNAL = "Something went wrong on our side. Please try again."


class AppError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
