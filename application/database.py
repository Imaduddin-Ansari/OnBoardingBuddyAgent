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

class NotificationType(str, enum.Enum):
    WELCOME = "welcome"
    ACCESS_GRANTED = "access_granted"
    COMPLETION = "completion"

# ============================================================================
# MODELS
# ============================================================================

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    personal_email = Column(String, nullable=False, unique=True)  # NEW: User-provided email
    email = Column(String, unique=True)  # CHANGED: Generated company email (nullable until generated)
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
            "personal_email": self.personal_email,
            "email": self.email,  # Company email
            "phone": self.phone,
            "department": self.department,
            "position": self.position,
            "joining_date": self.joining_date.isoformat() if self.joining_date else None,
            "manager_id": self.manager_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
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
    
    # ============================================================================
    # EMPLOYEE OPERATIONS
    # ============================================================================
    
    def create_employee(self, employee: Employee) -> Employee:
        """Create a new employee record."""
        session = self.get_session()
        try:
            session.add(employee)
            session.commit()
            session.refresh(employee)
            return employee
        finally:
            session.close()
    
    def get_employee(self, employee_id: str) -> Optional[Employee]:
        """Get employee by ID."""
        session = self.get_session()
        try:
            return session.query(Employee).filter(Employee.id == employee_id).first()
        finally:
            session.close()
    
    def get_employee_by_email(self, email: str) -> Optional[Employee]:
        """Get employee by email address."""
        session = self.get_session()
        try:
            return session.query(Employee).filter(Employee.email == email).first()
        finally:
            session.close()

    def get_employee_by_personal_email(self, personal_email: str) -> Optional[Employee]:
        """Get employee by personal email address."""
        session = self.get_session()
        try:
            return session.query(Employee).filter(Employee.personal_email == personal_email).first()
        finally:
            session.close()
    
    def get_all_employees(self) -> List[Employee]:
        """Get all employees."""
        session = self.get_session()
        try:
            return session.query(Employee).all()
        finally:
            session.close()
    
    def update_employee(self, employee_id: str, **kwargs) -> Optional[Employee]:
        """Update employee information."""
        session = self.get_session()
        try:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            if employee:
                for key, value in kwargs.items():
                    if hasattr(employee, key):
                        setattr(employee, key, value)
                employee.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(employee)
            return employee
        finally:
            session.close()
    
    def delete_employee(self, employee_id: str) -> bool:
        """Delete an employee record."""
        session = self.get_session()
        try:
            employee = session.query(Employee).filter(Employee.id == employee_id).first()
            if employee:
                session.delete(employee)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    # ============================================================================
    # NOTIFICATION OPERATIONS
    # ============================================================================
    
    def create_notification(self, notification: Notification) -> Notification:
        """Create a new notification record."""
        session = self.get_session()
        try:
            session.add(notification)
            session.commit()
            session.refresh(notification)
            return notification
        finally:
            session.close()
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID."""
        session = self.get_session()
        try:
            return session.query(Notification).filter(Notification.id == notification_id).first()
        finally:
            session.close()
    
    def get_notifications_by_employee(self, employee_id: str) -> List[Notification]:
        """Get all notifications for an employee."""
        session = self.get_session()
        try:
            return session.query(Notification).filter(Notification.employee_id == employee_id).all()
        finally:
            session.close()
    
    def get_pending_notifications(self) -> List[Notification]:
        """Get all pending notifications."""
        session = self.get_session()
        try:
            return session.query(Notification).filter(Notification.status == "pending").all()
        finally:
            session.close()
    
    def update_notification(self, notification_id: str, **kwargs) -> Optional[Notification]:
        """Update a notification record."""
        session = self.get_session()
        try:
            notification = session.query(Notification).filter(Notification.id == notification_id).first()
            if notification:
                for key, value in kwargs.items():
                    if hasattr(notification, key):
                        setattr(notification, key, value)
                session.commit()
                session.refresh(notification)
            return notification
        finally:
            session.close()
    
    def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification record."""
        session = self.get_session()
        try:
            notification = session.query(Notification).filter(Notification.id == notification_id).first()
            if notification:
                session.delete(notification)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    # ============================================================================
    # UTILITY OPERATIONS
    # ============================================================================
    
    def clear_all_data(self):
        """Clear all data from database (for testing purposes)."""
        session = self.get_session()
        try:
            session.query(Notification).delete()
            session.query(Employee).delete()
            session.commit()
        finally:
            session.close()
    
    def get_database_stats(self) -> dict:
        """Get statistics about the database."""
        session = self.get_session()
        try:
            total_employees = session.query(Employee).count()
            total_notifications = session.query(Notification).count()
            pending_notifications = session.query(Notification).filter(
                Notification.status == "pending"
            ).count()
            
            return {
                "total_employees": total_employees,
                "total_notifications": total_notifications,
                "pending_notifications": pending_notifications
            }
        finally:
            session.close()