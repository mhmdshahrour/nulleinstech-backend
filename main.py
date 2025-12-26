from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from email.message import EmailMessage
import smtplib
import ssl
import tempfile
import os
from typing import Optional

app = FastAPI(title="NullEinsTech Contact API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://mhmdshahrour.github.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "nulleinstech@gmail.com"
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

COMPANY_EMAIL = "nulleinstech@gmail.com"
MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".zip"}


def send_email(message: EmailMessage) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)

        
@app.options("/contact")
async def contact_options():
    return {}


@app.post("/contact")
async def contact(
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    company: Optional[str] = Form(None),
    subject: str = Form(...),
    message: str = Form(...),
    preferred_contact: str = Form("email"),
    file: Optional[UploadFile] = File(None),
):
    if not SMTP_PASSWORD:
        raise HTTPException(status_code=500, detail="SMTP not configured")

    if len(message) < 20:
        raise HTTPException(status_code=400, detail="Message too short")

    attachment_path = None

    try:
        if file:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail="Unsupported file type")

            content = await file.read()
            if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
                raise HTTPException(status_code=400, detail="File too large")

            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp.write(content)
            tmp.close()
            attachment_path = tmp.name

        inbound = EmailMessage()
        inbound["From"] = f"NullEinsTech <{SMTP_USER}>"
        inbound["To"] = COMPANY_EMAIL
        inbound["Reply-To"] = email
        inbound["Subject"] = "[NullEinsTech] New Contact Form Submission"

        inbound.set_content(
            f"""
Name: {full_name}
Email: {email}
Phone: {phone}
Company: {company or "-"}
Preferred Contact: {preferred_contact}
Subject: {subject}

Message:
{message}
""".strip()
        )

        if attachment_path:
            with open(attachment_path, "rb") as f:
                inbound.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="octet-stream",
                    filename=file.filename,
                )

        send_email(inbound)

        autoreply = EmailMessage()
        autoreply["From"] = f"NullEinsTech <{SMTP_USER}>"
        autoreply["To"] = email
        autoreply["Subject"] = "We’ve received your message | NullEinsTech"

        autoreply.set_content(
            f"""
Hello {full_name},

Thank you for contacting NullEinsTech.
We have received your message and will get back to you shortly.

Best regards,
NullEinsTech Team
""".strip()
        )

        send_email(autoreply)

        return {"status": "success"}

    finally:
        if attachment_path and os.path.exists(attachment_path):
            os.remove(attachment_path)
