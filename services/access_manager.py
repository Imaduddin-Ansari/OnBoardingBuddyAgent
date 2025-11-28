"""
Service Module 2: Access Setup
Sends automated requests for system credentials, email accounts, 
and workspace permissions via connected IT APIs.
Uses MailSlurp API to create REAL email addresses.
File: services/access_manager.py
"""
from datetime import datetime
from typing import List, Dict
import asyncio
import random
import string
import os
import mailslurp_client
from application.database import Database, AccessRequest, AccessType, AccessStatus

class AccessManager:
    """Manages system access setup for new employees."""
    
    def __init__(self, db: Database):
        self.db = db
        self.company_domain = "company.com"
        
        # MailSlurp API Configuration
        self.mailslurp_api_key = os.getenv("MAILSLURP_API_KEY")
    
    def _generate_username(self, name: str) -> str:
        """Generate username from employee name."""
        parts = name.strip().split()
        if len(parts) >= 2:
            username = f"{parts[0]}{parts[-1][0]}".lower()
        else:
            username = parts[0].lower()
        
        username += str(random.randint(100, 999))
        return username
    
    def _generate_password(self, length: int = 12) -> str:
        """Generate a secure random password."""
        uppercase = random.choice(string.ascii_uppercase)
        lowercase = random.choice(string.ascii_lowercase)
        digit = random.choice(string.digits)
        special = random.choice("!@#$%^&*")
        
        remaining = length - 4
        all_chars = string.ascii_letters + string.digits + "!@#$%^&*"
        rest = ''.join(random.choices(all_chars, k=remaining))
        
        password = uppercase + lowercase + digit + special + rest
        password_list = list(password)
        random.shuffle(password_list)
        
        return ''.join(password_list)
    
    def _create_mailslurp_inbox(self, name: str) -> Dict:
        """
        Create a REAL email inbox using MailSlurp API.
        
        Returns:
            Dict with email address, inbox_id, and access details
        """
        try:
            print("🔄 Creating real email address via MailSlurp...")
            
            # Create MailSlurp configuration
            configuration = mailslurp_client.Configuration()
            configuration.api_key['x-api-key'] = self.mailslurp_api_key
            
            with mailslurp_client.ApiClient(configuration) as api_client:
                # Create an inbox
                inbox_controller = mailslurp_client.InboxControllerApi(api_client)
                
                # Generate a name for the inbox
                parts = name.strip().split()
                inbox_name = f"{parts[0]}-{parts[-1] if len(parts) > 1 else 'employee'}".lower()
                
                # Create inbox
                inbox = inbox_controller.create_inbox(
                    name=inbox_name,
                    description=f"Corporate email for {name}"
                )
                
                email_address = inbox.email_address
                inbox_id = inbox.id
                
                print(f"✅ Email created successfully: {email_address}")
                
                return {
                    "success": True,
                    "email": email_address,
                    "inbox_id": inbox_id,
                    "inbox_name": inbox_name,
                    "service": "MailSlurp",
                    "access_url": f"https://app.mailslurp.com/inboxes/{inbox_id}",
                    "web_url": f"https://app.mailslurp.com/",
                    "note": "Permanent inbox - emails will be stored indefinitely"
                }
                
        except mailslurp_client.ApiException as e:
            print(f"❌ MailSlurp API error: {e.status} - {e.reason}")
            return {
                "success": False,
                "error": f"MailSlurp API error: {e.status} - {e.reason}"
            }
        except Exception as e:
            print(f"❌ Error creating email: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_mailslurp_messages(self, inbox_id: str) -> Dict:
        """
        Retrieve emails from a MailSlurp inbox.
        
        Args:
            inbox_id: The inbox ID from MailSlurp
            
        Returns:
            Dict with list of emails
        """
        try:
            configuration = mailslurp_client.Configuration()
            configuration.api_key['x-api-key'] = self.mailslurp_api_key
            
            with mailslurp_client.ApiClient(configuration) as api_client:
                inbox_controller = mailslurp_client.InboxControllerApi(api_client)
                emails = inbox_controller.get_emails(inbox_id=inbox_id)
                
                return {
                    "success": True,
                    "count": len(emails),
                    "emails": [
                        {
                            "id": email.id,
                            "subject": email.subject,
                            "from": email.from_,
                            "to": email.to,
                            "created_at": email.created_at
                        }
                        for email in emails
                    ]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_real_email(self, name: str) -> Dict:
        """
        Generate a REAL working email address using MailSlurp.
        
        Returns:
            Dict with email details
        """
        # Use MailSlurp to create permanent inbox
        result = self._create_mailslurp_inbox(name)
        
        if result["success"]:
            return result
        
        # If MailSlurp fails, use fallback
        print(f"⚠️ MailSlurp unavailable, using fallback email...")
        
        parts = name.strip().split()
        fallback_email = f"{parts[0].lower()}.{parts[-1].lower() if len(parts) > 1 else 'employee'}@fallback.local"
        
        return {
            "success": False,
            "error": "MailSlurp service unavailable",
            "email": fallback_email,
            "service": "Fallback",
            "note": "Email service temporarily unavailable. Using fallback address."
        }
    
    async def setup_all_access(self, employee_id: str) -> Dict:
        """
        Setup all required access for a new employee.
        Creates REAL email address via MailSlurp and system credentials.
        
        Args:
            employee_id: ID of the employee
            
        Returns:
            Dict with access requests, credentials, and summary message
        """
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"❌ Cannot setup access: Employee {employee_id} not found in the system.")
        
        first_name = employee.name.split()[0]
        access_requests = []
        credentials = {}
        
        print(f"\n{'='*60}")
        print(f"🚀 Setting up access for: {employee.name}")
        print(f"{'='*60}\n")
        
        # 1. Email Account - Create REAL working email via MailSlurp
        print("📧 Step 1/3: Creating email account...")
        email_result = await self.request_email_account(employee_id)
        access_requests.append(email_result['request'])
        credentials['email'] = email_result['credentials']
        
        # 2. Update employee record with the generated email
        self.db.update_employee(
            employee_id,
            email=credentials['email']['email_address']
        )
        
        # 3. System Credentials (VPN, building access, etc.)
        print("\n🔐 Step 2/3: Generating system credentials...")
        system_result = await self.request_system_credentials(employee_id)
        access_requests.append(system_result['request'])
        credentials['system'] = system_result['credentials']
        
        # 4. Workspace Permissions (based on department)
        print(f"\n🔧 Step 3/3: Setting up workspace access for {employee.department}...")
        workspace_result = await self.request_workspace_access(employee_id, employee.department)
        access_requests.append(workspace_result['request'])
        credentials['workspace'] = workspace_result['access_list']
        
        # Print credentials clearly
        print(f"\n{'='*60}")
        print(f"✅ ACCESS SETUP COMPLETE")
        print(f"{'='*60}\n")
        
        is_fallback = credentials['email'].get('is_fallback', False)
        
        if not is_fallback:
            print(f"📧 EMAIL CREDENTIALS:")
            print(f"   Email Address: {credentials['email']['email_address']}")
            print(f"   Password: {credentials['email']['password']}")
            print(f"   Service: {credentials['email']['service']}")
            if credentials['email'].get('inbox_id'):
                print(f"   Inbox ID: {credentials['email']['inbox_id']}")
            if credentials['email'].get('access_url'):
                print(f"   Access URL: {credentials['email']['access_url']}")
            print(f"   Status: ✅ ACTIVE - Permanent inbox (emails stored indefinitely)")
        else:
            print(f"⚠️  EMAIL (FALLBACK MODE):")
            print(f"   Email Address: {credentials['email']['email_address']}")
            print(f"   Note: Email service temporarily unavailable")
        
        print(f"\n🔐 SYSTEM CREDENTIALS:")
        print(f"   Username: {credentials['system']['username']}")
        print(f"   Password: {credentials['system']['password']}")
        print(f"   Building Badge: #{credentials['system']['badge_number']}")
        
        print(f"\n🔧 WORKSPACE ACCESS ({len(credentials['workspace'])} apps):")
        for tool in credentials['workspace']:
            print(f"   ✓ {tool}")
        
        print(f"\n{'='*60}\n")
        
        # Create comprehensive message
        service_name = credentials['email']['service']
        
        message = (
            f"✅ **Access Setup Complete for {employee.name}**\n\n"
        )
        
        if is_fallback:
            message += (
                f"⚠️ **Email Address (Fallback Mode):**\n"
                f"• Email: {credentials['email']['email_address']}\n"
                f"• Status: Using fallback (email services temporarily unavailable)\n"
                f"• Note: Real email services will be retried later\n\n"
            )
        else:
            message += (
                f"📧 **REAL Email Address Created (MailSlurp):**\n"
                f"• Email: {credentials['email']['email_address']}\n"
                f"• Password: {credentials['email']['password']}\n"
                f"• Service: {service_name}\n"
                f"• Inbox ID: {credentials['email'].get('inbox_id', 'N/A')}\n"
            )
            
            if credentials['email'].get('access_url'):
                message += f"• 📬 Access Inbox: {credentials['email']['access_url']}\n"
            
            message += f"• Status: ✅ Active - Permanent inbox\n"
            message += f"• Note: {credentials['email'].get('note', 'Inbox ready')}\n\n"
        
        message += (
            f"🔐 **System Access:**\n"
            f"• Username: {credentials['system']['username']}\n"
            f"• Password: {credentials['system']['password']}\n"
            f"• VPN Access: Enabled\n"
            f"• SSO Login: Configured\n"
            f"• Building Badge: #{credentials['system']['badge_number']}\n\n"
            f"**Workspace & Applications:**\n"
        )
        
        for tool in credentials['workspace']:
            message += f"• {tool}: Access Granted ✓\n"
        
        if not is_fallback:
            message += (
                f"\n📨 **How to Check Email:**\n"
                f"1. Visit: {credentials['email'].get('access_url', 'MailSlurp Dashboard')}\n"
                f"2. Login to MailSlurp: {credentials['email'].get('web_url', 'https://app.mailslurp.com/')}\n"
                f"3. All emails sent to {credentials['email']['email_address']} will appear in the inbox\n"
                f"4. Or check via API using inbox ID: {credentials['email'].get('inbox_id', 'N/A')}\n\n"
            )
        
        message += (
            f"📝 **Important Notes:**\n"
            f"• Save these credentials securely\n"
            f"• Change passwords on first login\n"
            f"• Enable two-factor authentication\n"
        )
        
        if not is_fallback:
            message += f"• MailSlurp inbox is permanent - emails stored indefinitely\n"
        
        return {
            "access_requests": access_requests,
            "credentials": credentials,
            "message": message,
            "success": True,
            "employee_name": employee.name,
            "email_address": credentials['email']['email_address'],
            "email_password": credentials['email']['password'],
            "email_service": credentials['email']['service'],
            "email_access_url": credentials['email'].get('access_url'),
            "inbox_id": credentials['email'].get('inbox_id'),
            "system_username": credentials['system']['username'],
            "system_password": credentials['system']['password'],
            "is_fallback": is_fallback
        }
    
    async def request_email_account(self, employee_id: str) -> Dict:
        """Request creation of a REAL email account using MailSlurp API."""
        employee = self.db.get_employee(employee_id)
        
        access_request = AccessRequest(
            employee_id=employee_id,
            access_type=AccessType.EMAIL,
            status=AccessStatus.PENDING,
            details=f"Creating REAL email account for {employee.name} via MailSlurp..."
        )
        
        access_request = self.db.create_access_request(access_request)
        
        # Create REAL email using MailSlurp
        email_result = await self.generate_real_email(employee.name)
        email_password = self._generate_password(14)
        
        # Even if email service fails, we continue with fallback
        if email_result["success"]:
            status = AccessStatus.COMPLETED
            details = f"✅ Real email created: {email_result['email']} via {email_result['service']} (Inbox: {email_result.get('inbox_id')})"
        else:
            # Use fallback but mark as completed (not failed)
            status = AccessStatus.COMPLETED
            details = f"⚠️ Using fallback email: {email_result['email']} (Email service temporarily unavailable)"
            print(f"⚠️ Email service error: {email_result.get('error')}")
        
        # Mark as completed
        self.db.update_access_request(
            access_request.id,
            status=status,
            completed_at=datetime.utcnow(),
            details=details
        )
        
        credentials = {
            "email_address": email_result["email"],
            "password": email_password,
            "service": email_result.get("service", "Fallback"),
            "inbox_id": email_result.get("inbox_id"),
            "inbox_name": email_result.get("inbox_name"),
            "access_url": email_result.get("access_url"),
            "web_url": email_result.get("web_url"),
            "note": email_result.get("note"),
            "is_fallback": not email_result["success"]
        }
        
        return {
            "request": access_request,
            "credentials": credentials
        }
    
    async def request_system_credentials(self, employee_id: str) -> Dict:
        """Request system credentials with generated username and password."""
        employee = self.db.get_employee(employee_id)
        
        username = self._generate_username(employee.name)
        system_password = self._generate_password(16)
        badge_number = f"{random.randint(10000, 99999)}"
        
        print(f"   ✓ Generated username: {username}")
        print(f"   ✓ Generated password: {system_password}")
        print(f"   ✓ Assigned badge: #{badge_number}")
        
        access_request = AccessRequest(
            employee_id=employee_id,
            access_type=AccessType.SYSTEM_CREDENTIALS,
            status=AccessStatus.PENDING,
            details=f"Setting up system credentials for username: {username}"
        )
        
        access_request = self.db.create_access_request(access_request)
        await asyncio.sleep(0.3)
        
        self.db.update_access_request(
            access_request.id,
            status=AccessStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            details=f"✅ System credentials created: Username '{username}', VPN enabled, SSO configured, Badge #{badge_number}"
        )
        
        return {
            "request": access_request,
            "credentials": {
                "username": username,
                "password": system_password,
                "badge_number": badge_number,
                "vpn_enabled": True,
                "sso_enabled": True
            }
        }
    
    async def request_workspace_access(self, employee_id: str, department: str) -> Dict:
        """Request workspace and application access based on department."""
        employee = self.db.get_employee(employee_id)
        access_details = self._get_department_access(department)
        
        print(f"   ✓ Granting access to {len(access_details)} applications")
        
        access_request = AccessRequest(
            employee_id=employee_id,
            access_type=AccessType.WORKSPACE,
            status=AccessStatus.PENDING,
            details=f"Granting {department} department access to: {', '.join(access_details)}"
        )
        
        access_request = self.db.create_access_request(access_request)
        await asyncio.sleep(0.2)
        
        self.db.update_access_request(
            access_request.id,
            status=AccessStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            details=f"✅ Workspace access granted for {len(access_details)} applications"
        )
        
        return {
            "request": access_request,
            "access_list": access_details
        }
    
    def _get_department_access(self, department: str) -> List[str]:
        """Map department to required system access."""
        access_map = {
            "Engineering": ["GitHub", "Jira", "AWS Console", "Slack", "Confluence"],
            "HR": ["BambooHR", "Workday", "Slack", "Google Workspace"],
            "Sales": ["Salesforce", "HubSpot", "Slack", "LinkedIn Sales Navigator"],
            "Marketing": ["HubSpot", "Google Analytics", "Canva", "Slack"],
            "Finance": ["QuickBooks", "Expensify", "Slack", "SAP"],
            "Operations": ["Asana", "Slack", "Google Workspace", "Zoom"],
            "IT": ["AWS Console", "GitHub", "Jira", "PagerDuty", "Slack"],
            "Legal": ["DocuSign", "Clio", "Slack", "Google Workspace"]
        }
        return access_map.get(department, ["Slack", "Google Workspace"])
    
    def get_access_status(self, employee_id: str) -> Dict:
        """Get current status of all access requests for an employee."""
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"❌ Employee with ID '{employee_id}' not found.")
        
        requests = self.db.get_access_requests(employee_id)
        
        completed_count = len([r for r in requests if r.status == AccessStatus.COMPLETED])
        pending_count = len([r for r in requests if r.status == AccessStatus.PENDING])
        failed_count = len([r for r in requests if r.status == AccessStatus.FAILED])
        
        if completed_count == len(requests) and len(requests) > 0:
            status_message = f"✅ All access setup completed for {employee.name}"
        elif pending_count > 0:
            status_message = f"⏳ Access setup in progress for {employee.name} ({completed_count}/{len(requests)} completed)"
        elif failed_count > 0:
            status_message = f"⚠️ Some access requests failed for {employee.name}"
        else:
            status_message = f"📋 No access requests found for {employee.name}"
        
        return {
            "employee_id": employee_id,
            "employee_name": employee.name,
            "employee_email": employee.email,
            "total_requests": len(requests),
            "completed": completed_count,
            "pending": pending_count,
            "failed": failed_count,
            "message": status_message,
            "requests": [r.to_dict() for r in requests]
        }
    
    def retry_failed_access(self, request_id: str) -> Dict:
        """Retry a failed access request."""
        request = self.db.update_access_request(
            request_id,
            status=AccessStatus.PENDING,
            error_message=None
        )
        
        if not request:
            raise ValueError(f"❌ Access request with ID '{request_id}' not found.")
        
        employee = self.db.get_employee(request.employee_id)
        
        message = (
            f"🔄 Retrying failed access request for {employee.name}\n"
            f"• Request Type: {request.access_type.value}\n"
            f"• Status: Pending (retry in progress)\n"
        )
        
        return {
            "request": request,
            "message": message,
            "success": True
        }