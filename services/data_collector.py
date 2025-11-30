from datetime import datetime
from typing import Optional
from application.database import Database, Employee

class DataCollector:
    """Handles employee data collection and validation."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create_employee(
        self,
        name: str,
        personal_email: str,
        department: str,
        joining_date: datetime,
        manager_id: Optional[str] = None,
        phone: Optional[str] = None,
        position: Optional[str] = None
    ) -> Employee:
        """
        Create a new employee record with validation.
        
        Args:
            name: Full name of employee
            personal_email: Personal email address provided by user
            department: Department (Engineering, HR, Sales, etc.)
            joining_date: datetime object
            manager_id: ID of assigned manager
            phone: Contact phone number
            position: Job title/position
        
        Returns:
            Employee object with generated ID
        """
        if not name or not personal_email or not department:
            raise ValueError("Name, personal email, and department are required")
        
        if '@' not in personal_email:
            raise ValueError("Invalid email format")
        
        existing = self.db.get_employee_by_personal_email(personal_email)
        if existing:
            raise ValueError(f"Employee with personal email {personal_email} already exists")
        
        if not isinstance(joining_date, datetime):
            raise ValueError("joining_date must be a datetime object")
        
        employee = Employee(
            name=name,
            personal_email=personal_email,
            email=None,
            department=department,
            joining_date=joining_date,
            manager_id=manager_id,
            phone=phone,
            position=position,
            status="active"
        )
        
        employee = self.db.create_employee(employee)
        return employee
    
    def get_employee_details(self, employee_id: str) -> Optional[Employee]:
        """Retrieve employee details by ID."""
        return self.db.get_employee(employee_id)
    
    def update_employee_info(self, employee_id: str, **kwargs) -> Optional[Employee]:
        """Update employee information."""
        return self.db.update_employee(employee_id, **kwargs)
    
    def validate_department(self, department: str) -> bool:
        """Validate if department exists in organization."""
        valid_departments = [
            "Engineering", "HR", "Sales", "Marketing", 
            "Finance", "Operations", "IT", "Legal"
        ]
        return department in valid_departments