"""
Service Module 1: Data Collection
Gathers new employee details including personal information, 
department, joining date, and assigned manager.
File: services/data_collector.py
"""
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
        email: str,
        department: str,
        joining_date: str,
        manager_id: Optional[str] = None,
        phone: Optional[str] = None,
        position: Optional[str] = None
    ) -> Employee:
        """
        Create a new employee record with validation.
        
        Args:
            name: Full name of employee
            email: Work email address
            department: Department (Engineering, HR, Sales, etc.)
            joining_date: ISO format date string or datetime
            manager_id: ID of assigned manager
            phone: Contact phone number
            position: Job title/position
            
        Returns:
            Employee object with generated ID
        """
        # Validate required fields
        if not name or not email or not department:
            raise ValueError("Name, email, and department are required")
        
        # Validate email format
        if '@' not in email:
            raise ValueError("Invalid email format")
        
        # Parse joining date
        if isinstance(joining_date, str):
            try:
                joining_date = datetime.fromisoformat(joining_date.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("Invalid date format. Use ISO format (YYYY-MM-DD)")
        
        # Create employee object
        employee = Employee(
            name=name,
            email=email,
            department=department,
            joining_date=joining_date,
            manager_id=manager_id,
            phone=phone,
            position=position,
            status="active"
        )
        
        # Save to database
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