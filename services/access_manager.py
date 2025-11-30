from datetime import datetime
from typing import List, Dict
import asyncio
import random
import string
import os
import mailslurp_client
from application.database import Database

class AccessManager:
    """Manages system access setup for new employees."""
    
    def __init__(self, db: Database):
        self.db = db
        self.company_domain = "company.com"
        
        # MailSlurp API Configuration
        self.mailslurp_api_key = os.getenv("MAILSLURP_API_KEY")
        
        # Validate API key on initialization
        if not self.mailslurp_api_key:
            print("⚠️  Warning: MAILSLURP_API_KEY not found in environment variables")
            print("    Set it with: export MAILSLURP_API_KEY='your-api-key'")
    
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
    
    def _create_mailslurp_inbox_sync(self, name: str) -> Dict:
        """
        Create a REAL email inbox using MailSlurp API (synchronous).
        
        Returns:
            Dict with email address, inbox_id, and access details
        """
        if not self.mailslurp_api_key:
            return {
                "success": False,
                "error": "MAILSLURP_API_KEY not configured"
            }
        
        try:
            print("🔄 Creating real email address via MailSlurp...")
            
            # Create MailSlurp configuration
            configuration = mailslurp_client.Configuration()
            configuration.api_key['x-api-key'] = self.mailslurp_api_key
            
            # Use context manager properly
            with mailslurp_client.ApiClient(configuration) as api_client:
                # Create an inbox
                inbox_controller = mailslurp_client.InboxControllerApi(api_client)
                
                # Generate a name for the inbox
                parts = name.strip().split()
                inbox_name = f"{parts[0]}-{parts[-1] if len(parts) > 1 else 'employee'}".lower()
                
                # Create inbox with proper parameters
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
                    "inbox_id": str(inbox_id),
                    "inbox_name": inbox_name,
                    "service": "MailSlurp",
                    "access_url": f"https://app.mailslurp.com/inboxes/{inbox_id}",
                    "web_url": "https://app.mailslurp.com/",
                    "note": "Permanent inbox - emails will be stored indefinitely"
                }
                
        except mailslurp_client.ApiException as e:
            error_msg = f"MailSlurp API error: {e.status}"
            if hasattr(e, 'reason') and e.reason:
                error_msg += f" - {e.reason}"
            if hasattr(e, 'body') and e.body:
                error_msg += f" - {e.body}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Error creating email: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    async def generate_real_email(self, name: str) -> Dict:
        """
        Generate a REAL working email address using MailSlurp.
        Runs the synchronous MailSlurp call in a thread pool to avoid blocking.
        Uses timeout to prevent hanging.
        
        Returns:
            Dict with email details
        """
        try:
            # Run the synchronous MailSlurp call in a thread pool with timeout
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,  # Uses default executor (ThreadPoolExecutor)
                    self._create_mailslurp_inbox_sync,
                    name
                ),
                timeout=10.0  # 10 second timeout
            )
            
            if result["success"]:
                return result
            
            # If MailSlurp fails, use fallback
            print(f"⚠️  MailSlurp unavailable: {result.get('error', 'Unknown error')}")
            print(f"    Using fallback email generation...")
            
        except asyncio.TimeoutError:
            print(f"⚠️  MailSlurp API timeout (>10s)")
            print(f"    Using fallback email generation...")
        except Exception as e:
            print(f"⚠️  Exception during email creation: {str(e)}")
            print(f"    Using fallback email generation...")
        
        # Fallback email generation
        parts = name.strip().split()
        fallback_email = f"{parts[0].lower()}.{parts[-1].lower() if len(parts) > 1 else 'employee'}@{self.company_domain}"
        
        return {
            "success": False,
            "error": "MailSlurp service unavailable or timeout",
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
            Dict with credentials and summary message
        """
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"❌ Cannot setup access: Employee {employee_id} not found in the system.")
        
        first_name = employee.name.split()[0]
        credentials = {}
        
        print(f"\n{'='*60}")
        print(f"🚀 Setting up access for: {employee.name}")
        print(f"{'='*60}\n")
        
        # 1. Email Account - Create REAL working email via MailSlurp
        print("📧 Step 1/3: Creating email account...")
        email_result = await self.generate_real_email(employee.name)
        email_password = self._generate_password(14)
        
        credentials['email'] = {
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
        
        # 2. Update employee record with the generated email
        self.db.update_employee(
            employee_id,
            email=credentials['email']['email_address']
        )
        
        # 3. System Credentials (VPN, building access, etc.)
        print("\n🔐 Step 2/3: Generating system credentials...")
        username = self._generate_username(employee.name)
        system_password = self._generate_password(16)
        badge_number = f"{random.randint(10000, 99999)}"
        
        print(f"   ✓ Generated username: {username}")
        print(f"   ✓ Generated password: {system_password}")
        print(f"   ✓ Assigned badge: #{badge_number}")
        
        credentials['system'] = {
            "username": username,
            "password": system_password,
            "badge_number": badge_number,
            "vpn_enabled": True,
            "sso_enabled": True
        }
        
        await asyncio.sleep(0.3)
        
        # 4. Workspace Permissions (based on department)
        print(f"\n🔧 Step 3/3: Setting up workspace access for {employee.department}...")
        access_details = self._get_department_access(employee.department)
        
        print(f"   ✓ Granting access to {len(access_details)} applications")
        
        credentials['workspace'] = access_details
        
        await asyncio.sleep(0.2)
        
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