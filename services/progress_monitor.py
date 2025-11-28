"""
Service Module 4: Progress Monitoring
Tracks task completion and identifies pending items for each employee.
File: services/progress_monitor.py
"""
from datetime import datetime
from typing import Dict, List
from application.database import Database, TaskStatus

class ProgressMonitor:
    """Monitors onboarding progress and tracks completion status."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def initialize_monitoring(self, employee_id: str) -> Dict:
        """Initialize progress tracking for a new employee."""
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"❌ Cannot initialize monitoring: Employee {employee_id} not found.")
        
        return {
            "message": f"✅ Progress monitoring initialized for {employee.name}",
            "employee_id": employee_id,
            "success": True
        }
    
    def get_employee_progress(self, employee_id: str) -> Dict:
        """
        Get detailed progress for a specific employee.
        
        Returns:
            Dict with completion stats, percentage, and task breakdown with message
        """
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"❌ Employee with ID '{employee_id}' not found.")
        
        tasks = self.db.get_tasks_by_employee(employee_id)
        
        if not tasks:
            return {
                "employee_id": employee_id,
                "employee_name": employee.name,
                "total_tasks": 0,
                "completed_tasks": 0,
                "pending_tasks": 0,
                "overdue_tasks": 0,
                "completion_percentage": 0.0,
                "status": "no_tasks_assigned",
                "message": f"📋 No tasks assigned yet to {employee.name}. Tasks will appear once onboarding begins."
            }
        
        completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        pending = len([t for t in tasks if t.status == TaskStatus.PENDING])
        overdue = len([t for t in tasks if t.status == TaskStatus.OVERDUE])
        
        completion_percentage = (completed / len(tasks)) * 100 if tasks else 0
        
        # Determine status emoji and message
        if completion_percentage == 100:
            status = "completed"
            emoji = "🎉"
            status_text = "All tasks completed!"
        elif overdue > 0:
            status = "needs_attention"
            emoji = "⚠️"
            status_text = f"{overdue} overdue task(s) - action required"
        elif completion_percentage >= 75:
            status = "on_track"
            emoji = "✅"
            status_text = "On track - great progress!"
        elif completion_percentage >= 50:
            status = "in_progress"
            emoji = "📊"
            status_text = "Making good progress"
        elif completion_percentage > 0:
            status = "started"
            emoji = "🚀"
            status_text = "Just getting started"
        else:
            status = "not_started"
            emoji = "📝"
            status_text = "Tasks assigned, ready to begin"
        
        message = (
            f"{emoji} **Progress Report: {employee.name}**\n\n"
            f"📊 **Completion:** {completion_percentage:.1f}% ({completed}/{len(tasks)} tasks)\n"
            f"⏳ Pending: {pending}\n"
        )
        
        if overdue > 0:
            message += f"⚠️ Overdue: {overdue}\n"
        
        message += f"\n💬 Status: {status_text}"
        
        return {
            "employee_id": employee_id,
            "employee_name": employee.name,
            "total_tasks": len(tasks),
            "completed_tasks": completed,
            "pending_tasks": pending,
            "overdue_tasks": overdue,
            "completion_percentage": round(completion_percentage, 1),
            "status": status,
            "message": message
        }
    
    def get_all_progress(self) -> Dict:
        """
        Get progress summary for ALL employees.
        Returns dict with progress details for each employee and overall summary.
        """
        employees = self.db.get_all_employees()
        
        if not employees:
            return {
                "message": "ℹ️ No employees found in the system.",
                "employees": [],
                "summary": {
                    "total_employees": 0,
                    "completed": 0,
                    "on_track": 0,
                    "needs_attention": 0
                }
            }
        
        progress_list = []
        completed_count = 0
        on_track_count = 0
        needs_attention_count = 0
        
        for employee in employees:
            progress = self.get_employee_progress(employee.id)
            progress_list.append(progress)
            
            if progress["status"] == "completed":
                completed_count += 1
            elif progress["status"] in ["needs_attention"]:
                needs_attention_count += 1
            elif progress["status"] in ["on_track", "in_progress", "started"]:
                on_track_count += 1
        
        message = (
            f"📊 **Overall Onboarding Progress Report**\n\n"
            f"👥 Total Employees: {len(employees)}\n"
            f"🎉 Completed: {completed_count}\n"
            f"✅ On Track: {on_track_count}\n"
            f"⚠️ Needs Attention: {needs_attention_count}\n\n"
        )
        
        if needs_attention_count > 0:
            message += f"⚠️ {needs_attention_count} employee(s) need immediate attention (overdue tasks)"
        else:
            message += "✅ All employees are progressing well!"
        
        return {
            "message": message,
            "employees": progress_list,
            "summary": {
                "total_employees": len(employees),
                "completed": completed_count,
                "on_track": on_track_count,
                "needs_attention": needs_attention_count
            }
        }
    
    def get_pending_items(self, employee_id: str) -> Dict:
        """Get all pending items (tasks and access requests) for an employee."""
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"❌ Employee with ID '{employee_id}' not found.")
        
        pending_tasks = self.db.get_pending_tasks(employee_id)
        access_requests = self.db.get_access_requests(employee_id)
        
        pending_access = [
            ar for ar in access_requests 
            if ar.status.value in ["pending", "in_progress"]
        ]
        
        total_pending = len(pending_tasks) + len(pending_access)
        
        if total_pending == 0:
            message = f"✅ Great! {employee.name} has no pending items. Everything is up to date."
        else:
            message = (
                f"📋 **Pending Items for {employee.name}**\n\n"
                f"⏳ Pending Tasks: {len(pending_tasks)}\n"
                f"🔐 Pending Access Requests: {len(pending_access)}\n"
                f"Total: {total_pending} item(s) need attention"
            )
        
        return {
            "employee_id": employee_id,
            "employee_name": employee.name,
            "message": message,
            "pending_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "category": t.category,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "priority": t.priority
                }
                for t in pending_tasks
            ],
            "pending_access_requests": [
                {
                    "id": ar.id,
                    "type": ar.access_type.value,
                    "status": ar.status.value,
                    "requested_at": ar.requested_at.isoformat() if ar.requested_at else None
                }
                for ar in pending_access
            ],
            "total_pending": total_pending
        }
    
    def check_overdue_tasks(self, employee_id: str = None) -> Dict:
        """Check for overdue tasks and return list with summary."""
        if employee_id:
            employee = self.db.get_employee(employee_id)
            if not employee:
                raise ValueError(f"❌ Employee with ID '{employee_id}' not found.")
            tasks = self.db.get_tasks_by_employee(employee_id)
            context = f"for {employee.name}"
        else:
            tasks = self.db.get_pending_tasks()
            context = "across all employees"
        
        overdue = []
        now = datetime.utcnow()
        
        for task in tasks:
            if task.status == TaskStatus.PENDING and task.due_date and task.due_date < now:
                # Update status to overdue
                self.db.update_task(task.id, status=TaskStatus.OVERDUE)
                
                employee = self.db.get_employee(task.employee_id)
                overdue.append({
                    "task_id": task.id,
                    "task_title": task.title,
                    "employee_id": task.employee_id,
                    "employee_name": employee.name if employee else "Unknown",
                    "due_date": task.due_date.isoformat(),
                    "days_overdue": (now - task.due_date).days
                })
        
        if not overdue:
            message = f"✅ No overdue tasks {context}. All tasks are on schedule!"
        else:
            message = (
                f"⚠️ **Alert: {len(overdue)} Overdue Task(s) {context}**\n\n"
                f"The following tasks require immediate attention:\n"
            )
            for item in overdue[:5]:
                message += f"• {item['task_title']} ({item['employee_name']}) - {item['days_overdue']} day(s) overdue\n"
            
            if len(overdue) > 5:
                message += f"• ... and {len(overdue) - 5} more\n"
        
        return {
            "message": message,
            "overdue_tasks": overdue,
            "count": len(overdue)
        }
    
    def get_completion_summary(self) -> Dict:
        """Get overall completion summary across all employees."""
        employees = self.db.get_all_employees()
        
        if not employees:
            return {
                "message": "ℹ️ No employees in the system yet.",
                "summary": {
                    "total_employees": 0,
                    "completed_onboarding": 0,
                    "in_progress": 0,
                    "not_started": 0,
                    "completion_rate": 0
                }
            }
        
        total_employees = len(employees)
        completed_onboarding = 0
        in_progress = 0
        not_started = 0
        
        for employee in employees:
            progress = self.get_employee_progress(employee.id)
            
            if progress["completion_percentage"] == 100:
                completed_onboarding += 1
            elif progress["completion_percentage"] > 0:
                in_progress += 1
            else:
                not_started += 1
        
        completion_rate = (completed_onboarding / total_employees * 100) if total_employees > 0 else 0
        
        message = (
            f"📈 **Onboarding Completion Summary**\n\n"
            f"👥 Total Employees: {total_employees}\n"
            f"🎉 Completed: {completed_onboarding} ({completion_rate:.1f}%)\n"
            f"🔄 In Progress: {in_progress}\n"
            f"📝 Not Started: {not_started}\n\n"
        )
        
        if completion_rate >= 80:
            message += "🌟 Excellent! Most employees have completed onboarding."
        elif completion_rate >= 60:
            message += "✅ Good progress overall. Keep up the momentum!"
        elif completion_rate >= 40:
            message += "📊 Moderate progress. Some employees need encouragement."
        else:
            message += "⚠️ Many employees are still in early stages. Consider sending reminders."
        
        return {
            "message": message,
            "summary": {
                "total_employees": total_employees,
                "completed_onboarding": completed_onboarding,
                "in_progress": in_progress,
                "not_started": not_started,
                "completion_rate": round(completion_rate, 1)
            }
        }