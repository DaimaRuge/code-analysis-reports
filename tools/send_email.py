#!/usr/bin/env python3
"""
邮件发送工具 - SMTP 配置
邮箱: qun.xitang.du@gmail.com
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

# Gmail SMTP 配置
SMTP_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,  # TLS 端口
    "sender_email": "qun.xitang.du@gmail.com",
    "sender_password": "hzyacyjilhigwhiu",  # Gmail 应用专用密码
}

def send_email(
    recipient: str,
    subject: str,
    body: str,
    body_type: str = "plain",  # "plain" 或 "html"
    attachment_path: str = None
) -> bool:
    """
    发送邮件
    
    Args:
        recipient: 收件人邮箱
        subject: 邮件主题
        body: 邮件正文
        body_type: 正文类型 ("plain" 或 "html")
        attachment_path: 附件路径（可选）
    
    Returns:
        bool: 是否发送成功
    """
    try:
        # 创建邮件对象
        msg = MIMEMultipart()
        msg["From"] = SMTP_CONFIG["sender_email"]
        msg["To"] = recipient
        msg["Subject"] = subject
        
        # 添加正文
        msg.attach(MIMEText(body, body_type, "utf-8"))
        
        # 添加附件（如果有）
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            filename = os.path.basename(attachment_path)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {filename}",
            )
            msg.attach(part)
        
        # 连接到 SMTP 服务器并发送
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_CONFIG["smtp_server"], SMTP_CONFIG["smtp_port"]) as server:
            server.starttls(context=context)  # 启用 TLS 加密
            server.login(
                SMTP_CONFIG["sender_email"],
                SMTP_CONFIG["sender_password"]
            )
            server.sendmail(
                SMTP_CONFIG["sender_email"],
                recipient,
                msg.as_string()
            )
        
        print(f"✅ 邮件发送成功！")
        print(f"   收件人: {recipient}")
        print(f"   主题: {subject}")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def send_email_with_markdown(recipient: str, subject: str, markdown_content: str):
    """发送 Markdown 格式的邮件（自动转换为 HTML）"""
    try:
        import markdown
        html_body = markdown.markdown(markdown_content)
        return send_email(recipient, subject, html_body, body_type="html")
    except ImportError:
        # 如果没有 markdown 库，以纯文本发送
        return send_email(recipient, subject, markdown_content, body_type="plain")

if __name__ == "__main__":
    # 测试发送
    import sys
    
    if len(sys.argv) < 4:
        print("用法: python send_email.py <收件人> <主题> <正文> [附件路径]")
        print("示例: python send_email.py user@example.com '测试邮件' '这是一封测试邮件'")
        sys.exit(1)
    
    recipient = sys.argv[1]
    subject = sys.argv[2]
    body = sys.argv[3]
    attachment = sys.argv[4] if len(sys.argv) > 4 else None
    
    send_email(recipient, subject, body, attachment_path=attachment)
