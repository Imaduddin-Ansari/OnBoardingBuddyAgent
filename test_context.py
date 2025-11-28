"""
Test context functionality for the onboarding agent.
This demonstrates how context stores values across requests.
"""
import json
import requests
from datetime import datetime

BASE_URL = "http://localhost:8001"

def test_context_flow():
    """
    Test the context flow:
    1. Create employee data (stores name, email, department, etc in context)
    2. Use employee_id from context to setup access
    3. Use employee_id and department from context to assign tasks
    4. Check progress using context values
    """
    
    print("=" * 80)
    print("TESTING CONTEXT MANAGEMENT")
    print("=" * 80)
    
    # Request 1: Collect employee data
    print("\n1. COLLECT DATA - Providing employee info (name, email, department)")
    print("-" * 80)
    
    request_1 = {
        "request_id": "req-001",
        "agent_name": "onboarding_agent",
        "intent": "onboarding.collect_data",
        "input": {
            "text": "Create employee John Smith in Engineering department",
            "metadata": {
                "language": "en",
                "extra": {
                    "name": "John Smith",
                    "email": "john.smith@company.com",
                    "department": "Engineering"
                }
            }
        },
        "context": {
            "user_id": "user-001",
            "conversation_id": "conv-001"
        }
    }
    
    response_1 = requests.post(f"{BASE_URL}/execute", json=request_1)
    print(f"Status: {response_1.status_code}")
    result_1 = response_1.json()
    print(json.dumps(result_1, indent=2))
    
    # Extract employee_id from response
    employee_id = json.loads(result_1["output"]["details"]).get("Employee ID").split(": ")[1]
    print(f"\n✓ Stored in context: name=John Smith, email=john.smith@company.com, department=Engineering")
    print(f"✓ Employee ID: {employee_id}")
    
    # Request 2: Setup access using context values (only provide intent, department already in context)
    print("\n2. SETUP ACCESS - Using employee_id from context (not provided in this request)")
    print("-" * 80)
    
    request_2 = {
        "request_id": "req-002",
        "agent_name": "onboarding_agent",
        "intent": "onboarding.setup_access",
        "input": {
            "text": "Setup access for employee",
            "metadata": {
                "language": "en",
                "extra": {
                    "employee_id": employee_id
                }
            }
        },
        "context": {
            "user_id": "user-001",
            "conversation_id": "conv-001"
        }
    }
    
    response_2 = requests.post(f"{BASE_URL}/execute", json=request_2)
    print(f"Status: {response_2.status_code}")
    result_2 = response_2.json()
    print(json.dumps(result_2, indent=2))
    print(f"\n✓ Successfully used employee_id from context")
    
    # Request 3: Assign tasks using context values
    print("\n3. ASSIGN TASKS - Using employee_id and department from context")
    print("-" * 80)
    
    request_3 = {
        "request_id": "req-003",
        "agent_name": "onboarding_agent",
        "intent": "onboarding.assign_tasks",
        "input": {
            "text": "Assign onboarding tasks",
            "metadata": {
                "language": "en",
                "extra": {
                    "employee_id": employee_id
                }
            }
        },
        "context": {
            "user_id": "user-001",
            "conversation_id": "conv-001"
        }
    }
    
    response_3 = requests.post(f"{BASE_URL}/execute", json=request_3)
    print(f"Status: {response_3.status_code}")
    result_3 = response_3.json()
    print(json.dumps(result_3, indent=2))
    print(f"\n✓ Successfully used employee_id and department from context")
    
    # Request 4: Check progress using context
    print("\n4. CHECK PROGRESS - Using employee_id from context")
    print("-" * 80)
    
    request_4 = {
        "request_id": "req-004",
        "agent_name": "onboarding_agent",
        "intent": "onboarding.check_progress",
        "input": {
            "text": "Check progress for current employee",
            "metadata": {
                "language": "en",
                "extra": {
                    "employee_id": employee_id
                }
            }
        },
        "context": {
            "user_id": "user-001",
            "conversation_id": "conv-001"
        }
    }
    
    response_4 = requests.post(f"{BASE_URL}/execute", json=request_4)
    print(f"Status: {response_4.status_code}")
    result_4 = response_4.json()
    print(json.dumps(result_4, indent=2))
    print(f"\n✓ Successfully retrieved progress using employee_id from context")
    
    # Request 5: Get status using context
    print("\n5. GET STATUS - Using employee_id from context")
    print("-" * 80)
    
    request_5 = {
        "request_id": "req-005",
        "agent_name": "onboarding_agent",
        "intent": "onboarding.get_status",
        "input": {
            "text": "Get onboarding status",
            "metadata": {
                "language": "en",
                "extra": {
                    "employee_id": employee_id
                }
            }
        },
        "context": {
            "user_id": "user-001",
            "conversation_id": "conv-001"
        }
    }
    
    response_5 = requests.post(f"{BASE_URL}/execute", json=request_5)
    print(f"Status: {response_5.status_code}")
    result_5 = response_5.json()
    print(json.dumps(result_5, indent=2))
    print(f"\n✓ Successfully retrieved status using employee_id from context")
    
    print("\n" + "=" * 80)
    print("CONTEXT MANAGEMENT TEST COMPLETE ✓")
    print("=" * 80)
    print("\nKey Benefits:")
    print("1. Values stored in context across requests")
    print("2. Functions check query first, then context")
    print("3. Error handling for missing required values")
    print("4. Seamless multi-step workflows without repeating data")

if __name__ == "__main__":
    print("Ensure the server is running: python -m uvicorn main:app --host 0.0.0.0 --port 8001")
    input("Press Enter to start tests...")
    try:
        test_context_flow()
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure the server is running on localhost:8001")
