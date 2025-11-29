"""
Service Module 4: Progress Monitoring
Tracks employee information completeness.
File: services/progress_monitor.py
"""
from datetime import datetime
from typing import Dict
from application.database import Database

class ProgressMonitor:
    """Monitors employee onboarding information completeness."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_employee_progress(self, employee_id: str) -> Dict:
        """
        Check if employee has all required information filled out.
        
        Returns:
            Dict with completion status and which fields are missing
        """
        employee = self.db.get_employee(employee_id)
        if not employee:
            raise ValueError(f"❌ Employee with ID '{employee_id}' not found.")
        
        # FIXED: Check personal_email (user-provided), NOT email (auto-generated)
        required_fields = {
            "name": employee.name,
            "personal_email": employee.personal_email,  # CHANGED: from email to personal_email
            "department": employee.department,
            "joining_date": employee.joining_date,
            "position": employee.position,
            "phone": employee.phone,
            "manager_id": employee.manager_id
        }
        # Note: 'email' (company email) is NOT checked - it's generated automatically
        
        # Check which fields are filled
        filled_fields = []
        missing_fields = []
        
        for field_name, field_value in required_fields.items():
            if field_value and str(field_value).strip():
                filled_fields.append(field_name)
            else:
                missing_fields.append(field_name)
        
        total_fields = len(required_fields)
        filled_count = len(filled_fields)
        completion_percentage = (filled_count / total_fields) * 100
        
        # Determine status
        if completion_percentage == 100:
            status = "complete"
            emoji = "✅"
            status_text = "All information complete"
        elif completion_percentage >= 70:
            status = "nearly_complete"
            emoji = "📊"
            status_text = "Almost complete - few fields missing"
        elif completion_percentage >= 40:
            status = "in_progress"
            emoji = "⏳"
            status_text = "Information partially filled"
        else:
            status = "incomplete"
            emoji = "⚠️"
            status_text = "Several required fields missing"
        
        # Build message
        message = (
            f"{emoji} **Information Progress: {employee.name}**\n\n"
            f"📊 **Completion:** {completion_percentage:.1f}% ({filled_count}/{total_fields} fields)\n\n"
        )
        
        if missing_fields:
            message += f"⚠️ **Missing Fields:**\n"
            for field in missing_fields:
                message += f"• {field.replace('_', ' ').title()}\n"
            message += f"\n💬 Status: {status_text}\n"
            message += f"\n📝 Please complete the missing information to proceed with onboarding."
        else:
            message += f"✅ **All Required Information Complete!**\n\n"
            message += f"🎉 {employee.name}'s profile is fully set up and ready for onboarding."
        
        return {
            "employee_id": employee_id,
            "employee_name": employee.name,
            "total_fields": total_fields,
            "filled_fields": filled_count,
            "missing_fields": missing_fields,
            "completion_percentage": round(completion_percentage, 1),
            "status": status,
            "message": message,
            "is_complete": len(missing_fields) == 0
        }
    
    def get_all_employees_progress(self) -> Dict:
        """
        Get information completeness for ALL employees.
        
        Returns:
            Dict with progress details for each employee and overall summary
        """
        employees = self.db.get_all_employees()
        
        if not employees:
            return {
                "message": "ℹ️ No employees found in the system.",
                "employees": [],
                "summary": {
                    "total_employees": 0,
                    "complete": 0,
                    "incomplete": 0
                }
            }
        
        progress_list = []
        complete_count = 0
        incomplete_count = 0
        
        for employee in employees:
            progress = self.get_employee_progress(employee.id)
            progress_list.append(progress)
            
            if progress["is_complete"]:
                complete_count += 1
            else:
                incomplete_count += 1
        
        message = (
            f"📊 **Overall Employee Information Status**\n\n"
            f"👥 Total Employees: {len(employees)}\n"
            f"✅ Complete Profiles: {complete_count}\n"
            f"⚠️ Incomplete Profiles: {incomplete_count}\n\n"
        )
        
        if incomplete_count > 0:
            message += f"⚠️ {incomplete_count} employee(s) have incomplete information"
        else:
            message += "✅ All employee profiles are complete!"
        
        return {
            "message": message,
            "employees": progress_list,
            "summary": {
                "total_employees": len(employees),
                "complete": complete_count,
                "incomplete": incomplete_count,
                "completion_rate": round((complete_count / len(employees)) * 100, 1) if employees else 0
            }
        }