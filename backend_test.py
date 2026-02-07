#!/usr/bin/env python3
import requests
import sys
import json
from datetime import datetime

class WorkflowBridgeAPITester:
    def __init__(self, base_url="https://workflow-bridge-15.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.admin_token = None
        self.test_user_id = None
        self.test_approver_id = None
        self.test_request_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.errors = []

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, use_admin=False):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        test_headers = {'Content-Type': 'application/json'}
        
        # Use admin token if specified
        token_to_use = self.admin_token if use_admin else self.token
        if token_to_use:
            test_headers['Authorization'] = f'Bearer {token_to_use}'
        if headers:
            test_headers.update(headers)
            
        # Debug logging
        self.log(f"  → {method} {url}")
        if token_to_use:
            self.log(f"  → Using token: {token_to_use[:20]}...{token_to_use[-10:]}")
        else:
            self.log("  → No token provided")

        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - {name} - Status: {response.status_code}")
                try:
                    return True, response.json() if response.text else {}
                except:
                    return True, {}
            else:
                error_msg = f"❌ FAILED - {name} - Expected {expected_status}, got {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail.get('detail', response.text[:100])}"
                except:
                    error_msg += f" - {response.text[:100]}"
                self.log(error_msg)
                self.errors.append(error_msg)
                return False, {}

        except requests.exceptions.Timeout:
            error_msg = f"❌ TIMEOUT - {name} - Request timed out after 30 seconds"
            self.log(error_msg)
            self.errors.append(error_msg)
            return False, {}
        except Exception as e:
            error_msg = f"❌ ERROR - {name} - Exception: {str(e)}"
            self.log(error_msg)
            self.errors.append(error_msg)
            return False, {}

    def test_auth_flow(self):
        """Test authentication endpoints"""
        self.log("🔐 TESTING AUTHENTICATION FLOW")
        
        # Test admin login
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@company.com", "password": "admin123"}
        )
        if success and 'token' in response:
            self.admin_token = response['token']
            self.token = response['token']  # Use admin token initially
            self.log(f"✓ Admin login successful, user: {response.get('user', {}).get('name', 'Unknown')}")
            return True
        return False

    def test_user_management(self):
        """Test user management endpoints"""
        self.log("👥 TESTING USER MANAGEMENT")
        
        # List users
        success, users_data = self.run_test("List Users", "GET", "users", 200, use_admin=True)
        if not success:
            return False
            
        # Create test approver user
        success, approver = self.run_test(
            "Create Test Approver",
            "POST",
            "users",
            201,
            data={
                "email": "test_approver@company.com",
                "password": "test123",
                "name": "Test Approver",
                "role": "approver",
                "department_id": "dept_general"  # Assuming general dept exists
            },
            use_admin=True
        )
        if success:
            self.test_approver_id = approver.get('id')
            self.log(f"✓ Test approver created with ID: {self.test_approver_id}")
        
        # Create test requestor user
        success, requestor = self.run_test(
            "Create Test Requestor",
            "POST",
            "users",
            201,
            data={
                "email": "test_requestor@company.com",
                "password": "test123", 
                "name": "Test Requestor",
                "role": "requestor",
                "department_id": "dept_general"
            },
            use_admin=True
        )
        if success:
            self.test_user_id = requestor.get('id')
            self.log(f"✓ Test requestor created with ID: {self.test_user_id}")

        # List approvers
        success, approvers = self.run_test("List Approvers", "GET", "users/approvers", 200)
        if success:
            self.log(f"✓ Found {len(approvers)} approvers")

        return success

    def test_departments_and_templates(self):
        """Test departments and form templates"""
        self.log("🏢 TESTING DEPARTMENTS & TEMPLATES")
        
        # List departments  
        success, departments = self.run_test("List Departments", "GET", "departments", 200)
        if not success:
            return False
        self.log(f"✓ Found {len(departments)} departments")
        
        # List form templates
        success, templates = self.run_test("List Form Templates", "GET", "form-templates", 200)
        if not success:
            return False
        self.log(f"✓ Found {len(templates)} form templates")
        
        # Get all templates (admin)
        success, all_templates = self.run_test("List All Templates (Admin)", "GET", "form-templates/all", 200, use_admin=True)
        if success:
            self.log(f"✓ Admin can see {len(all_templates)} templates")
            
            # Try to assign approver to first template
            if all_templates and self.test_approver_id:
                first_template = all_templates[0]
                success, updated = self.run_test(
                    "Assign Approver to Template",
                    "PUT",
                    f"form-templates/{first_template['id']}",
                    200,
                    data={
                        "approver_chain": [
                            {
                                "step": 1,
                                "user_id": self.test_approver_id,
                                "user_name": "Test Approver"
                            }
                        ]
                    },
                    use_admin=True
                )
                if success:
                    self.log("✓ Successfully assigned approver to template")
        
        return success

    def test_request_flow(self):
        """Test request creation and approval flow"""
        self.log("📋 TESTING REQUEST WORKFLOW")
        
        # First, login as requestor
        success, response = self.run_test(
            "Requestor Login",
            "POST", 
            "auth/login",
            200,
            data={"email": "test_requestor@company.com", "password": "test123"}
        )
        if success:
            self.token = response['token']  # Switch to requestor token
            self.log("✓ Logged in as test requestor")
        else:
            return False
        
        # List templates for requestor
        success, templates = self.run_test("List Templates (Requestor)", "GET", "form-templates", 200)
        if not success or not templates:
            return False
            
        # Create a request using the first template
        first_template = templates[0]
        form_data = {}
        for field in first_template.get('fields', []):
            form_data[field['name']] = f"test_{field['name']}_value"
            
        success, request = self.run_test(
            "Create New Request",
            "POST",
            "requests",
            201,
            data={
                "form_template_id": first_template['id'],
                "title": "Test Request - Office Supplies",
                "form_data": form_data,
                "notes": "This is a test request",
                "priority": "normal"
            }
        )
        if success:
            self.test_request_id = request.get('id')
            self.log(f"✓ Request created: {request.get('request_number')} - Status: {request.get('status')}")
        else:
            return False
        
        # List requests as requestor
        success, requests_data = self.run_test("List My Requests", "GET", "requests?my_requests=true", 200)
        if success:
            self.log(f"✓ Requestor can see {len(requests_data.get('items', []))} requests")
        
        # Get specific request details
        success, request_detail = self.run_test(
            "Get Request Details",
            "GET",
            f"requests/{self.test_request_id}",
            200
        )
        if success:
            self.log(f"✓ Retrieved request details: {request_detail.get('title')}")
        
        # Now switch to approver and test approval flow
        if self.test_approver_id:
            success, response = self.run_test(
                "Approver Login",
                "POST",
                "auth/login", 
                200,
                data={"email": "test_approver@company.com", "password": "test123"}
            )
            if success:
                self.token = response['token']  # Switch to approver token
                self.log("✓ Logged in as test approver")
                
                # List pending approvals
                success, pending = self.run_test("List Pending Approvals", "GET", "requests?my_approvals=true", 200)
                if success:
                    pending_count = len(pending.get('items', []))
                    self.log(f"✓ Approver has {pending_count} pending approvals")
                    
                    # Approve the request if it's pending
                    if pending_count > 0 and self.test_request_id:
                        success, approved = self.run_test(
                            "Approve Request",
                            "POST",
                            f"requests/{self.test_request_id}/action",
                            200,
                            data={
                                "action": "approve",
                                "comments": "Approved via automated test"
                            }
                        )
                        if success:
                            self.log(f"✓ Request approved - New status: {approved.get('status')}")
        
        return True

    def test_notifications(self):
        """Test notifications system"""
        self.log("🔔 TESTING NOTIFICATIONS")
        
        # List notifications
        success, notifs = self.run_test("List Notifications", "GET", "notifications", 200)
        if success:
            total = notifs.get('total', 0)
            unread = notifs.get('unread_count', 0)
            self.log(f"✓ Found {total} notifications ({unread} unread)")
            
            # Mark all as read if there are any
            if unread > 0:
                success, _ = self.run_test("Mark All Notifications Read", "POST", "notifications/read-all", 200)
                if success:
                    self.log("✓ Marked all notifications as read")
        
        return success

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        self.log("📊 TESTING DASHBOARD STATS")
        
        # Switch back to admin token for stats
        self.token = self.admin_token
        
        success, stats = self.run_test("Get Dashboard Stats", "GET", "dashboard/stats", 200)
        if success:
            self.log(f"✓ Stats - Users: {stats.get('total_users', 0)}, "
                    f"Requests: {stats.get('total_requests', 0)}, "
                    f"Templates: {stats.get('total_templates', 0)}")
        
        return success

    def cleanup_test_data(self):
        """Clean up test data"""
        self.log("🧹 CLEANING UP TEST DATA")
        
        # Switch to admin token for cleanup
        self.token = self.admin_token
        
        # Delete test users
        if self.test_user_id:
            success, _ = self.run_test("Delete Test Requestor", "DELETE", f"users/{self.test_user_id}", 200, use_admin=True)
            if success:
                self.log("✓ Test requestor deleted")
        
        if self.test_approver_id:
            success, _ = self.run_test("Delete Test Approver", "DELETE", f"users/{self.test_approver_id}", 200, use_admin=True)
            if success:
                self.log("✓ Test approver deleted")

    def run_all_tests(self):
        """Run complete test suite"""
        self.log("🚀 STARTING WORKFLOW BRIDGE API TESTS")
        self.log(f"Base URL: {self.base_url}")
        
        try:
            # Test authentication first
            if not self.test_auth_flow():
                self.log("❌ Authentication failed, stopping tests")
                return False
                
            # Test user management
            self.test_user_management()
            
            # Test departments and templates
            self.test_departments_and_templates()
            
            # Test request workflow
            self.test_request_flow()
            
            # Test notifications
            self.test_notifications()
            
            # Test dashboard stats
            self.test_dashboard_stats()
            
        except Exception as e:
            self.log(f"❌ Unexpected error during testing: {str(e)}")
        finally:
            # Always try to cleanup
            self.cleanup_test_data()
        
        # Print final results
        self.log("\n" + "="*60)
        self.log(f"📊 FINAL RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.errors:
            self.log(f"\n❌ FAILED TESTS ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10 errors
                self.log(f"  • {error}")
            if len(self.errors) > 10:
                self.log(f"  ... and {len(self.errors) - 10} more errors")
        
        return success_rate >= 80  # Consider 80%+ success rate as passing


def main():
    tester = WorkflowBridgeAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())