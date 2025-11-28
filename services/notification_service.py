"""
Service Module 5: Notification Service
Sends REAL email notifications using SMTP for welcome emails and reminders.
File: services/notification_service.py
"""
from datetime import datetime
from typing import List, Optional, Dict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from application.database import Database, Notification, NotificationType, TaskStatus

# Load environment variables
load_dotenv()

class NotificationService:
    """Sends real email notifications to employees."""
    
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
        """Send welcome email to new employee."""
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
                f"• Overview of onboarding tasks\n"
                f"• System access information\n"
                f"• Important next steps and contacts"
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
    
    async def send_task_reminder(self, employee_id: str) -> Dict:
        """Send reminder about pending tasks."""
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"❌ Cannot send reminder: Employee {employee_id} not found.")
        
        # Get pending tasks
        pending_tasks = self.db.get_pending_tasks(employee_id)
        
        if not pending_tasks:
            return {
                "notification": None,
                "message": f"ℹ️ No pending tasks for {employee.name}. No reminder needed.",
                "success": True
            }
        
        first_name = employee.name.split()[0]
        
        # Create notification
        notification = Notification(
            employee_id=employee_id,
            type=NotificationType.TASK_REMINDER,
            subject=f"Reminder: You have {len(pending_tasks)} pending onboarding task(s)",
            message=self._generate_task_reminder_body(employee, pending_tasks),
            status="pending"
        )
        
        notification = self.db.create_notification(notification)
        
        # Send email
        try:
            if not self.test_mode:
                self._send_email(
                    to_email=employee.email,
                    subject=notification.subject,
                    body=notification.message
                )
                delivery_status = "sent via email"
            else:
                print(f"[TEST MODE] Would send reminder to {employee.email}")
                print(f"Subject: {notification.subject}")
                print(f"Tasks: {len(pending_tasks)}")
                delivery_status = "simulated (test mode)"
            
            self.db.update_notification(
                notification.id,
                status="sent",
                sent_at=datetime.utcnow()
            )
            
            message = (
                f"✅ **Task Reminder Sent to {employee.name}**\n\n"
                f"📧 To: {employee.email}\n"
                f"📋 Pending Tasks: {len(pending_tasks)}\n"
                f"📤 Status: {delivery_status}\n\n"
                f"The reminder includes:\n"
            )
            
            for i, task in enumerate(pending_tasks[:3], 1):
                due = task.due_date.strftime('%b %d') if task.due_date else "No deadline"
                message += f"{i}. {task.title} (Due: {due})\n"
            
            if len(pending_tasks) > 3:
                message += f"... and {len(pending_tasks) - 3} more tasks"
            
        except Exception as e:
            self.db.update_notification(
                notification.id,
                status="failed",
                error_message=str(e)
            )
            
            message = (
                f"❌ **Failed to send reminder to {employee.name}**\n\n"
                f"Error: {str(e)}"
            )
            raise Exception(message)
        
        return {
            "notification": notification,
            "message": message,
            "success": True
        }
    
    async def send_bulk_reminders(self) -> Dict:
        """Send reminders to all employees with pending tasks."""
        employees = self.db.get_all_employees()
        sent_notifications = []
        failed_sends = []
        no_tasks_count = 0
        
        for employee in employees:
            pending_tasks = self.db.get_pending_tasks(employee.id)
            if pending_tasks:
                try:
                    result = await self.send_task_reminder(employee.id)
                    if result["notification"]:
                        sent_notifications.append(result["notification"])
                except Exception as e:
                    failed_sends.append({
                        "employee": employee.name,
                        "error": str(e)
                    })
            else:
                no_tasks_count += 1
        
        message = (
            f"📧 **Bulk Reminder Campaign Complete**\n\n"
            f"📊 Results:\n"
            f"• ✅ Successfully sent: {len(sent_notifications)}\n"
            f"• ❌ Failed: {len(failed_sends)}\n"
            f"• ℹ️ No pending tasks: {no_tasks_count}\n"
            f"• 👥 Total employees: {len(employees)}\n"
        )
        
        if failed_sends:
            message += f"\n⚠️ Failed sends:\n"
            for fail in failed_sends[:3]:
                message += f"• {fail['employee']}\n"
        
        if len(sent_notifications) > 0:
            message += f"\n✅ Reminders successfully delivered to employees with pending tasks."
        
        return {
            "notifications": sent_notifications,
            "message": message,
            "success": True,
            "stats": {
                "sent": len(sent_notifications),
                "failed": len(failed_sends),
                "no_tasks": no_tasks_count,
                "total": len(employees)
            }
        }
    
    def _send_email(self, to_email: str, subject: str, body: str) -> None:
        """
        Send actual email using SMTP - matches test script style.
        Requires SENDER_EMAIL and SENDER_PASSWORD in environment variables.
        """
        if not all([self.sender_email, self.sender_password]):
            raise ValueError("SENDER_EMAIL and SENDER_PASSWORD must be set in environment variables")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"{self.sender_name} <{self.sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add plain text body (you can also add HTML if needed)
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
        """Generate welcome email content."""
        first_name = employee.name.split()[0]
        
        return f"""Hi {first_name},

Welcome to the team! We're thrilled to have you join us in the {employee.department} department as our new {employee.position or 'team member'}.

Your onboarding journey starts today, and we've prepared everything you need to get started smoothly.

WHAT'S NEXT:

1. Check Your Tasks
   You have several onboarding tasks assigned to you. Please complete them by their due dates.
   You can view all your tasks in the onboarding dashboard.

2. System Access
   We're setting up your accounts right now:
   - Email account: {employee.email}
   - System credentials (VPN, SSO, building access)
   - Department-specific tools and applications
   
   You'll receive your credentials shortly.

3. Meet Your Team
   Your manager will reach out to schedule a welcome meeting. Don't hesitate to ask questions!

IMPORTANT DATES:
- Joining Date: {employee.joining_date.strftime('%B %d, %Y') if employee.joining_date else 'TBD'}
- First Day Orientation: Check your calendar for details

We're here to help you succeed. If you have any questions or need assistance, please reach out to:
- HR Team: hr@company.com
- IT Support: support@company.com
- Your Manager: {employee.manager_id}@company.com

Once again, welcome aboard! We're excited to see what you'll achieve.

Best regards,
{self.sender_name}

---
This is an automated message from the Onboarding System."""
    
    def _generate_task_reminder_body(self, employee, pending_tasks) -> str:
        """Generate task reminder email content."""
        first_name = employee.name.split()[0]
        
        # Sort tasks by due date and priority
        sorted_tasks = sorted(
            pending_tasks,
            key=lambda t: (t.priority, t.due_date or datetime.max)
        )
        
        task_list = []
        for i, task in enumerate(sorted_tasks[:10], 1):
            due_date = task.due_date.strftime('%b %d') if task.due_date else "No due date"
            priority_emoji = "🔴" if task.priority == 1 else "🟡" if task.priority == 2 else "🟢"
            task_list.append(f"{i}. {priority_emoji} {task.title} (Due: {due_date})")
        
        tasks_text = '\n'.join(task_list)
        
        return f"""Hi {first_name},

This is a friendly reminder about your pending onboarding tasks.

You currently have {len(pending_tasks)} task(s) waiting to be completed:

{tasks_text}

{'... and more' if len(pending_tasks) > 10 else ''}

NEED HELP?
If you're stuck on any task or need clarification, please don't hesitate to reach out to:
- Your Manager
- HR Team: hr@company.com
- IT Support: support@company.com (for technical tasks)

We want to make sure your onboarding experience is smooth and successful!

Best regards,
{self.sender_name}

---
This is an automated reminder from the Onboarding System."""
    
    def send_overdue_alert(self, employee_id: str, overdue_tasks: List) -> Dict:
        """Send alert about overdue tasks."""
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"❌ Employee {employee_id} not found.")
        
        first_name = employee.name.split()[0]
        
        # Build overdue tasks message
        overdue_list = '\n'.join([f"- {t.title}" for t in overdue_tasks])
        
        notification = Notification(
            employee_id=employee_id,
            type=NotificationType.TASK_OVERDUE,
            subject=f"⚠️ URGENT: You have {len(overdue_tasks)} overdue task(s)",
            message=f"""Hi {first_name},

Some of your onboarding tasks are now overdue:

{overdue_list}

Please complete these as soon as possible.

Best regards,
{self.sender_name}""",
            status="pending"
        )
        
        notification = self.db.create_notification(notification)
        
        # Send email
        try:
            if not self.test_mode:
                self._send_email(
                    to_email=employee.email,
                    subject=notification.subject,
                    body=notification.message
                )
                delivery_status = "sent via email"
            else:
                delivery_status = "simulated (test mode)"
            
            self.db.update_notification(notification.id, status="sent", sent_at=datetime.utcnow())
            
            message = (
                f"⚠️ **Overdue Alert Sent to {employee.name}**\n\n"
                f"📧 To: {employee.email}\n"
                f"🚨 Overdue Tasks: {len(overdue_tasks)}\n"
                f"📤 Status: {delivery_status}\n\n"
                f"Manager should follow up with {first_name} regarding these overdue tasks."
            )
            
        except Exception as e:
            self.db.update_notification(notification.id, status="failed", error_message=str(e))
            message = f"❌ Failed to send overdue alert: {str(e)}"
        
        return {
            "notification": notification,
            "message": message,
            "success": True
        }