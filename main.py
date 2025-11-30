from fastapi import FastAPI, HTTPException, BackgroundTasks
import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
import uvicorn
import uuid
import json

# Import our modules
from application.database import Database, Employee
from services.data_collector import DataCollector
from services.access_manager import AccessManager
from services.progress_monitor import ProgressMonitor
from services.notification_service import NotificationService

app = FastAPI(
    title="Onboarding Buddy Agent",
    description="Employee onboarding automation system",
    version="1.0.0"
)

db = Database()
access_manager = AccessManager(db)
progress_monitor = ProgressMonitor(db)
notification_service = NotificationService(db)

data_collector = DataCollector(db)

class InputMetadata(BaseModel):
    language: str = "en"
    extra: Dict[str, Any] = Field(default_factory=dict)

class RequestInput(BaseModel):
    text: str
    metadata: InputMetadata = Field(default_factory=InputMetadata)

class RequestContext(BaseModel):
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class WorkerRequest(BaseModel):
    request_id: str
    agent_name: str
    intent: str
    input: RequestInput
    context: RequestContext = Field(default_factory=RequestContext)

class OutputData(BaseModel):
    result: str
    confidence: Optional[float] = None
    details: Optional[str] = None

class ErrorData(BaseModel):
    type: str
    message: str

class WorkerResponse(BaseModel):
    request_id: str
    agent_name: str
    status: str
    output: Optional[OutputData] = None
    error: Optional[ErrorData] = None

@app.get("/health")
async def health_check():
    """Health check endpoint for supervisor agent."""
    return {
        "status": "healthy",
        "agent": "onboarding_agent",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "database": "connected",
        "services": {
            "data_collection": "operational",
            "access_setup": "operational",
            "progress_monitoring": "operational",
            "notifications": "operational"
        }
    }

@app.post("/execute", response_model=WorkerResponse)
async def execute_intent(request: WorkerRequest, background_tasks: BackgroundTasks):
    """
    Main execution endpoint implementing onboarding intents.
    Routes requests to appropriate service handlers.
    """
    try:
        # Parse input to extract structured data
        input_data = parse_input(request.input.text, request.input.metadata.extra)
        
        # Route to appropriate handler based on intent
        if request.intent in ["onboarding.create", "employee.create"]:
            result = await handle_create_employee(input_data)
        
        elif request.intent in ["onboarding.update", "employee.update"]:
            result = await handle_update_employee(input_data)
        
        elif request.intent in ["onboarding.check_progress", "employee.check_status"]:
            result = await handle_check_progress(input_data)
        
        else:
            return WorkerResponse(
                request_id=request.request_id,
                agent_name=request.agent_name,
                status="error",
                output=None,
                error=ErrorData(
                    type="unsupported_intent",
                    message=f"Intent '{request.intent}' is not supported"
                )
            )
        
        # Success response
        return WorkerResponse(
            request_id=request.request_id,
            agent_name=request.agent_name,
            status="success",
            output=result,
            error=None
        )
    
    except Exception as e:
        return WorkerResponse(
            request_id=request.request_id,
            agent_name=request.agent_name,
            status="error",
            output=None,
            error=ErrorData(
                type="runtime_error",
                message=str(e)
            )
        )

async def handle_create_employee(data: dict) -> OutputData:
    """Create new employee and trigger onboarding flow."""
    
    # Create employee
    employee = data_collector.create_employee(
        name=data.get("name"),
        personal_email=data.get("personal_email"),
        department=data.get("department"),
        joining_date=data.get("joining_date"),
        manager_id=data.get("manager_id"),
        phone=data.get("phone"),
        position=data.get("position")
    )
    
    # Check progress
    progress = progress_monitor.get_employee_progress(employee.id)
    
    # Build response based on progress
    if progress["is_complete"]:
        try:
            access_result = await access_manager.setup_all_access(employee.id)
            
            # Send welcome email to personal email
            try:
                welcome_result = await notification_service.send_welcome_email(employee.id)
            except Exception as e:
                print(f"Warning: Failed to send welcome email: {e}")
            
            result_msg = format_complete_onboarding_details(employee, access_result, progress)
            
        except Exception as e:
            result_msg = format_incomplete_access_details(employee, progress)
    else:
        result_msg = format_incomplete_employee_details(employee, progress)
    
    return OutputData(
        result=result_msg,
        confidence=1.0,
        details=None
    )

# Update handle_update_employee:
async def handle_update_employee(data: dict) -> OutputData:
    """Update employee information by personal email."""
    
    personal_email = data.get("personal_email") or data.get("email")
    
    if not personal_email:
        raise ValueError("Personal email is required to update employee information")
    
    # Find employee by personal email
    employee = db.get_employee_by_personal_email(personal_email)
    
    if not employee:
        raise ValueError(f"No employee found with personal email: {personal_email}")
    
    # Update employee information
    update_fields = {}
    if data.get("name"):
        update_fields["name"] = data.get("name")
    if data.get("department"):
        update_fields["department"] = data.get("department")
    if data.get("position"):
        update_fields["position"] = data.get("position")
    if data.get("phone"):
        update_fields["phone"] = data.get("phone")
    if data.get("manager_id"):
        update_fields["manager_id"] = data.get("manager_id")
    if data.get("joining_date"):
        update_fields["joining_date"] = data.get("joining_date")
    
    if not update_fields:
        raise ValueError("No fields provided to update")
    
    # Perform update
    updated_employee = data_collector.update_employee_info(employee.id, **update_fields)
    
    # Check progress after update
    progress = progress_monitor.get_employee_progress(employee.id)
    
    # If now complete, trigger access setup
    if progress["is_complete"]:
        try:
            access_result = await access_manager.setup_all_access(employee.id)
            
            try:
                welcome_result = await notification_service.send_welcome_email(employee.id)
            except Exception as e:
                print(f"Warning: Failed to send welcome email: {e}")
            
            result_msg = format_complete_onboarding_details(updated_employee, access_result, progress)
            
        except Exception as e:
            result_msg = format_incomplete_access_details(updated_employee, progress)
    else:
        result_msg = format_incomplete_employee_details(updated_employee, progress)
    
    return OutputData(
        result=result_msg,
        confidence=1.0,
        details=None
    )


# Update handle_check_progress:
async def handle_check_progress(data: dict) -> OutputData:
    """Check employee information completeness."""
    
    employee_id = data.get("employee_id")
    personal_email = data.get("personal_email") or data.get("email")
    
    if not employee_id and not personal_email:
        # Return progress for all employees
        all_progress = progress_monitor.get_all_employees_progress()
        result_msg = f"""EMPLOYEE ONBOARDING DASHBOARD

Total Employees: {all_progress['summary']['total_employees']}
Complete: {all_progress['summary']['complete']}
Incomplete: {all_progress['summary']['incomplete']}

EMPLOYEE LIST:
"""
        for emp_progress in all_progress['employees']:
            result_msg += f"\n- {emp_progress['name']} ({emp_progress['personal_email']}): {emp_progress['completion_percentage']:.0f}% complete"
        
        return OutputData(
            result=result_msg,
            confidence=1.0,
            details=None
        )
    
    # Find employee
    if personal_email:
        employee = db.get_employee_by_personal_email(personal_email)
        if not employee:
            raise ValueError(f"No employee found with personal email: {personal_email}")
        employee_id = employee.id
    else:
        employee = db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
    
    # Get progress
    progress = progress_monitor.get_employee_progress(employee_id)
    
    # Format response
    if progress["is_complete"]:
        result_msg = format_complete_progress_details(employee, progress)
    else:
        result_msg = format_incomplete_employee_details(employee, progress)
    
    return OutputData(
        result=result_msg,
        confidence=1.0,
        details=None
    )


# Update formatting functions to show both emails:
def format_complete_onboarding_details(employee: Employee, access_result: dict, progress: dict) -> str:
    """Format details when onboarding is complete."""
    credentials = access_result.get("credentials", {})
    email_creds = credentials.get("email", {})
    system_creds = credentials.get("system", {})
    workspace_apps = credentials.get("workspace", [])
    
    details = f"""✅ EMPLOYEE ONBOARDING COMPLETE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 EMPLOYEE DETAILS

Name: {employee.name}
Personal Email: {employee.personal_email}
Company Email: {employee.email or 'Pending generation'}
Department: {employee.department}
Position: {employee.position or 'Not specified'}
Phone: {employee.phone or 'Not specified'}
Manager ID: {employee.manager_id or 'Not specified'}
Joining Date: {employee.joining_date.strftime('%B %d, %Y') if employee.joining_date else 'Not specified'}
Employee ID: {employee.id}

Profile Completion: {progress['completion_percentage']:.0f}% ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📧 EMAIL ACCOUNT GENERATED

Company Email: {email_creds.get('email_address', 'N/A')}
Password: {email_creds.get('password', 'N/A')}
Service: {email_creds.get('service', 'N/A')}
Inbox ID: {email_creds.get('inbox_id', 'N/A')}

🌐 WEB ACCESS
Access URL: {email_creds.get('access_url', 'N/A')}
Web Portal: {email_creds.get('web_url', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔐 SYSTEM CREDENTIALS

Username: {system_creds.get('username', 'N/A')}
Password: {system_creds.get('password', 'N/A')}
Building Badge: #{system_creds.get('badge_number', 'N/A')}
VPN Access: {'✓ Enabled' if system_creds.get('vpn_enabled') else '✗ Disabled'}
SSO Login: {'✓ Configured' if system_creds.get('sso_enabled') else '✗ Not configured'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💻 WORKSPACE ACCESS ({len(workspace_apps)} applications)

"""
    for app in workspace_apps:
        details += f"  • {app}\n"
    
    details += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✉️ WELCOME EMAIL

Status: ✓ Sent to {employee.personal_email}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 NEXT STEPS

1. Employee will receive welcome email at their personal email
2. IT will prepare hardware and workstation
3. Manager will schedule first day orientation
4. Employee begins onboarding on {employee.joining_date.strftime('%B %d, %Y') if employee.joining_date else 'TBD'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return details


def format_incomplete_employee_details(employee: Employee, progress: dict) -> str:
    """Format details when employee information is incomplete."""
    missing_fields = progress.get("missing_fields", [])
    
    details = f"""⚠️ EMPLOYEE INFORMATION INCOMPLETE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 EMPLOYEE DETAILS

Name: {employee.name if employee.name else '❌ MISSING'}
Personal Email: {employee.personal_email if employee.personal_email else '❌ MISSING'}
Company Email: {employee.email if employee.email else 'Not yet generated'}
Department: {employee.department if employee.department else '❌ MISSING'}
Position: {employee.position if employee.position else '❌ MISSING'}
Phone: {employee.phone if employee.phone else '❌ MISSING'}
Manager ID: {employee.manager_id if employee.manager_id else '❌ MISSING'}
Joining Date: {employee.joining_date.strftime('%B %d, %Y') if employee.joining_date else '❌ MISSING'}
Employee ID: {employee.id}

Profile Completion: {progress['completion_percentage']:.0f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ MISSING INFORMATION ({len(missing_fields)} field(s)):

"""
    for field in missing_fields:
        field_display = field.replace('_', ' ').title()
        details += f"  • {field_display}\n"
    
    details += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 HOW TO COMPLETE

To update this employee's information, use their personal email:

Example update request:
{{
    "email": "{employee.personal_email}",
    "position": "Software Engineer",
    "phone": "+1-555-0123",
    "manager_id": "MGR001"
}}

Once all required fields are complete, the system will automatically:
  1. Generate corporate email account
  2. Create system credentials
  3. Setup workspace access
  4. Send welcome email with all details

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return details

def format_incomplete_access_details(employee: Employee, progress: dict) -> str:
    """Format details when access setup is pending or failed."""
    details = f"""⏳ EMPLOYEE CREATED - ACCESS SETUP IN PROGRESS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 EMPLOYEE DETAILS

Name: {employee.name}
Personal Email: {employee.personal_email}
Company Email: {employee.email or 'Pending generation'}
Department: {employee.department}
Position: {employee.position or 'Not specified'}
Phone: {employee.phone or 'Not specified'}
Manager ID: {employee.manager_id or 'Not specified'}
Joining Date: {employee.joining_date.strftime('%B %d, %Y') if employee.joining_date else 'Not specified'}
Employee ID: {employee.id}

Profile Completion: {progress['completion_percentage']:.0f}% ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 ACCESS SETUP STATUS

The system is currently setting up:
  • Corporate email account
  • System credentials (username, password, VPN)
  • Workspace application access
  • Building access badge

Status: Access setup is being processed. Details will be available shortly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    return details

def format_complete_progress_details(employee: Employee, progress: dict) -> str:
    """Format details for complete progress check."""
    details = f"""✅ EMPLOYEE INFORMATION COMPLETE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 EMPLOYEE DETAILS

Name: {employee.name}
Email: {employee.email}
Department: {employee.department}
Position: {employee.position}
Phone: {employee.phone}
Manager ID: {employee.manager_id}
Joining Date: {employee.joining_date.strftime('%B %d, %Y') if employee.joining_date else 'Not specified'}
Employee ID: {employee.id}

Profile Completion: {progress['completion_percentage']:.0f}% ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All required information is complete. Employee is ready for access setup.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    return details

"""
Fix for joining_date parsing - Convert ISO strings to datetime objects
Add this helper function and update the parse_input function
"""

def parse_date_string(date_str: str) -> datetime:
    """
    Convert various date string formats to datetime object.
    Handles ISO format, natural language dates, etc.
    """
    if not date_str:
        return None
    
    try:
        # Try parsing ISO format first
        if 'T' in date_str:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        
        # Use dateutil parser for flexible parsing
        return date_parser.parse(date_str)
    except Exception as e:
        print(f"Warning: Could not parse date '{date_str}': {e}")
        return None

def parse_input(text: str, extra: dict) -> dict:
    """
    Parse natural language input and extract structured data.
    Supports both structured extra dict and row-based text format.
    """
    if extra and any(key in extra for key in ["name", "email", "personal_email", "employee_id", "department"]):
        # Convert joining_date string to datetime if present
        if "joining_date" in extra and isinstance(extra["joining_date"], str):
            extra["joining_date"] = parse_date_string(extra["joining_date"])
        
        # Handle email field - treat as personal_email
        if "email" in extra and "personal_email" not in extra:
            extra["personal_email"] = extra["email"]
        return extra
    
    # Try row-based format first (Name: value, Personal Email: value, etc.)
    row_based_data = parse_row_based_format(text)
    if row_based_data:
        return row_based_data
    
    # Otherwise, parse from natural language text
    result = {}
    text_lower = text.lower()
    
    # Extract name (look for capitalized sequences)
    name = extract_name_from_text(text)
    if name:
        result["name"] = name
    
    # Extract email - store as personal_email
    email = extract_email_from_text(text)
    if email:
        result["personal_email"] = email
    elif name:
        # Generate email from name if not provided
        result["personal_email"] = generate_email_from_name(name)
    
    # Extract department
    department = extract_department(text_lower)
    if department:
        result["department"] = department
    
    # Extract position/job title
    position = extract_position(text_lower)
    if position:
        result["position"] = position
    
    # Extract phone
    phone = extract_phone_from_text(text)
    if phone:
        result["phone"] = phone
    
    # Set joining date (default to next Monday if not specified)
    if "joining" in text_lower or "start" in text_lower:
        date_str = extract_date(text_lower)
        result["joining_date"] = parse_date_string(date_str)
    elif name:  # If creating employee, set default joining date
        result["joining_date"] = get_next_monday()
    
    # Set manager_id based on department
    if department:
        result["manager_id"] = get_manager_for_department(department)
    
    # Extract employee_id
    employee_id = extract_employee_id(text_lower)
    if employee_id:
        result["employee_id"] = employee_id
    
    return result


def parse_row_based_format(text: str) -> dict:
    """
    Parse row-based format like:
    Name: Huzaifa
    Personal Email: i222669@nu.edu.pk
    Department: Software Developer
    """
    result = {}
    
    # Field mappings (case-insensitive)
    field_mappings = {
        'name': 'name',
        'personal email': 'personal_email',
        'personal_email': 'personal_email',
        'email': 'personal_email',
        'department': 'department',
        'position': 'position',
        'phone': 'phone',
        'phone number': 'phone',
        'phone_number': 'phone',
        'contact': 'phone',
        'contact number': 'phone',
        'manager id': 'manager_id',
        'manager_id': 'manager_id',
        'joining date': 'joining_date',
        'joining_date': 'joining_date',
        'start date': 'joining_date',
        'employee id': 'employee_id',
        'employee_id': 'employee_id'
    }
    
    # Split text into lines
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or ':' not in line:
            continue
        
        # Split on first colon
        parts = line.split(':', 1)
        if len(parts) != 2:
            continue
        
        field_name = parts[0].strip().lower()
        field_value = parts[1].strip()
        
        # Skip empty values
        if not field_value:
            continue
        
        # Map field name to internal field
        internal_field = field_mappings.get(field_name)
        if internal_field:
            if internal_field == 'joining_date':
                # Parse date string to datetime
                result[internal_field] = parse_date_string(field_value)
            else:
                result[internal_field] = field_value
    
    # If we found at least one field, set defaults for missing fields
    if result:
        # Set default joining date if not provided
        if 'joining_date' not in result and 'name' in result:
            result['joining_date'] = get_next_monday()
        
        # Set manager_id based on department if not provided
        if 'department' in result and 'manager_id' not in result:
            result['manager_id'] = get_manager_for_department(result['department'])
    
    return result if result else None
    
def extract_date(text_lower: str) -> str:
    """Extract or infer joining date from text - returns ISO string."""
    # Pattern 1: YYYY-MM-DD or YYYY/MM/DD
    match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text_lower)
    if match:
        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}T00:00:00"
    
    # Pattern 2: Month Day, Year
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    for month_name, month_num in months.items():
        if month_name in text_lower:
            day_match = re.search(rf'{month_name}\s+(\d{{1,2}})', text_lower)
            year_match = re.search(r'(20\d{2})', text_lower)
            if day_match:
                day = day_match.group(1).zfill(2)
                year = year_match.group(1) if year_match else "2025"
                return f"{year}-{str(month_num).zfill(2)}-{day}T00:00:00"
    
    # Default: next Monday (return as ISO string, will be converted by parse_date_string)
    return get_next_monday().isoformat()
    
def extract_name_from_text(text: str) -> str:
    """Extract person name from text (looks for capitalized words)."""
    # Pattern 1: "for [Name]"
    match = re.search(r'\bfor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
    if match:
        return match.group(1)
    
    # Pattern 2: "employee [Name]"
    match = re.search(r'\bemployee\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
    if match:
        return match.group(1)
    
    # Pattern 3: Any sequence of 2+ capitalized words
    match = re.search(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', text)
    if match:
        name = match.group(1)
        # Exclude common words that might be capitalized
        excluded = ["Engineering", "Marketing", "Sales", "Finance", "Human Resources", 
                    "Operations", "Legal", "Monday", "Tuesday", "Wednesday", "Thursday", 
                    "Friday", "Saturday", "Sunday"]
        if name not in excluded:
            return name
    
    return None

def extract_email_from_text(text: str) -> str:
    """Extract email address from text."""
    match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if match:
        return match.group(0)
    return None

def extract_phone_from_text(text: str) -> str:
    """Extract phone number from text."""
    # Pattern: +1-555-0123 or (555) 123-4567 or 555-123-4567
    patterns = [
        r'\+\d{1,3}-\d{3}-\d{4}',
        r'\(\d{3}\)\s*\d{3}-\d{4}',
        r'\d{3}-\d{3}-\d{4}'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return None

def generate_email_from_name(name: str) -> str:
    """Generate email address from name."""
    email_name = name.lower().replace(" ", ".")
    return f"{email_name}@company.com"

def extract_department(text_lower: str) -> str:
    """Extract department from text."""
    departments = {
        "engineering": "Engineering",
        "engineer": "Engineering",
        "hr": "HR",
        "human resources": "HR",
        "sales": "Sales",
        "marketing": "Marketing",
        "finance": "Finance",
        "operations": "Operations",
        "it": "IT",
        "information technology": "IT",
        "legal": "Legal"
    }
    
    for keyword, dept in departments.items():
        if keyword in text_lower:
            return dept
    
    return None

def extract_position(text_lower: str) -> str:
    """Extract job position/title from text."""
    positions = {
        "senior engineer": "Senior Software Engineer",
        "engineer": "Software Engineer",
        "manager": "Manager",
        "director": "Director",
        "analyst": "Analyst",
        "designer": "Designer",
        "developer": "Developer",
        "specialist": "Specialist",
        "coordinator": "Coordinator",
        "executive": "Executive",
        "lead": "Team Lead"
    }
    
    for keyword, position in positions.items():
        if keyword in text_lower:
            return position
    
    return None

def get_next_monday() -> datetime:
    """Get the date of next Monday."""
    today = datetime.utcnow()
    days_ahead = 0 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)

def get_manager_for_department(department: str) -> str:
    """Map department to manager ID."""
    manager_map = {
        "Engineering": "MGR001",
        "HR": "MGR002",
        "Sales": "MGR003",
        "Marketing": "MGR004",
        "Finance": "MGR005",
        "Operations": "MGR006",
        "IT": "MGR007",
        "Legal": "MGR008"
    }
    return manager_map.get(department, "MGR001")

def extract_employee_id(text_lower: str) -> str:
    """Extract employee ID from query."""
    # Pattern 1: employee_id: emp-xxx
    match = re.search(r'employee[_\s]?id[:\s]+([a-f0-9-]+)', text_lower)
    if match:
        return match.group(1)
    
    # Pattern 2: emp-xxx anywhere
    match = re.search(r'emp[-_]([a-f0-9-]+)', text_lower)
    if match:
        return f"emp-{match.group(1)}"
    
    # Pattern 3: uuid pattern
    match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', text_lower)
    if match:
        return match.group(1)
    
    return None

@app.get("/employees")
async def list_employees():
    """List all employees"""
    employees = db.get_all_employees()
    return {
        "total": len(employees),
        "employees": [e.to_dict() for e in employees]
    }

@app.get("/employees/{employee_id}")
async def get_employee(employee_id: str):
    """Get employee details"""
    employee = db.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee.to_dict()

@app.get("/dashboard")
async def get_dashboard():
    """Get dashboard overview"""
    all_progress = progress_monitor.get_all_employees_progress()
    
    return {
        "summary": all_progress["summary"],
        "employees": all_progress["employees"],
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)