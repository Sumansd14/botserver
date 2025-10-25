def send_email_notification(data: dict):
    sender = os.getenv("OWNER_EMAIL")
    app_pw = os.getenv("GMAIL_APP_PASSWORD")
    if not sender or not app_pw:
        raise RuntimeError("Email env vars not set")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"New Lead from {data.get('name','')}"
    msg["From"] = sender
    msg["To"] = sender
    msg.attach(MIMEText(
        f"New lead:\n\nName: {data.get('name')}\nPhone: {data.get('phone')}\nMessage: {data.get('message')}\n",
        "plain"
    ))

    import smtplib, ssl
    ctx = ssl.create_default_context()

    # Try 587 (STARTTLS) first
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(sender, app_pw)
            server.send_message(msg)
        return
    except OSError as e:
        print(f"[email warn] 587 failed: {e}")

    # Fallback to 465 (SSL)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=10) as server:
        server.login(sender, app_pw)
        server.send_message(msg)