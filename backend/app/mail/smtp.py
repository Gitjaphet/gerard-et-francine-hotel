from email.message import EmailMessage
from email.utils import formataddr

import aiosmtplib

from app.mail.base import OutgoingEmail


class SmtpMailer:
    def __init__(
        self, *, host: str, port: int, username: str, password: str, sender: str, sender_name: str
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = formataddr((sender_name, sender))

    async def send(self, email: OutgoingEmail) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = email.to
        message["Subject"] = email.subject
        if email.reply_to:
            message["Reply-To"] = email.reply_to
        message.set_content(email.body)

        await aiosmtplib.send(
            message,
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            start_tls=True,
            timeout=20,
        )
