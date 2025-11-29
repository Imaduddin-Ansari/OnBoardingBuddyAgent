"""
Service Module 5: Notification Service
Sends welcome email notifications to new employees.
File: services/notification_service.py
"""
from datetime import datetime
from typing import Dict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from application.database import Database, Notification, NotificationType

# Load environment variables
load_dotenv()

class NotificationService:
    """Sends welcome email notifications to employees."""
    
    def __init__(self, db: Database):
        self.db = db
        
        # Email configuration - using environment variables
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.sender_password = os.getenv("SENDER_PASSWORD")
        self.sender_name = os.getenv("SENDER_NAME", "HR Team")
        
        # For testing without real email
        self.test_mode = os.getenv("EMAIL_TEST_MODE", "true").lower() == "true"
        
        # Validate email configuration
        if not self.test_mode:
            if not all([self.sender_email, self.sender_password]):
                print("⚠️ Warning: SENDER_EMAIL and SENDER_PASSWORD not set. Running in test mode.")
                self.test_mode = True
    
    async def send_welcome_email(self, employee_id: str) -> Dict:
        """
        Send welcome email to new employee with credentials and next steps.
        
        Args:
            employee_id: ID of the employee
            
        Returns:
            Dict with notification details and success status
        """
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"❌ Cannot send welcome email: Employee {employee_id} not found.")
        
        first_name = employee.name.split()[0]
        
        # Create notification record
        notification = Notification(
            employee_id=employee_id,
            type=NotificationType.WELCOME,
            subject=f"Welcome to the team, {first_name}! 🎉",
            message=self._generate_welcome_email_body(employee),
            status="pending"
        )
        
        notification = self.db.create_notification(notification)
        
        # Send actual email
        try:
            if not self.test_mode:
                self._send_email(
                    to_email=employee.email,
                    subject=notification.subject,
                    body=notification.message
                )
                delivery_status = "sent via email"
            else:
                print(f"[TEST MODE] Would send welcome email to {employee.email}")
                print(f"Subject: {notification.subject}")
                print(f"Body preview: {notification.message[:200]}...")
                delivery_status = "simulated (test mode)"
            
            # Mark as sent
            self.db.update_notification(
                notification.id,
                status="sent",
                sent_at=datetime.utcnow()
            )
            
            message = (
                f"✅ **Welcome Email Sent to {employee.name}**\n\n"
                f"📧 To: {employee.email}\n"
                f"📝 Subject: {notification.subject}\n"
                f"📤 Status: {delivery_status}\n\n"
                f"💡 The email includes:\n"
                f"• Personalized welcome message\n"
                f"• System credentials and access information\n"
                f"• Hardware collection instructions from IT\n"
                f"• First day orientation details\n"
                f"• Important contacts and resources\n"
                f"• Next steps for onboarding"
            )
            
        except Exception as e:
            # Mark as failed
            self.db.update_notification(
                notification.id,
                status="failed",
                error_message=str(e)
            )
            
            message = (
                f"❌ **Failed to send welcome email to {employee.name}**\n\n"
                f"Error: {str(e)}\n\n"
                f"Please check email configuration and try again."
            )
            
            raise Exception(message)
        
        return {
            "notification": notification,
            "message": message,
            "success": True
        }
    
    def _send_email(self, to_email: str, subject: str, body: str) -> None:
        """
        Send actual email using SMTP.
        Requires SENDER_EMAIL and SENDER_PASSWORD in environment variables.
        """
        if not all([self.sender_email, self.sender_password]):
            raise ValueError("SENDER_EMAIL and SENDER_PASSWORD must be set in environment variables")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{self.sender_name} <{self.sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add plain text body
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                print(f"✅ Email sent successfully to {to_email}")
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {e}")
            raise
    
    def _generate_welcome_email_body(self, employee) -> str:
        """Generate comprehensive welcome email content."""
        first_name = employee.name.split()[0]
        
        return f"""Hi {first_name},

Welcome to the team! We're thrilled to have you join us in the {employee.department} department as our new {employee.position or 'team member'}.

Your onboarding journey starts today, and we've prepared everything you need to get started smoothly.

═══════════════════════════════════════════════════════
📧 YOUR CREDENTIALS
═══════════════════════════════════════════════════════

Your system accounts have been created:

• Email: {employee.email}
• Access your email through the company portal
• Change your password on first login
• Enable two-factor authentication for security

═══════════════════════════════════════════════════════
🖥️ HARDWARE & EQUIPMENT SETUP
═══════════════════════════════════════════════════════

IMPORTANT: Please collect your hardware from IT Department on your first day:

What you'll receive:
• Laptop (pre-configured with necessary software)
• Monitor, keyboard, and mouse
• Building access badge
• Welcome kit with company swag

📍 Where: IT Department, 3rd Floor
⏰ When: First day, 9:00 AM
👤 Contact: IT Support Team (support@company.com)

Please bring:
• Government-issued ID for verification
• Completed paperwork (if any sent separately)

═══════════════════════════════════════════════════════
📅 YOUR FIRST DAY - {employee.joining_date.strftime('%B %d, %Y') if employee.joining_date else 'TBD'}
═══════════════════════════════════════════════════════

What to expect:

9:00 AM - Hardware Collection
• Visit IT Department to collect your equipment
• Setup will be assisted by IT staff

10:00 AM - Welcome Orientation
• Meet the HR team
• Company overview and culture introduction
• Office tour

11:30 AM - Department Introduction
• Meet your team members
• Meeting with your manager
• Overview of your role and responsibilities

1:00 PM - Lunch with Team
• Get to know your colleagues
• Informal Q&A session

2:30 PM - System Training
• Email and communication tools
• Project management systems
• Department-specific applications

4:00 PM - First Day Wrap-up
• Review action items
• Schedule for rest of the week
• Address any questions

═══════════════════════════════════════════════════════
✅ NEXT STEPS BEFORE YOUR FIRST DAY
═══════════════════════════════════════════════════════

1. ✓ Review this email and note important times
2. ✓ Prepare your ID and any required documents
3. ✓ Plan your commute to arrive by 9:00 AM
4. ✓ Read any additional documents sent by HR
5. ✓ Prepare questions for your first day

═══════════════════════════════════════════════════════
📞 IMPORTANT CONTACTS
═══════════════════════════════════════════════════════

• HR Team: hr@company.com | (555) 0100
• IT Support: support@company.com | (555) 0101
• Your Manager: {employee.manager_id}@company.com
• Reception: reception@company.com | (555) 0102
• Emergency: security@company.com | (555) 0911

═══════════════════════════════════════════════════════
🏢 OFFICE LOCATION & PARKING
═══════════════════════════════════════════════════════

Office Address:
[Company Name]
123 Business Street
City, State 12345

Parking: Visitor parking available (bring this email for validation)
Public Transit: [Transit info if applicable]

═══════════════════════════════════════════════════════
💡 HELPFUL TIPS FOR YOUR FIRST WEEK
═══════════════════════════════════════════════════════

• Arrive 10-15 minutes early on your first day
• Dress code is business casual (check with your manager for team-specific norms)
• Bring a notepad for notes during orientation
• Don't hesitate to ask questions - everyone is here to help!
• Take time to introduce yourself to colleagues

═══════════════════════════════════════════════════════
📚 ADDITIONAL RESOURCES
═══════════════════════════════════════════════════════

You'll receive access to:
• Employee Handbook (digital copy in your email)
• Company Intranet (login credentials provided on day 1)
• Learning & Development Portal
• Benefits Information Package

═══════════════════════════════════════════════════════

We're excited to have you as part of our team, {first_name}! Your skills and experience will be a great addition to {employee.department}.

If you have any questions before your first day, please don't hesitate to reach out. We're here to make your transition as smooth as possible.

See you soon!

Best regards,
{self.sender_name}

P.S. Remember to collect your hardware from IT at 9:00 AM on your first day!

═══════════════════════════════════════════════════════
This is an automated welcome message from the Employee Onboarding System.
For questions, contact hr@company.com
═══════════════════════════════════════════════════════"""