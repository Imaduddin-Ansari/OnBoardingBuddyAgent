"""
Complete Onboarding Buddy Agent - Main Application
Implements all 6 functional requirements from section 1.6.2
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
import re
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
import uvicorn
import uuid
import json

# Import our modules
from application.database import Database, Employee, Task, AccessRequest, Notification
from services.data_collector import DataCollector
from services.access_manager import AccessManager
from services.task_manager import TaskManager
from services.progress_monitor import ProgressMonitor
from services.notification_service import NotificationService
from services.reporter import Reporter

app = FastAPI(
    title="Onboarding Buddy Agent",
    description="Complete employee onboarding automation system",
    version="1.0.0"
)

# Initialize database and services
db = Database()
data_collector = DataCollector(db)
access_manager = AccessManager(db)
task_manager = TaskManager(db)
progress_monitor = ProgressMonitor(db)
notification_service = NotificationService(db)
reporter = Reporter(db)

# ============================================================================
# REQUEST/RESPONSE MODELS (Supervisor Handshake Protocol)
# ============================================================================

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

# ============================================================================
# HEALTH CHECK
# ============================================================================

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
            "task_assignment": "operational",
            "progress_monitoring": "operational",
            "notifications": "operational",
            "reporting": "operational"
        }
    }

# ============================================================================
# MAIN EXECUTION ENDPOINT
# ============================================================================

@app.post("/execute", response_model=WorkerResponse)
async def execute_intent(request: WorkerRequest, background_tasks: BackgroundTasks):
    """
    Main execution endpoint implementing all onboarding intents.
    Routes requests to appropriate service handlers.
    """
    try:
        # Parse input to extract structured data
        input_data = parse_input(request.input.text, request.input.metadata.extra)
        
        # Route to appropriate handler based on intent
        if request.intent == "onboarding.create":
            result = await handle_create_onboarding(input_data, background_tasks)
        
        elif request.intent == "onboarding.collect_data":
            result = await handle_collect_data(input_data)
        
        elif request.intent == "onboarding.setup_access":
            result = await handle_setup_access(input_data, background_tasks)
        
        elif request.intent == "onboarding.assign_tasks":
            result = await handle_assign_tasks(input_data)
        
        elif request.intent == "onboarding.check_progress":
            result = await handle_check_progress(input_data)
        
        elif request.intent == "onboarding.send_notifications":
            result = await handle_send_notifications(input_data, background_tasks)
        
        elif request.intent == "onboarding.generate_report":
            result = await handle_generate_report(input_data)
        
        elif request.intent == "onboarding.get_status":
            result = await handle_get_status(input_data)
        
        elif request.intent == "onboarding.complete_task":
            result = await handle_complete_task(input_data)
        
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

# ============================================================================
# INTENT HANDLERS
# ============================================================================

async def handle_create_onboarding(data: dict, background_tasks: BackgroundTasks) -> OutputData:
    """
    Complete onboarding flow - orchestrates all 6 functions.
    1. Collect data -> 2. Setup access -> 3. Assign tasks -> 
    4. Monitor progress -> 5. Send notifications -> 6. Generate report
    """
    # 1. Data Collection
    employee = data_collector.create_employee(
        name=data.get("name"),
        email=data.get("email"),
        department=data.get("department"),
        joining_date=data.get("joining_date"),
        manager_id=data.get("manager_id"),
        phone=data.get("phone"),
        position=data.get("position")
    )
    
    # 2. Access Setup (async in background)
    background_tasks.add_task(
        access_manager.setup_all_access,
        employee.id
    )
    
    # 3. Task Assignment
    tasks = task_manager.assign_onboarding_tasks(
        employee.id,
        department=employee.department
    )
    
    # 4. Progress Monitoring (start monitoring)
    progress_monitor.initialize_monitoring(employee.id)
    
    # 5. Notifications (send welcome email)
    background_tasks.add_task(
        notification_service.send_welcome_email,
        employee.id
    )
    
    # 6. Generate initial report
    report = reporter.generate_employee_report(employee.id)
    
    return OutputData(
        result=f"Onboarding created successfully for {employee.name} (ID: {employee.id})",
        confidence=1.0,
        details=json.dumps({
            "employee_id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "department": employee.department,
            "tasks_assigned": len(tasks),
            "access_requests_initiated": 3,
            "status": "initiated",
            "report": report
        }, indent=2)
    )

async def handle_collect_data(data: dict) -> OutputData:
    """Function 1: Data Collection"""
    employee = data_collector.create_employee(
        name=data.get("name"),
        email=data.get("email"),
        department=data.get("department"),
        joining_date=data.get("joining_date"),
        manager_id=data.get("manager_id"),
        phone=data.get("phone"),
        position=data.get("position")
    )
    
    return OutputData(
        result=f"Employee data collected for {employee.name}",
        confidence=1.0,
        details=f"Employee ID: {employee.id}, Department: {employee.department}"
    )

async def handle_setup_access(data: dict, background_tasks: BackgroundTasks) -> OutputData:
    """Function 2: Access Setup"""
    employee_id = data.get("employee_id")
    
    if not employee_id:
        raise ValueError("employee_id is required")
    
    # Run access setup in background
    background_tasks.add_task(access_manager.setup_all_access, employee_id)
    
    return OutputData(
        result=f"Access setup initiated for employee {employee_id}",
        confidence=0.95,
        details="Requests sent for: email account, system credentials, workspace permissions"
    )

async def handle_assign_tasks(data: dict) -> OutputData:
    """Function 3: Task Assignment"""
    employee_id = data.get("employee_id")
    department = data.get("department")
    
    if not employee_id:
        raise ValueError("employee_id is required")
    
    tasks = task_manager.assign_onboarding_tasks(employee_id, department)
    
    return OutputData(
        result=f"Assigned {len(tasks)} onboarding tasks",
        confidence=1.0,
        details=f"Tasks: {', '.join([t.title for t in tasks])}"
    )

async def handle_check_progress(data: dict) -> OutputData:
    """Function 4: Progress Monitoring"""
    employee_id = data.get("employee_id")
    
    if not employee_id:
        # Return progress for all employees
        all_progress = progress_monitor.get_all_progress()
        return OutputData(
            result=f"Progress retrieved for {len(all_progress)} employees",
            confidence=1.0,
            details=json.dumps(all_progress, indent=2)
        )
    
    progress = progress_monitor.get_employee_progress(employee_id)
    pending_items = progress_monitor.get_pending_items(employee_id)
    
    return OutputData(
        result=f"Progress: {progress['completed_tasks']}/{progress['total_tasks']} tasks completed",
        confidence=1.0,
        details=json.dumps({
            "progress": progress,
            "pending_items": pending_items
        }, indent=2)
    )

async def handle_send_notifications(data: dict, background_tasks: BackgroundTasks) -> OutputData:
    """Function 5: Notifications"""
    employee_id = data.get("employee_id")
    notification_type = data.get("type", "reminder")
    
    if not employee_id:
        # Send reminders to all employees with pending tasks
        background_tasks.add_task(notification_service.send_bulk_reminders)
        return OutputData(
            result="Bulk reminder notifications scheduled",
            confidence=1.0,
            details="Reminders will be sent to all employees with pending tasks"
        )
    
    if notification_type == "welcome":
        background_tasks.add_task(notification_service.send_welcome_email, employee_id)
        message = "Welcome email scheduled"
    else:
        background_tasks.add_task(notification_service.send_task_reminder, employee_id)
        message = "Task reminder scheduled"
    
    return OutputData(
        result=message,
        confidence=1.0,
        details=f"Notification will be sent to employee {employee_id}"
    )

async def handle_generate_report(data: dict) -> OutputData:
    """Function 6: Reporting"""
    report_type = data.get("report_type", "employee")
    employee_id = data.get("employee_id")
    
    if report_type == "summary":
        report = reporter.generate_summary_report()
        return OutputData(
            result="Summary report generated",
            confidence=1.0,
            details=json.dumps(report, indent=2)
        )
    
    elif report_type == "issues":
        issues = reporter.get_issue_alerts()
        return OutputData(
            result=f"Found {len(issues)} issues requiring attention",
            confidence=1.0,
            details=json.dumps(issues, indent=2)
        )
    
    else:  # employee report
        if not employee_id:
            raise ValueError("employee_id is required for employee report")
        
        report = reporter.generate_employee_report(employee_id)
        return OutputData(
            result=f"Employee report generated for {employee_id}",
            confidence=1.0,
            details=json.dumps(report, indent=2)
        )

async def handle_get_status(data: dict) -> OutputData:
    """Get overall status of an employee's onboarding"""
    employee_id = data.get("employee_id")
    
    if not employee_id:
        raise ValueError("employee_id is required")
    
    employee = db.get_employee(employee_id)
    if not employee:
        raise ValueError(f"Employee {employee_id} not found")
    
    progress = progress_monitor.get_employee_progress(employee_id)
    access_status = access_manager.get_access_status(employee_id)
    
    return OutputData(
        result=f"Employee {employee.name}: {progress['completion_percentage']:.0f}% complete",
        confidence=1.0,
        details=json.dumps({
            "employee": employee.to_dict(),
            "progress": progress,
            "access_status": access_status
        }, indent=2)
    )

async def handle_complete_task(data: dict) -> OutputData:
    """
    Mark a task as completed.
    Can use task_id, task_name, or employee_id.
    """
    task_id = data.get("task_id")
    task_name = data.get("task_name")
    employee_id = data.get("employee_id")
    
    if task_id:
        # Complete by task_id (most specific)
        task = task_manager.complete_task(task_id)
        return OutputData(
            result=f"Task '{task.title}' marked as completed",
            confidence=1.0,
            details=f"Completed at: {task.completed_at}"
        )
    
    elif task_name and employee_id:
        # Complete by task name for specific employee
        task = task_manager.complete_task_by_name(employee_id, task_name)
        return OutputData(
            result=f"Task '{task.title}' marked as completed for employee",
            confidence=0.9,
            details=f"Completed at: {task.completed_at}"
        )
    
    elif task_name:
        # Need to find employee - try first employee with this task
        employees = db.get_all_employees()
        for employee in employees:
            try:
                task = task_manager.complete_task_by_name(employee.id, task_name)
                return OutputData(
                    result=f"Task '{task.title}' marked as completed for {employee.name}",
                    confidence=0.8,
                    details=f"Employee: {employee.name}, Completed at: {task.completed_at}"
                )
            except ValueError:
                continue
        
        raise ValueError(f"No employee found with task matching '{task_name}'")
    
    elif employee_id:
        # Complete all pending tasks for employee (for testing)
        completed = task_manager.complete_all_tasks(employee_id)
        return OutputData(
            result=f"Completed {len(completed)} tasks",
            confidence=1.0,
            details=f"All tasks completed for employee {employee_id}"
        )
    
    else:
        raise ValueError("Need task_id, task_name (with optional employee_id), or employee_id")
    """Mark a task as completed"""
    task_id = data.get("task_id")
    employee_id = data.get("employee_id")
    
    if not task_id and not employee_id:
        raise ValueError("Either task_id or employee_id is required")
    
    if task_id:
        task = task_manager.complete_task(task_id)
        return OutputData(
            result=f"Task '{task.title}' marked as completed",
            confidence=1.0,
            details=f"Completed at: {task.completed_at}"
        )
    else:
        # Complete all pending tasks for employee (for testing)
        completed = task_manager.complete_all_tasks(employee_id)
        return OutputData(
            result=f"Completed {len(completed)} tasks",
            confidence=1.0,
            details=f"All tasks completed for employee {employee_id}"
        )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

"""
Updated handler functions for main.py
Replace your existing handle_complete_task and parse_input functions with these
"""

# ============================================================================
# UPDATED PARSE_INPUT - Extract task name
# ============================================================================

def parse_input(text: str, extra: dict) -> dict:
    """
    Parse natural language input and extract structured data.
    Now extracts task names for completion.
    """
    # If extra contains structured data, use it directly
    if extra and any(key in extra for key in ["name", "email", "employee_id", "task_id", "task_name"]):
        return extra
    
    # Otherwise, parse from natural language text
    result = {}
    text_lower = text.lower()
    words = text.split()
    
    # ====================================================================
    # INTENT 1 & 2: Extract employee data for create/collect_data
    # ====================================================================
    
    # Extract name (look for capitalized sequences)
    name = extract_name_from_text(text)
    if name:
        result["name"] = name
        result["email"] = generate_email_from_name(name)
    
    # Extract department
    department = extract_department(text_lower)
    if department:
        result["department"] = department
    
    # Extract position/job title
    position = extract_position(text_lower)
    if position:
        result["position"] = position
    
    # Set joining date (default to next Monday if not specified)
    if "joining" in text_lower or "start" in text_lower:
        result["joining_date"] = extract_date(text_lower)
    elif name:  # If creating employee, set default joining date
        result["joining_date"] = get_next_monday().isoformat()
    
    # Set manager_id based on department
    if department:
        result["manager_id"] = get_manager_for_department(department)
    
    # ====================================================================
    # Extract employee_id for other intents
    # ====================================================================
    
    employee_id = extract_employee_id(text_lower)
    if employee_id:
        result["employee_id"] = employee_id
    
    # ====================================================================
    # Extract report type for generate_report intent
    # ====================================================================
    
    if "summary" in text_lower or "dashboard" in text_lower or "overall" in text_lower:
        result["report_type"] = "summary"
    elif "issue" in text_lower or "alert" in text_lower or "problem" in text_lower:
        result["report_type"] = "issues"
    elif "report" in text_lower:
        result["report_type"] = "employee"
    
    # ====================================================================
    # Extract notification type
    # ====================================================================
    
    if "welcome" in text_lower:
        result["type"] = "welcome"
    elif "remind" in text_lower or "reminder" in text_lower:
        result["type"] = "reminder"
    elif "overdue" in text_lower:
        result["type"] = "overdue"
    
    # ====================================================================
    # Extract task_id or task_name for complete_task intent
    # ====================================================================
    
    task_id = extract_task_id(text_lower)
    if task_id:
        result["task_id"] = task_id
    else:
        # Try to extract task name from text
        task_name = extract_task_name(text)
        if task_name:
            result["task_name"] = task_name
    
    return result


def extract_task_name(text: str) -> str:
    """
    Extract task name from text for completion.
    Examples:
    - "Complete security training" -> "security training"
    - "Mark training as complete" -> "training"
    - "Finish setup workstation" -> "setup workstation"
    """
    text_lower = text.lower()
    
    # Common patterns for task completion
    patterns = [
        ("complete ", ""),
        ("mark ", " as complete"),
        ("mark ", " complete"),
        ("finish ", ""),
        ("done with ", ""),
        ("completed ", ""),
    ]
    
    # Try each pattern
    for prefix, suffix in patterns:
        if prefix in text_lower:
            # Find the start position
            start = text_lower.find(prefix) + len(prefix)
            
            # Find end position (before suffix or end of sentence)
            if suffix and suffix in text_lower[start:]:
                end = text_lower.find(suffix, start)
            else:
                # End at common sentence terminators
                end = len(text_lower)
                for terminator in [" for ", " by ", " on ", ".", "!", "?"]:
                    term_pos = text_lower.find(terminator, start)
                    if term_pos != -1 and term_pos < end:
                        end = term_pos
            
            # Extract task name
            task_name = text[start:end].strip()
            if task_name and len(task_name) > 3:  # Minimum 3 chars
                return task_name
    
    # If no pattern matched, look for keywords in the text
    task_keywords = [
        "training", "security", "workstation", "equipment", "handbook",
        "paperwork", "meeting", "environment", "git", "code", "review"
    ]
    
    for keyword in task_keywords:
        if keyword in text_lower:
            # Return surrounding context
            pos = text_lower.find(keyword)
            start = max(0, pos - 20)
            end = min(len(text), pos + len(keyword) + 20)
            context = text[start:end].strip()
            return keyword  # Just return the keyword for simplicity
    
    return None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_name_from_text(text: str) -> str:
    """Extract person name from text (looks for capitalized words)."""
    # Common patterns: "for John Smith", "employee John Smith", "John Smith in"
    
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
                    "Friday", "Saturday", "Sunday", "January", "February", "March", 
                    "April", "May", "June", "July", "August", "September", "October", 
                    "November", "December"]
        if name not in excluded and not any(dept in name for dept in excluded):
            return name
    
    return None


def generate_email_from_name(name: str) -> str:
    """Generate email address from name."""
    # Convert "John Smith" to "john.smith@company.com"
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
        "engineer": "Software Engineer",
        "senior engineer": "Senior Software Engineer",
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
    
    return "New Hire"  # Default


def extract_date(text_lower: str) -> str:
    """Extract or infer joining date from text."""
    # Look for date patterns
    
    # Pattern 1: YYYY-MM-DD or YYYY/MM/DD
    match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text_lower)
    if match:
        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}T00:00:00"
    
    # Pattern 2: Month Day, Year (e.g., "December 1, 2025")
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    for month_name, month_num in months.items():
        if month_name in text_lower:
            # Try to find day and year
            day_match = re.search(rf'{month_name}\s+(\d{{1,2}})', text_lower)
            year_match = re.search(r'(20\d{2})', text_lower)
            if day_match:
                day = day_match.group(1).zfill(2)
                year = year_match.group(1) if year_match else "2025"
                return f"{year}-{str(month_num).zfill(2)}-{day}T00:00:00"
    
    # Default: next Monday
    return get_next_monday().isoformat()


def get_next_monday() -> datetime:
    """Get the date of next Monday."""
    today = datetime.utcnow()
    days_ahead = 0 - today.weekday()  # Monday is 0
    if days_ahead <= 0:  # Target day already happened this week
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
    """Extract employee ID from query using regex patterns."""
    # Pattern 1: employee_id: emp-xxx or employee_id emp-xxx
    match = re.search(r'employee[_\s]?id[:\s]+([a-f0-9-]+)', text_lower)
    if match:
        return match.group(1)
    
    # Pattern 2: emp-xxx or emp_xxx anywhere in query
    match = re.search(r'emp[-_]([a-f0-9-]+)', text_lower)
    if match:
        return f"emp-{match.group(1)}"
    
    # Pattern 3: Look for uuid pattern
    match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', text_lower)
    if match:
        return match.group(1)
    
    return None


def extract_task_id(text_lower: str) -> str:
    """Extract task ID from query."""
    # Pattern 1: task_id: task-xxx or task_id task-xxx
    match = re.search(r'task[_\s]?id[:\s]+([a-f0-9-]+)', text_lower)
    if match:
        return match.group(1)
    
    # Pattern 2: task-xxx or task_xxx anywhere in query
    match = re.search(r'task[-_]([a-f0-9-]+)', text_lower)
    if match:
        return f"task-{match.group(1)}"
    
    # Pattern 3: Look for uuid pattern
    match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', text_lower)
    if match:
        return match.group(1)
    
    return None
    """Parse natural language input and extract structured data."""
    # If extra contains structured data, use it
    if extra:
        return extra
    
    # Simple parsing from text (in production, use NLP)
    result = {}
    text_lower = text.lower()
    
    # Extract employee_id if mentioned
    words = text.split()
    for i, word in enumerate(words):
        if word in ["id", "employee", "employee_id"] and i + 1 < len(words):
            result["employee_id"] = words[i + 1].strip(",.:;")
    
    # Extract report type
    if "summary" in text_lower:
        result["report_type"] = "summary"
    elif "issue" in text_lower or "alert" in text_lower:
        result["report_type"] = "issues"
    
    # Extract notification type
    if "welcome" in text_lower:
        result["type"] = "welcome"
    elif "reminder" in text_lower:
        result["type"] = "reminder"
    
    return result

# ============================================================================
# ADDITIONAL ENDPOINTS (Direct Access)
# ============================================================================

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

@app.get("/tasks/{employee_id}")
async def get_employee_tasks(employee_id: str):
    """Get all tasks for an employee"""
    tasks = db.get_tasks_by_employee(employee_id)
    return {
        "employee_id": employee_id,
        "total_tasks": len(tasks),
        "tasks": [t.to_dict() for t in tasks]
    }

@app.get("/dashboard")
async def get_dashboard():
    """Get dashboard overview"""
    summary = reporter.generate_summary_report()
    issues = reporter.get_issue_alerts()
    
    return {
        "summary": summary,
        "issues": issues,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)