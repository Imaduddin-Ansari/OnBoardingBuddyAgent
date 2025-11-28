"""
Database module with SQLAlchemy models and operations
File: database.py
"""
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import List, Optional
import enum
import uuid

Base = declarative_base()

# ============================================================================
# ENUMS
# ============================================================================

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"

class AccessType(str, enum.Enum):
    EMAIL = "email"
    SYSTEM_CREDENTIALS = "system_credentials"
    WORKSPACE = "workspace"
    VPN = "vpn"
    BUILDING = "building_access"

class AccessStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class NotificationType(str, enum.Enum):
    WELCOME = "welcome"
    TASK_REMINDER = "task_reminder"
    TASK_OVERDUE = "task_overdue"
    ACCESS_GRANTED = "access_granted"
    COMPLETION = "completion"

# ============================================================================
# MODELS
# ============================================================================

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String)
    department = Column(String, nullable=False)
    position = Column(String)
    joining_date = Column(DateTime, nullable=False)
    manager_id = Column(String)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "department": self.department,
            "position": self.position,
            "joining_date": self.joining_date.isoformat() if self.joining_date else None,
            "manager_id": self.manager_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)  # policy, equipment, training, etc.
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    priority = Column(Integer, default=1)  # 1=high, 2=medium, 3=low
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class AccessRequest(Base):
    __tablename__ = "access_requests"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, nullable=False)
    access_type = Column(SQLEnum(AccessType), nullable=False)
    status = Column(SQLEnum(AccessStatus), default=AccessStatus.PENDING)
    requested_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    details = Column(Text)
    error_message = Column(Text)
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "access_type": self.access_type.value if isinstance(self.access_type, AccessType) else self.access_type,
            "status": self.status.value if isinstance(self.status, AccessStatus) else self.status,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "details": self.details,
            "error_message": self.error_message
        }

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, nullable=False)
    type = Column(SQLEnum(NotificationType), nullable=False)
    subject = Column(String)
    message = Column(Text)
    sent_at = Column(DateTime)
    status = Column(String, default="pending")  # pending, sent, failed
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "type": self.type.value if isinstance(self.type, NotificationType) else self.type,
            "subject": self.subject,
            "message": self.message,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# ============================================================================
# DATABASE CLASS
# ============================================================================

class Database:
    def __init__(self, db_url: str = "sqlite:///onboarding.db"):
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    # Employee operations
    def create_employee(self, employee: Employee) -> Employee:
        session = self.get_session()
        try:
            session.add(employee)
            session.commit()
            session.refresh(employee)
            return employee
        finally:
            session.close()
    
    def get_employee(self, employee_id: str) -> Optional[Employee]:
        session = self.get_session()
        try:
            return session.query(Employee).filter(Employee.id == employee_id).first()
        finally:
            session.close()
    
    def get_all_employees(self) -> List[Employee]:
        session = self.get_session()
        try:
            return session.query(Employee).all()
        finally:
            session.close()
    
    def update_employee(self, employee_id: str, **kwargs) -> Optional[Employee]:
        session = self.get_session()
        try:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            if employee:
                for key, value in kwargs.items():
                    setattr(employee, key, value)
                session.commit()
                session.refresh(employee)
            return employee
        finally:
            session.close()
    
    # Task operations
    def create_task(self, task: Task) -> Task:
        session = self.get_session()
        try:
            session.add(task)
            session.commit()
            session.refresh(task)
            return task
        finally:
            session.close()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        session = self.get_session()
        try:
            return session.query(Task).filter(Task.id == task_id).first()
        finally:
            session.close()
    
    def get_tasks_by_employee(self, employee_id: str) -> List[Task]:
        session = self.get_session()
        try:
            return session.query(Task).filter(Task.employee_id == employee_id).all()
        finally:
            session.close()
    
    def get_pending_tasks(self, employee_id: str = None) -> List[Task]:
        session = self.get_session()
        try:
            query = session.query(Task).filter(Task.status == TaskStatus.PENDING)
            if employee_id:
                query = query.filter(Task.employee_id == employee_id)
            return query.all()
        finally:
            session.close()
    
    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        session = self.get_session()
        try:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                for key, value in kwargs.items():
                    setattr(task, key, value)
                session.commit()
                session.refresh(task)
            return task
        finally:
            session.close()
    
    # Access request operations
    def create_access_request(self, access_request: AccessRequest) -> AccessRequest:
        session = self.get_session()
        try:
            session.add(access_request)
            session.commit()
            session.refresh(access_request)
            return access_request
        finally:
            session.close()
    
    def get_access_requests(self, employee_id: str) -> List[AccessRequest]:
        session = self.get_session()
        try:
            return session.query(AccessRequest).filter(AccessRequest.employee_id == employee_id).all()
        finally:
            session.close()
    
    def update_access_request(self, request_id: str, **kwargs) -> Optional[AccessRequest]:
        session = self.get_session()
        try:
            request = session.query(AccessRequest).filter(AccessRequest.id == request_id).first()
            if request:
                for key, value in kwargs.items():
                    setattr(request, key, value)
                session.commit()
                session.refresh(request)
            return request
        finally:
            session.close()
    
    # Notification operations
    def create_notification(self, notification: Notification) -> Notification:
        session = self.get_session()
        try:
            session.add(notification)
            session.commit()
            session.refresh(notification)
            return notification
        finally:
            session.close()
    
    def get_pending_notifications(self) -> List[Notification]:
        session = self.get_session()
        try:
            return session.query(Notification).filter(Notification.status == "pending").all()
        finally:
            session.close()
    
    def update_notification(self, notification_id: str, **kwargs) -> Optional[Notification]:
        session = self.get_session()
        try:
            notification = session.query(Notification).filter(Notification.id == notification_id).first()
            if notification:
                for key, value in kwargs.items():
                    setattr(notification, key, value)
                session.commit()
                session.refresh(notification)
            return notification
        finally:
            session.close()