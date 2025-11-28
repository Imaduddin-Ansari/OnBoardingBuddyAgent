"""
Complete Test Suite for Onboarding Agent
Tests all endpoints and intents with proper assertions

Usage:
    python test_all_endpoints.py

Requirements:
    pip install requests colorama
"""
import requests
import json
import time
from typing import Dict, Any, Optional
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

BASE_URL = "http://localhost:8001"
EMPLOYEE_IDS = []  # Store created employee IDs for testing

class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name: str):
        self.passed += 1
        print(f"{Fore.GREEN}✓ PASS{Style.RESET_ALL}: {test_name}")
    
    def add_fail(self, test_name: str, reason: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {reason}")
        print(f"{Fore.RED}✗ FAIL{Style.RESET_ALL}: {test_name}")
        print(f"  {Fore.YELLOW}Reason: {reason}{Style.RESET_ALL}")
    
    def print_summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*80}")
        print(f"  TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {total}")
        print(f"{Fore.GREEN}Passed: {self.passed}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {self.failed}{Style.RESET_ALL}")
        
        if self.failed > 0:
            print(f"\n{Fore.RED}Failed Tests:{Style.RESET_ALL}")
            for error in self.errors:
                print(f"  • {error}")
        
        success_rate = (self.passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        print(f"{'='*80}\n")

results = TestResults()

def print_section(title: str):
    """Print a section header."""
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}{Style.RESET_ALL}")

def print_response(data: Dict[Any, Any], verbose: bool = False):
    """Print API response (only in verbose mode)."""
    if verbose:
        print(f"{Fore.MAGENTA}{json.dumps(data, indent=2)}{Style.RESET_ALL}")

def create_worker_request(intent: str, extra_data: Dict[Any, Any]) -> Dict[Any, Any]:
    """Create a worker request following the supervisor handshake protocol."""
    return {
        "request_id": f"test-{intent}-{int(time.time()*1000)}",
        "agent_name": "onboarding_agent",
        "intent": intent,
        "input": {
            "text": f"Test {intent}",
            "metadata": {
                "language": "en",
                "extra": extra_data
            }
        },
        "context": {
            "user_id": "test_user",
            "conversation_id": "test_conversation",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    }

def assert_response_structure(response: Dict[Any, Any], test_name: str):
    """Assert that response follows worker handshake protocol."""
    required_fields = ["request_id", "agent_name", "status"]
    
    for field in required_fields:
        if field not in response:
            results.add_fail(test_name, f"Missing required field: {field}")
            return False
    
    if response["status"] not in ["success", "error"]:
        results.add_fail(test_name, f"Invalid status: {response['status']}")
        return False
    
    if response["status"] == "success":
        if "output" not in response or response["output"] is None:
            results.add_fail(test_name, "Success response missing output")
            return False
        if "result" not in response["output"]:
            results.add_fail(test_name, "Output missing result field")
            return False
    
    if response["status"] == "error":
        if "error" not in response or response["error"] is None:
            results.add_fail(test_name, "Error response missing error field")
            return False
    
    return True

# ============================================================================
# TEST 1: HEALTH CHECK
# ============================================================================

def test_health_check():
    """Test /health endpoint."""
    print_section("TEST 1: Health Check Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        if response.status_code != 200:
            results.add_fail("Health Check", f"HTTP {response.status_code}")
            return
        
        data = response.json()
        print_response(data, verbose=True)
        
        # Assert structure
        if "status" not in data or data["status"] != "healthy":
            results.add_fail("Health Check", "Status not healthy")
            return
        
        if "agent" not in data or data["agent"] != "onboarding_agent":
            results.add_fail("Health Check", "Agent name incorrect")
            return
        
        results.add_pass("Health Check")
        
    except Exception as e:
        results.add_fail("Health Check", str(e))

# ============================================================================
# TEST 2: DATA COLLECTION (Function 1)
# ============================================================================

def test_data_collection():
    """Test onboarding.collect_data intent."""
    print_section("TEST 2: Function 1 - Data Collection")
    
    test_cases = [
        {
            "name": "Valid Employee - Engineering",
            "data": {
                "name": "Alice Johnson",
                "email": "alice.johnson@company.com",
                "department": "Engineering",
                "joining_date": "2025-02-01",
                "position": "Senior Software Engineer",
                "phone": "+1-555-0101"
            }
        },
        {
            "name": "Valid Employee - HR",
            "data": {
                "name": "Bob Smith",
                "email": "bob.smith@company.com",
                "department": "HR",
                "joining_date": "2025-02-15",
                "position": "HR Manager"
            }
        },
        {
            "name": "Valid Employee - Sales",
            "data": {
                "name": "Carol White",
                "email": "carol.white@company.com",
                "department": "Sales",
                "joining_date": "2025-03-01",
                "position": "Sales Representative",
                "phone": "+1-555-0102"
            }
        }
    ]
    
    for test_case in test_cases:
        try:
            request_data = create_worker_request("onboarding.collect_data", test_case["data"])
            response = requests.post(f"{BASE_URL}/execute", json=request_data, timeout=10)
            
            if response.status_code != 200:
                results.add_fail(f"Data Collection - {test_case['name']}", f"HTTP {response.status_code}")
                continue
            
            data = response.json()
            print_response(data)
            
            if not assert_response_structure(data, f"Data Collection - {test_case['name']}"):
                continue
            
            if data["status"] == "success":
                # Extract employee_id from details
                details = data["output"]["details"]
                if "Employee ID:" in details:
                    employee_id = details.split("Employee ID: ")[1].split(",")[0].strip()
                    EMPLOYEE_IDS.append(employee_id)
                    print(f"  {Fore.BLUE}Created employee ID: {employee_id}{Style.RESET_ALL}")
                
                results.add_pass(f"Data Collection - {test_case['name']}")
            else:
                results.add_fail(f"Data Collection - {test_case['name']}", data["error"]["message"])
        
        except Exception as e:
            results.add_fail(f"Data Collection - {test_case['name']}", str(e))

# ============================================================================
# TEST 3: ACCESS SETUP (Function 2)
# ============================================================================

def test_access_setup():
    """Test onboarding.setup_access intent."""
    print_section("TEST 3: Function 2 - Access Setup")
    
    if not EMPLOYEE_IDS:
        results.add_fail("Access Setup", "No employee IDs available")
        return
    
    employee_id = EMPLOYEE_IDS[0]
    
    try:
        request_data = create_worker_request(
            "onboarding.setup_access",
            {"employee_id": employee_id}
        )
        
        response = requests.post(f"{BASE_URL}/execute", json=request_data, timeout=10)
        
        if response.status_code != 200:
            results.add_fail("Access Setup", f"HTTP {response.status_code}")
            return
        
        data = response.json()
        print_response(data)
        
        if not assert_response_structure(data, "Access Setup"):
            return
        
        if data["status"] == "success":
            results.add_pass("Access Setup")
            
            # Wait for access requests to complete
            print(f"  {Fore.YELLOW}Waiting 3 seconds for access requests to process...{Style.RESET_ALL}")
            time.sleep(3)
        else:
            results.add_fail("Access Setup", data["error"]["message"])
    
    except Exception as e:
        results.add_fail("Access Setup", str(e))

# ============================================================================
# TEST 4: TASK ASSIGNMENT (Function 3)
# ============================================================================

def test_task_assignment():
    """Test onboarding.assign_tasks intent."""
    print_section("TEST 4: Function 3 - Task Assignment")
    
    if not EMPLOYEE_IDS:
        results.add_fail("Task Assignment", "No employee IDs available")
        return
    
    test_cases = [
        {"employee_id": EMPLOYEE_IDS[0], "department": "Engineering"},
        {"employee_id": EMPLOYEE_IDS[1] if len(EMPLOYEE_IDS) > 1 else EMPLOYEE_IDS[0], "department": "HR"},
    ]
    
    for i, test_data in enumerate(test_cases):
        try:
            request_data = create_worker_request("onboarding.assign_tasks", test_data)
            response = requests.post(f"{BASE_URL}/execute", json=request_data, timeout=10)
            
            if response.status_code != 200:
                results.add_fail(f"Task Assignment - Case {i+1}", f"HTTP {response.status_code}")
                continue
            
            data = response.json()
            print_response(data)
            
            if not assert_response_structure(data, f"Task Assignment - Case {i+1}"):
                continue
            
            if data["status"] == "success":
                result_text = data["output"]["result"]
                if "tasks" in result_text.lower():
                    results.add_pass(f"Task Assignment - Case {i+1}")
                else:
                    results.add_fail(f"Task Assignment - Case {i+1}", "No tasks mentioned in result")
            else:
                results.add_fail(f"Task Assignment - Case {i+1}", data["error"]["message"])
        
        except Exception as e:
            results.add_fail(f"Task Assignment - Case {i+1}", str(e))

# ============================================================================
# TEST 5: PROGRESS MONITORING (Function 4)
# ============================================================================

def test_progress_monitoring():
    """Test onboarding.check_progress intent."""
    print_section("TEST 5: Function 4 - Progress Monitoring")
    
    # Test 5a: Check specific employee progress
    if EMPLOYEE_IDS:
        try:
            request_data = create_worker_request(
                "onboarding.check_progress",
                {"employee_id": EMPLOYEE_IDS[0]}
            )
            
            response = requests.post(f"{BASE_URL}/execute", json=request_data, timeout=10)
            
            if response.status_code != 200:
                results.add_fail("Progress Monitoring - Single Employee", f"HTTP {response.status_code}")
            else:
                data = response.json()
                print_response(data)
                
                if assert_response_structure(data, "Progress Monitoring - Single Employee"):
                    if data["status"] == "success":
                        results.add_pass("Progress Monitoring - Single Employee")
                    else:
                        results.add_fail("Progress Monitoring - Single Employee", data["error"]["message"])
        
        except Exception as e:
            results.add_fail("Progress Monitoring - Single Employee", str(e))
    
    # Test 5b: Check all employees progress
    try:
        request_data = create_worker_request("onboarding.check_progress", {})
        response = requests.post(f"{BASE_URL}/execute", json=request_data, timeout=10)
        
        if response.status_code != 200:
            results.add_fail("Progress Monitoring - All Employees", f"HTTP {response.status_code}")
        else:
            data = response.json()
            print_response(data)
            
            if assert_response_structure(data, "Progress Monitoring - All Employees"):
                if data["status"] == "success":
                    results.add_pass("Progress Monitoring - All Employees")
                else:
                    results.add_fail("Progress Monitoring - All Employees", data["error"]["message"])
    
    except Exception as e:
        results.add_fail("Progress Monitoring - All Employees", str(e))

# ============================================================================
# TEST 6: NOTIFICATIONS (Function 5)
# ============================================================================

def test_notifications():
    """Test onboarding.send_notifications intent."""
    print_section("TEST 6: Function 5 - Notifications")
    
    if not EMPLOYEE_IDS:
        results.add_fail("Notifications", "No employee IDs available")
        return
    
    test_cases = [
        {"name": "Welcome Email", "data": {"employee_id": EMPLOYEE_IDS[0], "type": "welcome"}},
        {"name": "Task Reminder", "data": {"employee_id": EMPLOYEE_IDS[0], "type": "reminder"}},
        {"name": "Bulk Reminders", "data": {}},
    ]
    
    for test_case in test_cases:
        try:
            request_data = create_worker_request("onboarding.send_notifications", test_case["data"])
            response = requests.post(f"{BASE_URL}/execute", json=request_data, timeout=10)
            
            if response.status_code != 200:
                results.add_fail(f"Notifications - {test_case['name']}", f"HTTP {response.status_code}")
                continue
            
            data = response.json()
            print_response(data)
            
            if not assert_response_structure(data, f"Notifications - {test_case['name']}"):
                continue
            
            if data["status"] == "success":
                results.add_pass(f"Notifications - {test_case['name']}")
            else:
                results.add_fail(f"Notifications - {test_case['name']}", data["error"]["message"])
        
        except Exception as e:
            results.add_fail(f"Notifications - {test_case['name']}", str(e))

# ============================================================================
# TEST 7: REPORTING (Function 6)
# ============================================================================

def test_reporting():
    """Test onboarding.generate_report intent."""
    print_section("TEST 7: Function 6 - Reporting")
    
    test_cases = [
        {"name": "Summary Report", "data": {"report_type": "summary"}},
        {"name": "Issues Report", "data": {"report_type": "issues"}},
    ]
    
    # Add employee report if we have employee IDs
    if EMPLOYEE_IDS:
        test_cases.append({
            "name": "Employee Report",
            "data": {"report_type": "employee", "employee_id": EMPLOYEE_IDS[0]}
        })
    
    for test_case in test_cases:
        try:
            request_data = create_worker_request("onboarding.generate_report", test_case["data"])
            response = requests.post(f"{BASE_URL}/execute", json=request_data, timeout=10)
            
            if response.status_code != 200:
                results.add_fail(f"Reporting - {test_case['name']}", f"HTTP {response.status_code}")
                continue
            
            data = response.json()
            print_response(data)
            
            if not assert_response_structure(data, f"Reporting - {test_case['name']}"):
                continue
            
            if data["status"] == "success":
                results.add_pass(f"Reporting - {test_case['name']}")
            else:
                results.add_fail(f"Reporting - {test_case['name']}", data["error"]["message"])
        
        except Exception as e:
            results.add_fail(f"Reporting - {test_case['name']}", str(e))

# ============================================================================
# TEST 8: COMPLETE ONBOARDING WORKFLOW
# ============================================================================

def test_complete_workflow():
    """Test onboarding.create intent (full workflow)."""
    print_section("TEST 8: Complete Onboarding Workflow")
    
    try:
        request_data = create_worker_request(
            "onboarding.create",
            {
                "name": "Diana Prince",
                "email": "diana.prince@company.com",
                "department": "Marketing",
                "joining_date": "2025-03-15",
                "position": "Marketing Director",
                "phone": "+1-555-0103"
            }
        )
        
        response = requests.post(f"{BASE_URL}/execute", json=request_data, timeout=15)
        
        if response.status_code != 200:
            results.add_fail("Complete Workflow", f"HTTP {response.status_code}")
            return
        
        data = response.json()
        print_response(data, verbose=True)
        
        if not assert_response_structure(data, "Complete Workflow"):
            return
        
        if data["status"] == "success":
            # Verify all components were executed
            details = data["output"].get("details", "")
            
            checks = {
                "Employee created": "employee_id" in details,
                "Tasks assigned": "tasks_assigned" in details,
                "Access initiated": "access_requests_initiated" in details,
                "Report generated": "report" in details
            }
            
            all_passed = all(checks.values())
            
            if all_passed:
                results.add_pass("Complete Workflow")
            else:
                failed_checks = [k for k, v in checks.items() if not v]
                results.add_fail("Complete Workflow", f"Missing: {', '.join(failed_checks)}")
        else:
            results.add_fail("Complete Workflow", data["error"]["message"])
    
    except Exception as e:
        results.add_fail("Complete Workflow", str(e))

# ============================================================================
# TEST 9: STATUS CHECK
# ============================================================================

def test_status_check():
    """Test onboarding.get_status intent."""
    print_section("TEST 9: Status Check")
    
    if not EMPLOYEE_IDS:
        results.add_fail("Status Check", "No employee IDs available")
        return
    
    try:
        request_data = create_worker_request(
            "onboarding.get_status",
            {"employee_id": EMPLOYEE_IDS[0]}
        )
        
        response = requests.post(f"{BASE_URL}/execute", json=request_data, timeout=10)
        
        if response.status_code != 200:
            results.add_fail("Status Check", f"HTTP {response.status_code}")
            return
        
        data = response.json()
        print_response(data)
        
        if not assert_response_structure(data, "Status Check"):
            return
        
        if data["status"] == "success":
            results.add_pass("Status Check")
        else:
            results.add_fail("Status Check", data["error"]["message"])
    
    except Exception as e:
        results.add_fail("Status Check", str(e))

# ============================================================================
# TEST 10: ADDITIONAL ENDPOINTS
# ============================================================================

def test_additional_endpoints():
    """Test additional REST endpoints."""
    print_section("TEST 10: Additional REST Endpoints")
    
    endpoints = [
        {"name": "List Employees", "url": "/employees", "method": "GET"},
        {"name": "Dashboard", "url": "/dashboard", "method": "GET"},
    ]
    
    # Add employee-specific endpoints if we have IDs
    if EMPLOYEE_IDS:
        endpoints.extend([
            {"name": "Get Employee", "url": f"/employees/{EMPLOYEE_IDS[0]}", "method": "GET"},
            {"name": "Get Employee Tasks", "url": f"/tasks/{EMPLOYEE_IDS[0]}", "method": "GET"},
        ])
    
    for endpoint in endpoints:
        try:
            if endpoint["method"] == "GET":
                response = requests.get(f"{BASE_URL}{endpoint['url']}", timeout=10)
            
            if response.status_code != 200:
                results.add_fail(f"Endpoint - {endpoint['name']}", f"HTTP {response.status_code}")
                continue
            
            data = response.json()
            print_response(data)
            
            results.add_pass(f"Endpoint - {endpoint['name']}")
        
        except Exception as e:
            results.add_fail(f"Endpoint - {endpoint['name']}", str(e))

# ============================================================================
# TEST 11: ERROR HANDLING
# ============================================================================

def test_error_handling():
    """Test error handling for invalid requests."""
    print_section("TEST 11: Error Handling")
    
    test_cases = [
        {
            "name": "Invalid Intent",
            "intent": "onboarding.invalid_intent",
            "data": {},
            "expect_error": True
        },
        {
            "name": "Missing Employee ID",
            "intent": "onboarding.setup_access",
            "data": {},
            "expect_error": True
        },
        {
            "name": "Invalid Employee ID",
            "intent": "onboarding.check_progress",
            "data": {"employee_id": "invalid_id_12345"},
            "expect_error": True
        }
    ]
    
    for test_case in test_cases:
        try:
            request_data = create_worker_request(test_case["intent"], test_case["data"])
            response = requests.post(f"{BASE_URL}/execute", json=request_data, timeout=10)
            
            if response.status_code != 200:
                results.add_fail(f"Error Handling - {test_case['name']}", f"HTTP {response.status_code}")
                continue
            
            data = response.json()
            print_response(data)
            
            if not assert_response_structure(data, f"Error Handling - {test_case['name']}"):
                continue
            
            # Should return error status
            if test_case["expect_error"] and data["status"] == "error":
                results.add_pass(f"Error Handling - {test_case['name']}")
            elif test_case["expect_error"] and data["status"] != "error":
                results.add_fail(f"Error Handling - {test_case['name']}", "Expected error but got success")
            else:
                results.add_pass(f"Error Handling - {test_case['name']}")
        
        except Exception as e:
            results.add_fail(f"Error Handling - {test_case['name']}", str(e))

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all tests."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}")
    print("="*80)
    print("  ONBOARDING AGENT - COMPREHENSIVE TEST SUITE")
    print("  Testing all endpoints and intents")
    print("="*80)
    print(Style.RESET_ALL)
    
    try:
        # Run all tests
        test_health_check()
        test_data_collection()
        test_access_setup()
        test_task_assignment()
        test_progress_monitoring()
        test_notifications()
        test_reporting()
        test_complete_workflow()
        test_status_check()
        test_additional_endpoints()
        test_error_handling()
        
        # Print summary
        results.print_summary()
        
        # Exit with appropriate code
        exit(0 if results.failed == 0 else 1)
        
    except requests.exceptions.ConnectionError:
        print(f"\n{Fore.RED}❌ ERROR: Could not connect to onboarding agent.{Style.RESET_ALL}")
        print("Make sure the agent is running on http://localhost:8002")
        print("Run: python main.py")
        exit(1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Test suite interrupted by user.{Style.RESET_ALL}")
        results.print_summary()
        exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}❌ FATAL ERROR: {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()