"""
Service Module 3: Task Assignment
Allocates mandatory onboarding tasks (policy acknowledgment, 
equipment checklist, training modules).
File: services/task_manager.py
"""
from datetime import datetime, timedelta
from typing import List, Optional
from application.database import Database, Task, TaskStatus

class TaskManager:
    """Manages onboarding task assignment and tracking."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def assign_onboarding_tasks(self, employee_id: str, department: Optional[str] = None) -> List[Task]:
        """
        Assign all mandatory onboarding tasks to a new employee.
        
        Args:
            employee_id: ID of the employee
            department: Department name for department-specific tasks
            
        Returns:
            List of Task objects
        """
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
        
        tasks = []
        
        # 1. Core onboarding tasks (for all employees)
        core_tasks = self._get_core_tasks(employee_id)
        tasks.extend(core_tasks)
        
        # 2. Department-specific tasks
        if department:
            dept_tasks = self._get_department_tasks(employee_id, department)
            tasks.extend(dept_tasks)
        
        # 3. Role-specific training
        if employee.position:
            training_tasks = self._get_training_tasks(employee_id, employee.position)
            tasks.extend(training_tasks)
        
        return tasks
    
    def _get_core_tasks(self, employee_id: str) -> List[Task]:
        """Create core onboarding tasks required for all employees."""
        base_date = datetime.utcnow()
        
        core_task_data = [
            {
                "title": "Complete Company Policy Acknowledgment",
                "description": "Read and acknowledge the employee handbook, code of conduct, and company policies.",
                "category": "policy",
                "priority": 1,
                "due_days": 3
            },
            {
                "title": "Equipment Checklist - Verify Laptop and Accessories",
                "description": "Confirm receipt of laptop, charger, mouse, keyboard, and other equipment.",
                "category": "equipment",
                "priority": 1,
                "due_days": 1
            },
            {
                "title": "Setup Workstation and Login Credentials",
                "description": "Setup your workstation, test all login credentials, and verify access to systems.",
                "category": "equipment",
                "priority": 1,
                "due_days": 2
            },
            {
                "title": "Complete Information Security Training",
                "description": "Complete mandatory cybersecurity awareness training module.",
                "category": "training",
                "priority": 1,
                "due_days": 5
            },
            {
                "title": "Review Emergency Procedures",
                "description": "Review building evacuation procedures and emergency contacts.",
                "category": "policy",
                "priority": 2,
                "due_days": 3
            },
            {
                "title": "Schedule 1:1 Meeting with Manager",
                "description": "Schedule and complete initial 1:1 meeting with your direct manager.",
                "category": "meeting",
                "priority": 1,
                "due_days": 2
            },
            {
                "title": "Complete HR Onboarding Forms",
                "description": "Fill out tax forms, benefits enrollment, and emergency contact information.",
                "category": "policy",
                "priority": 1,
                "due_days": 7
            },
            {
                "title": "Join Company Communication Channels",
                "description": "Join Slack workspace, team channels, and company-wide groups.",
                "category": "communication",
                "priority": 2,
                "due_days": 1
            }
        ]
        
        tasks = []
        for task_data in core_task_data:
            task = Task(
                employee_id=employee_id,
                title=task_data["title"],
                description=task_data["description"],
                category=task_data["category"],
                priority=task_data["priority"],
                due_date=base_date + timedelta(days=task_data["due_days"]),
                status=TaskStatus.PENDING
            )
            task = self.db.create_task(task)
            tasks.append(task)
        
        return tasks
    
    def _get_department_tasks(self, employee_id: str, department: str) -> List[Task]:
        """Create department-specific onboarding tasks."""
        base_date = datetime.utcnow()
        
        dept_tasks_map = {
            "Engineering": [
                ("Setup Development Environment", "Install and configure IDE, Git, Docker, and other dev tools.", "technical", 3),
                ("Complete Code Review Training", "Learn code review process and best practices.", "training", 5),
                ("Review Architecture Documentation", "Study system architecture and technical documentation.", "technical", 7)
            ],
            "Sales": [
                ("Complete Product Training", "Learn about all products and services.", "training", 5),
                ("Shadow Sales Calls", "Join 3-5 sales calls to learn the process.", "training", 10),
                ("Setup CRM Account", "Configure Salesforce and learn pipeline management.", "technical", 2)
            ],
            "Marketing": [
                ("Review Brand Guidelines", "Study company branding, voice, and style guide.", "policy", 3),
                ("Setup Marketing Tools", "Configure access to marketing automation and analytics tools.", "technical", 2),
                ("Meet Content Team", "Introduction meeting with content and design teams.", "meeting", 5)
            ],
            "HR": [
                ("HRIS Training", "Learn to use HR information system.", "training", 3),
                ("Review Hiring Process", "Understand recruitment and hiring procedures.", "policy", 5),
                ("Complete Compliance Training", "Employment law and compliance certification.", "training", 7)
            ]
        }
        
        tasks = []
        task_data_list = dept_tasks_map.get(department, [])
        
        for title, description, category, due_days in task_data_list:
            task = Task(
                employee_id=employee_id,
                title=title,
                description=description,
                category=category,
                priority=2,
                due_date=base_date + timedelta(days=due_days),
                status=TaskStatus.PENDING
            )
            task = self.db.create_task(task)
            tasks.append(task)
        
        return tasks
    
    def _get_training_tasks(self, employee_id: str, position: str) -> List[Task]:
        """Create role-specific training tasks."""
        base_date = datetime.utcnow()
        
        # Generic training task
        task = Task(
            employee_id=employee_id,
            title=f"Complete {position} Role Training",
            description=f"Complete all required training modules for {position} position.",
            category="training",
            priority=2,
            due_date=base_date + timedelta(days=14),
            status=TaskStatus.PENDING
        )
        task = self.db.create_task(task)
        
        return [task]
    
    def complete_task(self, task_id: str) -> Task:
        """Mark a task as completed."""
        task = self.db.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            completed_at=datetime.utcnow()
        )
        if not task:
            raise ValueError(f"Task {task_id} not found")
        return task
    
    def complete_all_tasks(self, employee_id: str) -> List[Task]:
        """Complete all pending tasks for an employee (testing helper)."""
        tasks = self.db.get_pending_tasks(employee_id)
        completed = []
        for task in tasks:
            updated = self.db.update_task(
                task.id,
                status=TaskStatus.COMPLETED,
                completed_at=datetime.utcnow()
            )
            completed.append(updated)
        return completed
    
    def get_employee_tasks(self, employee_id: str) -> List[Task]:
        """Get all tasks for an employee."""
        return self.db.get_tasks_by_employee(employee_id)
    
    def get_overdue_tasks(self, employee_id: Optional[str] = None) -> List[Task]:
        """Get overdue tasks."""
        if employee_id:
            tasks = self.db.get_tasks_by_employee(employee_id)
        else:
            tasks = self.db.get_pending_tasks()
        
        now = datetime.utcnow()
        overdue = [
            task for task in tasks 
            if task.status == TaskStatus.PENDING and task.due_date and task.due_date < now
        ]
        return overdue