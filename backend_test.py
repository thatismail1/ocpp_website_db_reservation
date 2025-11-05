#!/usr/bin/env python3
"""
Backend Authentication System Test Suite
Tests the OCPP management website authentication system
"""

import requests
import json
import os
from datetime import datetime

# Get backend URL from environment
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://127.0.0.1:8001')
API_BASE = f"{BACKEND_URL}/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_test_header(test_name):
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== {test_name} ==={Colors.ENDC}")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.ENDC}")

class AuthTestSuite:
    def __init__(self):
        self.admin_token = None
        self.user_token = None
        self.test_results = []
        
    def add_result(self, test_name, passed, message=""):
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
        
    def test_admin_login(self):
        """Test 1: Admin Login"""
        print_test_header("Test 1: Admin Login")
        
        try:
            response = requests.post(f"{API_BASE}/auth/login", json={
                "username": "admin",
                "password": "admin123", 
                "role": "admin"
            })
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['access_token', 'token_type', 'role', 'user_data']
                
                if all(field in data for field in required_fields):
                    if data['role'] == 'admin' and data['token_type'] == 'bearer':
                        self.admin_token = data['access_token']
                        print_success("Admin login successful")
                        print_info(f"Token type: {data['token_type']}")
                        print_info(f"Role: {data['role']}")
                        print_info(f"User data: {data['user_data']}")
                        self.add_result("Admin Login", True)
                        return True
                    else:
                        print_error(f"Invalid role or token_type: {data}")
                        self.add_result("Admin Login", False, "Invalid role or token_type")
                else:
                    print_error(f"Missing required fields in response: {data}")
                    self.add_result("Admin Login", False, "Missing required fields")
            else:
                print_error(f"Login failed with status {response.status_code}: {response.text}")
                self.add_result("Admin Login", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            print_error(f"Admin login test failed: {str(e)}")
            self.add_result("Admin Login", False, str(e))
            
        return False
        
    def test_admin_token_verification(self):
        """Test 2: Admin Token Verification"""
        print_test_header("Test 2: Admin Token Verification")
        
        if not self.admin_token:
            print_error("No admin token available for verification")
            self.add_result("Admin Token Verification", False, "No admin token")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{API_BASE}/auth/verify", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if (data.get('username') == 'admin' and 
                    data.get('role') == 'admin' and 
                    data.get('authenticated') == True):
                    print_success("Admin token verification successful")
                    print_info(f"Verified data: {data}")
                    self.add_result("Admin Token Verification", True)
                    return True
                else:
                    print_error(f"Invalid verification data: {data}")
                    self.add_result("Admin Token Verification", False, "Invalid verification data")
            else:
                print_error(f"Token verification failed with status {response.status_code}: {response.text}")
                self.add_result("Admin Token Verification", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            print_error(f"Admin token verification failed: {str(e)}")
            self.add_result("Admin Token Verification", False, str(e))
            
        return False
        
    def test_user_login_valid(self):
        """Test 3: Valid User Login (DE2DF96C - Murat Gol)"""
        print_test_header("Test 3: Valid User Login (DE2DF96C)")
        
        try:
            response = requests.post(f"{API_BASE}/auth/login", json={
                "username": "DE2DF96C",
                "password": "evcharger2025",
                "role": "user"
            })
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['access_token', 'token_type', 'role', 'user_data']
                
                if all(field in data for field in required_fields):
                    if (data['role'] == 'user' and 
                        data['token_type'] == 'bearer' and
                        'id_tag' in data['user_data'] and
                        'full_name' in data['user_data'] and
                        'plan' in data['user_data']):
                        
                        self.user_token = data['access_token']
                        print_success("User login successful")
                        print_info(f"Token type: {data['token_type']}")
                        print_info(f"Role: {data['role']}")
                        print_info(f"User data: {data['user_data']}")
                        
                        # Verify user data matches expected values
                        user_data = data['user_data']
                        if (user_data['id_tag'] == 'DE2DF96C' and
                            'Murat' in user_data['full_name'] and
                            'Gol' in user_data['full_name']):
                            print_success("User data matches expected values")
                            self.add_result("Valid User Login", True)
                            return True
                        else:
                            print_error(f"User data doesn't match expected values: {user_data}")
                            self.add_result("Valid User Login", False, "User data mismatch")
                    else:
                        print_error(f"Invalid user login response structure: {data}")
                        self.add_result("Valid User Login", False, "Invalid response structure")
                else:
                    print_error(f"Missing required fields in user login response: {data}")
                    self.add_result("Valid User Login", False, "Missing required fields")
            else:
                print_error(f"User login failed with status {response.status_code}: {response.text}")
                self.add_result("Valid User Login", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            print_error(f"User login test failed: {str(e)}")
            self.add_result("Valid User Login", False, str(e))
            
        return False
        
    def test_user_login_invalid_rfid(self):
        """Test 4: Invalid RFID Tag Login"""
        print_test_header("Test 4: Invalid RFID Tag Login")
        
        try:
            response = requests.post(f"{API_BASE}/auth/login", json={
                "username": "INVALID123",
                "password": "evcharger2025",
                "role": "user"
            })
            
            if response.status_code == 401:
                print_success("Invalid RFID correctly rejected with 401 Unauthorized")
                self.add_result("Invalid RFID Login", True)
                return True
            else:
                print_error(f"Expected 401 but got {response.status_code}: {response.text}")
                self.add_result("Invalid RFID Login", False, f"Expected 401, got {response.status_code}")
                
        except Exception as e:
            print_error(f"Invalid RFID test failed: {str(e)}")
            self.add_result("Invalid RFID Login", False, str(e))
            
        return False
        
    def test_user_login_wrong_password(self):
        """Test 5: Valid RFID with Wrong Password"""
        print_test_header("Test 5: Valid RFID with Wrong Password")
        
        try:
            response = requests.post(f"{API_BASE}/auth/login", json={
                "username": "DE2DF96C",
                "password": "wrongpass",
                "role": "user"
            })
            
            if response.status_code == 401:
                print_success("Wrong password correctly rejected with 401 Unauthorized")
                self.add_result("Wrong Password Login", True)
                return True
            else:
                print_error(f"Expected 401 but got {response.status_code}: {response.text}")
                self.add_result("Wrong Password Login", False, f"Expected 401, got {response.status_code}")
                
        except Exception as e:
            print_error(f"Wrong password test failed: {str(e)}")
            self.add_result("Wrong Password Login", False, str(e))
            
        return False
        
    def test_user_dashboard_access(self):
        """Test 6: User Dashboard Access with User Token"""
        print_test_header("Test 6: User Dashboard Access")
        
        if not self.user_token:
            print_error("No user token available for dashboard test")
            self.add_result("User Dashboard Access", False, "No user token")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"}
            response = requests.get(f"{API_BASE}/user/dashboard", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                required_sections = ['user_info', 'chargers', 'active_session', 'transaction_history']
                
                if all(section in data for section in required_sections):
                    user_info = data['user_info']
                    required_user_fields = ['id_tag', 'full_name', 'plan', 'quota_kwh', 'used_kwh', 'remaining_kwh', 'unlimited']
                    
                    if all(field in user_info for field in required_user_fields):
                        print_success("User dashboard access successful")
                        print_info(f"User info: {user_info}")
                        print_info(f"Number of chargers: {len(data['chargers'])}")
                        print_info(f"Active session: {data['active_session']}")
                        print_info(f"Transaction history entries: {len(data['transaction_history'])}")
                        self.add_result("User Dashboard Access", True)
                        return True
                    else:
                        print_error(f"Missing user_info fields: {user_info}")
                        self.add_result("User Dashboard Access", False, "Missing user_info fields")
                else:
                    print_error(f"Missing required sections in dashboard response: {list(data.keys())}")
                    self.add_result("User Dashboard Access", False, "Missing required sections")
            else:
                print_error(f"Dashboard access failed with status {response.status_code}: {response.text}")
                self.add_result("User Dashboard Access", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            print_error(f"User dashboard test failed: {str(e)}")
            self.add_result("User Dashboard Access", False, str(e))
            
        return False
        
    def test_user_dashboard_admin_access(self):
        """Test 7: User Dashboard Access with Admin Token (Should Fail)"""
        print_test_header("Test 7: User Dashboard with Admin Token (Should Fail)")
        
        if not self.admin_token:
            print_error("No admin token available for this test")
            self.add_result("Admin Dashboard Access Denial", False, "No admin token")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{API_BASE}/user/dashboard", headers=headers)
            
            if response.status_code == 403:
                print_success("Admin correctly denied access to user dashboard with 403 Forbidden")
                self.add_result("Admin Dashboard Access Denial", True)
                return True
            else:
                print_error(f"Expected 403 but got {response.status_code}: {response.text}")
                self.add_result("Admin Dashboard Access Denial", False, f"Expected 403, got {response.status_code}")
                
        except Exception as e:
            print_error(f"Admin dashboard denial test failed: {str(e)}")
            self.add_result("Admin Dashboard Access Denial", False, str(e))
            
        return False
        
    def test_users_endpoint_read_access(self):
        """Test 8: Users Endpoint Read Access (Should Work for All)"""
        print_test_header("Test 8: Users Endpoint Read Access")
        
        if not self.user_token:
            print_error("No user token available for this test")
            self.add_result("Users Read Access", False, "No user token")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"}
            response = requests.get(f"{API_BASE}/users", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    print_success(f"Users endpoint accessible to user token, returned {len(data)} users")
                    self.add_result("Users Read Access", True)
                    return True
                else:
                    print_error(f"Unexpected users data format: {data}")
                    self.add_result("Users Read Access", False, "Unexpected data format")
            else:
                print_error(f"Users endpoint failed with status {response.status_code}: {response.text}")
                self.add_result("Users Read Access", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            print_error(f"Users read access test failed: {str(e)}")
            self.add_result("Users Read Access", False, str(e))
            
        return False
        
    def test_users_create_admin_only(self):
        """Test 9: Users Create Endpoint (Admin Only)"""
        print_test_header("Test 9: Users Create Endpoint (Admin Only)")
        
        if not self.user_token:
            print_error("No user token available for this test")
            self.add_result("Users Create Admin Only", False, "No user token")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"}
            response = requests.post(f"{API_BASE}/users", 
                headers=headers,
                json={
                    "id_tag": "TESTUSER123",
                    "header_name": "Test",
                    "surname": "User",
                    "plan": "limited",
                    "quota_kwh": 50.0
                })
            
            if response.status_code == 403:
                print_success("User correctly denied access to create users with 403 Forbidden")
                self.add_result("Users Create Admin Only", True)
                return True
            else:
                print_error(f"Expected 403 but got {response.status_code}: {response.text}")
                self.add_result("Users Create Admin Only", False, f"Expected 403, got {response.status_code}")
                
        except Exception as e:
            print_error(f"Users create admin only test failed: {str(e)}")
            self.add_result("Users Create Admin Only", False, str(e))
            
        return False
        
    def test_users_delete_admin_only(self):
        """Test 10: Users Delete Endpoint (Admin Only)"""
        print_test_header("Test 10: Users Delete Endpoint (Admin Only)")
        
        if not self.user_token:
            print_error("No user token available for this test")
            self.add_result("Users Delete Admin Only", False, "No user token")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.user_token}"}
            response = requests.delete(f"{API_BASE}/users/someuser", headers=headers)
            
            if response.status_code == 403:
                print_success("User correctly denied access to delete users with 403 Forbidden")
                self.add_result("Users Delete Admin Only", True)
                return True
            else:
                print_error(f"Expected 403 but got {response.status_code}: {response.text}")
                self.add_result("Users Delete Admin Only", False, f"Expected 403, got {response.status_code}")
                
        except Exception as e:
            print_error(f"Users delete admin only test failed: {str(e)}")
            self.add_result("Users Delete Admin Only", False, str(e))
            
        return False
        
    def test_another_valid_rfid(self):
        """Test 11: Another Valid RFID Login (25A8C634 - Ozan Keysan)"""
        print_test_header("Test 11: Another Valid RFID Login (25A8C634)")
        
        try:
            response = requests.post(f"{API_BASE}/auth/login", json={
                "username": "25A8C634",
                "password": "evcharger2025",
                "role": "user"
            })
            
            if response.status_code == 200:
                data = response.json()
                if (data.get('role') == 'user' and 
                    'user_data' in data and
                    data['user_data'].get('id_tag') == '25A8C634'):
                    
                    user_data = data['user_data']
                    if 'Ozan' in user_data.get('full_name', '') and 'Keysan' in user_data.get('full_name', ''):
                        print_success("Second RFID login successful")
                        print_info(f"User data: {user_data}")
                        self.add_result("Another Valid RFID Login", True)
                        return True
                    else:
                        print_error(f"User data doesn't match expected values for Ozan Keysan: {user_data}")
                        self.add_result("Another Valid RFID Login", False, "User data mismatch")
                else:
                    print_error(f"Invalid response for second RFID: {data}")
                    self.add_result("Another Valid RFID Login", False, "Invalid response")
            else:
                print_error(f"Second RFID login failed with status {response.status_code}: {response.text}")
                self.add_result("Another Valid RFID Login", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            print_error(f"Second RFID login test failed: {str(e)}")
            self.add_result("Another Valid RFID Login", False, str(e))
            
        return False
        
    def run_all_tests(self):
        """Run all authentication tests"""
        print(f"{Colors.BOLD}{Colors.BLUE}🚀 Starting OCPP Authentication System Tests{Colors.ENDC}")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"API Base: {API_BASE}")
        
        # Run all tests in sequence
        tests = [
            self.test_admin_login,
            self.test_admin_token_verification,
            self.test_user_login_valid,
            self.test_user_login_invalid_rfid,
            self.test_user_login_wrong_password,
            self.test_user_dashboard_access,
            self.test_user_dashboard_admin_access,
            self.test_users_endpoint_read_access,
            self.test_users_create_admin_only,
            self.test_users_delete_admin_only,
            self.test_another_valid_rfid
        ]
        
        for test in tests:
            test()
            
        # Print summary
        self.print_summary()
        
    def print_summary(self):
        """Print test results summary"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}📊 TEST RESULTS SUMMARY{Colors.ENDC}")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['passed'])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            message = f" - {result['message']}" if result['message'] else ""
            print(f"{status} {result['test']}{message}")
            
        print("=" * 60)
        if passed == total:
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED ({passed}/{total}){Colors.ENDC}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}⚠️  {total - passed} TESTS FAILED ({passed}/{total}){Colors.ENDC}")
            
        return passed == total

if __name__ == "__main__":
    test_suite = AuthTestSuite()
    success = test_suite.run_all_tests()
    exit(0 if success else 1)