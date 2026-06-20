import random
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, session

class EmailService:
    @staticmethod
    def generate_otp():
        """Generate a secure 6-digit OTP code"""
        return str(random.randint(100000, 999999))

    @staticmethod
    def send_otp_email(recipient_email, otp_code):
        """Sends OTP to the recipient email using SMTP. Falls back gracefully on credential failure."""
        subject = f"Kode OTP Pendaftaran Guru MDT Miftahul Hidayah: {otp_code}"
        
        # HTML body styled beautifully
        html_body = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; border: 1px solid #e2e8f0; rounded-xl; border-radius: 16px; background-color: #ffffff;">
            <div style="text-align: center; margin-bottom: 24px;">
                <h2 style="color: #4f46e5; margin: 0; font-size: 24px; font-weight: 800;">MDT Miftahul Hidayah</h2>
                <p style="color: #64748b; margin: 4px 0 0 0; font-size: 14px;">Sistem Manajemen Informasi & Absensi</p>
            </div>
            
            <div style="border-top: 1px solid #f1f5f9; padding-top: 24px; margin-bottom: 24px;">
                <p style="font-size: 15px; color: #334155; line-height: 1.6;">Assalamu'alaikum Warahmatullahi Wabarakatuh,</p>
                <p style="font-size: 15px; color: #334155; line-height: 1.6;">Terima kasih telah mendaftar sebagai Guru di MDT Miftahul Hidayah. Berikut adalah kode verifikasi OTP Anda:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <span style="font-family: 'Courier New', Courier, monospace; font-size: 36px; font-weight: 800; letter-spacing: 6px; color: #4f46e5; background-color: #f5f3ff; padding: 12px 30px; border-radius: 12px; border: 1px dashed #c7d2fe; display: inline-block;">
                        {otp_code}
                    </span>
                </div>
                
                <p style="font-size: 13px; color: #ef4444; font-weight: 600;">Kode ini hanya berlaku selama 5 menit. Jangan sebarkan kode ini kepada siapa pun demi keamanan akun Anda.</p>
            </div>
            
            <div style="border-top: 1px solid #f1f5f9; padding-top: 20px; font-size: 12px; color: #94a3b8; text-align: center; line-height: 1.5;">
                <p style="margin: 0;">MDT Miftahul Hidayah &copy; 2026. All rights reserved.</p>
                <p style="margin: 4px 0 0 0;">Jl. Miftahul Hidayah, MDT Core Monolith System.</p>
            </div>
        </div>
        """
        
        # Get SMTP details from config
        mail_username = current_app.config.get('MAIL_USERNAME', '')
        mail_password = current_app.config.get('MAIL_PASSWORD', '')
        
        if not mail_username or mail_username == 'your-email@gmail.com' or not mail_password or mail_password == 'your-app-password':
            print(f"\n[SMTP NOT CONFIGURED] Fallback active.")
            print(f"==================================================")
            print(f"[OTP] EMAIL TUJUAN: {recipient_email}")
            print(f"[OTP] KODE VERIFIKASI: {otp_code}")
            print(f"==================================================\n")
            return False
            
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"MDT Miftahul Hidayah <{mail_username}>"
            msg['To'] = recipient_email
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Connect to Gmail SMTP
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(mail_username, mail_password)
            server.sendmail(mail_username, recipient_email, msg.as_string())
            server.quit()
            print(f"[SUCCESS] Real email OTP successfully sent to {recipient_email} via Gmail SMTP.")
            return True
        except Exception as e:
            print(f"\n[SMTP ERROR] Gagal mengirim email ke {recipient_email}: {e}")
            print(f"==================================================")
            print(f"[OTP] EMAIL TUJUAN: {recipient_email}")
            print(f"[OTP] KODE VERIFIKASI: {otp_code}")
            print(f"==================================================\n")
            return False
