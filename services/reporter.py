"""
Service Module 6: Reporting
Shares progress summaries and issue alerts with the Supervisor Agent 
for review and coordination.
File: services/reporter.py
"""
from datetime import datetime, timedelta
from typing import Dict, List
from application.database import Database, TaskStatus, AccessStatus

class Reporter:
    """Generates reports and alerts for supervisor agent."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def generate_employee_report(self, employee_id: str) -> Dict:
        """
        Generate comprehensive report for a single employee.
        
        Returns detailed progress, tasks, access status, and recommendations.
        """
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
        
        # Task statistics
        tasks = self.db.get_tasks_by_employee(employee_id)
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        pending_tasks = len([t for t in tasks if t.status == TaskStatus.PENDING])
        
        overdue_tasks = [
            t for t in tasks 
            if t.status == TaskStatus.PENDING and t.due_date and t.due_date < datetime.utcnow()
        ]
        
        # Access statistics
        access_requests = self.db.get_access_requests(employee_id)
        total_access = len(access_requests)
        completed_access = len([a for a in access_requests if a.status == AccessStatus.COMPLETED])
        pending_access = len([a for a in access_requests if a.status == AccessStatus.PENDING])
        failed_access = len([a for a in access_requests if a.status == AccessStatus.FAILED])
        
        # Calculate metrics
        completion_percentage = ((completed_tasks + completed_access) / 
                                (total_tasks + total_access) * 100) if (total_tasks + total_access) > 0 else 0
        
        days_since_joining = (datetime.utcnow() - employee.joining_date).days if employee.joining_date else 0
        
        # Determine status
        status = self._determine_employee_status(completion_percentage, len(overdue_tasks), days_since_joining)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            employee_id, 
            len(overdue_tasks), 
            pending_access, 
            failed_access,
            completion_percentage,
            days_since_joining
        )
        
        return {
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "email": employee.email,
                "department": employee.department,
                "position": employee.position,
                "joining_date": employee.joining_date.isoformat() if employee.joining_date else None,
                "days_since_joining": days_since_joining
            },
            "progress": {
                "completion_percentage": round(completion_percentage, 2),
                "status": status,
                "tasks": {
                    "total": total_tasks,
                    "completed": completed_tasks,
                    "pending": pending_tasks,
                    "overdue": len(overdue_tasks)
                },
                "access_requests": {
                    "total": total_access,
                    "completed": completed_access,
                    "pending": pending_access,
                    "failed": failed_access
                }
            },
            "issues": {
                "has_overdue_tasks": len(overdue_tasks) > 0,
                "has_failed_access": failed_access > 0,
                "overdue_task_list": [t.title for t in overdue_tasks],
                "stuck_access_requests": pending_access > 0 and days_since_joining > 5
            },
            "recommendations": recommendations,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def generate_summary_report(self) -> Dict:
        """
        Generate summary report for all employees.
        
        Provides high-level overview of onboarding status across organization.
        """
        employees = self.db.get_all_employees()
        total_employees = len(employees)
        
        # Count by status
        completed_count = 0
        on_track_count = 0
        at_risk_count = 0
        
        total_overdue_tasks = 0
        total_pending_access = 0
        
        for employee in employees:
            tasks = self.db.get_tasks_by_employee(employee.id)
            access_requests = self.db.get_access_requests(employee.id)
            
            total_items = len(tasks) + len(access_requests)
            completed_items = (
                len([t for t in tasks if t.status == TaskStatus.COMPLETED]) +
                len([a for a in access_requests if a.status == AccessStatus.COMPLETED])
            )
            
            completion_pct = (completed_items / total_items * 100) if total_items > 0 else 0
            
            overdue = len([
                t for t in tasks 
                if t.status == TaskStatus.PENDING and t.due_date and t.due_date < datetime.utcnow()
            ])
            
            total_overdue_tasks += overdue
            total_pending_access += len([a for a in access_requests if a.status == AccessStatus.PENDING])
            
            if completion_pct >= 100:
                completed_count += 1
            elif overdue > 3:
                at_risk_count += 1
            else:
                on_track_count += 1
        
        return {
            "summary": {
                "total_employees": total_employees,
                "completed": completed_count,
                "on_track": on_track_count,
                "at_risk": at_risk_count,
                "total_overdue_tasks": total_overdue_tasks,
                "total_pending_access_requests": total_pending_access
            },
            "breakdown": {
                "completion_rate": round((completed_count / total_employees * 100) if total_employees > 0 else 0, 2),
                "at_risk_rate": round((at_risk_count / total_employees * 100) if total_employees > 0 else 0, 2)
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def get_issue_alerts(self) -> List[Dict]:
        """
        Get all current issues requiring attention.
        
        Returns list of alerts for supervisor to review.
        """
        alerts = []
        employees = self.db.get_all_employees()
        
        for employee in employees:
            # Check for overdue tasks
            tasks = self.db.get_tasks_by_employee(employee.id)
            overdue_tasks = [
                t for t in tasks 
                if t.status == TaskStatus.PENDING and t.due_date and t.due_date < datetime.utcnow()
            ]
            
            if len(overdue_tasks) > 3:
                alerts.append({
                    "type": "critical",
                    "category": "overdue_tasks",
                    "employee_id": employee.id,
                    "employee_name": employee.name,
                    "message": f"{employee.name} has {len(overdue_tasks)} overdue tasks",
                    "count": len(overdue_tasks),
                    "action_required": "Manager follow-up needed"
                })
            elif len(overdue_tasks) > 0:
                alerts.append({
                    "type": "warning",
                    "category": "overdue_tasks",
                    "employee_id": employee.id,
                    "employee_name": employee.name,
                    "message": f"{employee.name} has {len(overdue_tasks)} overdue task(s)",
                    "count": len(overdue_tasks),
                    "action_required": "Send reminder"
                })
            
            # Check for stuck access requests
            access_requests = self.db.get_access_requests(employee.id)
            stuck_access = [
                a for a in access_requests 
                if a.status == AccessStatus.PENDING and 
                (datetime.utcnow() - a.requested_at).days > 3
            ]
            
            if stuck_access:
                alerts.append({
                    "type": "warning",
                    "category": "stuck_access",
                    "employee_id": employee.id,
                    "employee_name": employee.name,
                    "message": f"{len(stuck_access)} access request(s) pending for over 3 days",
                    "count": len(stuck_access),
                    "action_required": "Contact IT department"
                })
            
            # Check for failed access requests
            failed_access = [a for a in access_requests if a.status == AccessStatus.FAILED]
            if failed_access:
                alerts.append({
                    "type": "critical",
                    "category": "failed_access",
                    "employee_id": employee.id,
                    "employee_name": employee.name,
                    "message": f"{len(failed_access)} access request(s) have failed",
                    "count": len(failed_access),
                    "action_required": "Immediate IT intervention required"
                })
        
        # Sort by severity (critical first)
        alerts.sort(key=lambda x: 0 if x["type"] == "critical" else 1)
        
        return alerts
    
    def get_daily_digest(self) -> Dict:
        """Generate daily digest for supervisor."""
        summary = self.generate_summary_report()
        issues = self.get_issue_alerts()
        
        # Recent activity (employees joined in last 7 days)
        recent_employees = [
            emp for emp in self.db.get_all_employees()
            if emp.joining_date and (datetime.utcnow() - emp.joining_date).days <= 7
        ]
        
        return {
            "date": datetime.utcnow().date().isoformat(),
            "summary": summary,
            "critical_issues": len([i for i in issues if i["type"] == "critical"]),
            "warnings": len([i for i in issues if i["type"] == "warning"]),
            "recent_hires": len(recent_employees),
            "recent_hire_list": [{"name": e.name, "department": e.department} for e in recent_employees],
            "alerts": issues[:10]  # Top 10 alerts
        }
    
    def _determine_employee_status(self, completion_pct: float, overdue_count: int, days: int) -> str:
        """Determine employee onboarding status."""
        if completion_pct >= 100:
            return "completed"
        elif overdue_count > 3:
            return "at_risk"
        elif completion_pct >= 75:
            return "on_track"
        elif completion_pct >= 50:
            return "in_progress"
        else:
            return "just_started"
    
    def _generate_recommendations(
        self, 
        employee_id: str, 
        overdue_count: int, 
        pending_access: int,
        failed_access: int,
        completion_pct: float,
        days_since_joining: int
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if overdue_count > 3:
            recommendations.append("URGENT: Schedule meeting with employee to address overdue tasks")
        elif overdue_count > 0:
            recommendations.append("Send reminder notification for overdue tasks")
        
        if failed_access > 0:
            recommendations.append("URGENT: Contact IT to resolve failed access requests")
        
        if pending_access > 0 and days_since_joining > 5:
            recommendations.append("Follow up with IT on pending access requests")
        
        if completion_pct < 30 and days_since_joining > 7:
            recommendations.append("Check in with employee - onboarding progress is slower than expected")
        
        if completion_pct >= 90:
            recommendations.append("Employee near completion - prepare completion certificate and welcome package")
        
        if not recommendations:
            recommendations.append("Onboarding progressing normally - no action required")
        
        return recommendations