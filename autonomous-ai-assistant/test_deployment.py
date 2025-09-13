#!/usr/bin/env python3
"""
Autonomous AI Assistant - Deployment Test Script
This script tests all major functionalities of the deployed system.
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List
import os

class DeploymentTester:
    """Test suite for the Autonomous AI Assistant deployment"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.test_results = []
        self.passed = 0
        self.failed = 0
        
    def print_header(self, title: str):
        """Print a formatted test section header"""
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")
    
    def print_test(self, test_name: str, status: str, message: str = ""):
        """Print test result"""
        status_symbol = "✓" if status == "PASS" else "✗"
        status_color = "\033[92m" if status == "PASS" else "\033[91m"
        reset_color = "\033[0m"
        
        print(f"{status_color}{status_symbol} {test_name:<40} [{status}]{reset_color}")
        if message:
            print(f"    {message}")
        
        if status == "PASS":
            self.passed += 1
        else:
            self.failed += 1
            
        self.test_results.append({
            "test": test_name,
            "status": status,
            "message": message
        })
    
    def make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request and return response"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return {
                "success": True,
                "status_code": response.status_code,
                "data": response.json() if response.content else {}
            }
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Connection refused - service may not be running"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON response"}
    
    def test_system_health(self):
        """Test system health and availability"""
        self.print_header("SYSTEM HEALTH TESTS")
        
        # Test main health endpoint
        response = self.make_request("/health")
        if response["success"] and response["status_code"] == 200:
            health_data = response["data"]
            if health_data.get("status") == "healthy":
                self.print_test("Health Check", "PASS", "System is healthy")
                
                # Check individual services
                services = health_data.get("services", {})
                for service, status in services.items():
                    service_status = "PASS" if status else "FAIL"
                    self.print_test(f"Service: {service}", service_status)
            else:
                self.print_test("Health Check", "FAIL", "System reports unhealthy status")
        else:
            error_msg = response.get("error", f"HTTP {response.get('status_code', 'unknown')}")
            self.print_test("Health Check", "FAIL", error_msg)
        
        # Test API status
        response = self.make_request("/api/status")
        if response["success"] and response["status_code"] == 200:
            self.print_test("API Status", "PASS")
        else:
            self.print_test("API Status", "FAIL", response.get("error", "API not responding"))
    
    def test_nlp_processing(self):
        """Test NLP processing functionality"""
        self.print_header("NLP PROCESSING TESTS")
        
        test_commands = [
            {"command": "Create a folder named TestFolder", "expected_intent": "File Management"},
            {"command": "Send an email to john@example.com", "expected_intent": "Email Handling"},
            {"command": "Schedule a meeting tomorrow at 3pm", "expected_intent": "Scheduling"},
            {"command": "Analyze the sales data", "expected_intent": "Data Analysis"}
        ]
        
        for test_case in test_commands:
            response = self.make_request("/process", "POST", {"command": test_case["command"]})
            
            if response["success"] and response["status_code"] == 200:
                data = response["data"]
                if data.get("status") == "success":
                    intent_label = data.get("intent", {}).get("label", "")
                    if intent_label == test_case["expected_intent"]:
                        confidence = data.get("intent", {}).get("score", 0)
                        self.print_test(f"NLP: {test_case['command'][:30]}...", "PASS", 
                                      f"Intent: {intent_label}, Confidence: {confidence:.2f}")
                    else:
                        self.print_test(f"NLP: {test_case['command'][:30]}...", "FAIL", 
                                      f"Expected {test_case['expected_intent']}, got {intent_label}")
                else:
                    self.print_test(f"NLP: {test_case['command'][:30]}...", "FAIL", 
                                  data.get("error", "Processing failed"))
            else:
                self.print_test(f"NLP: {test_case['command'][:30]}...", "FAIL", 
                              response.get("error", "Request failed"))
    
    def test_file_management(self):
        """Test file management operations"""
        self.print_header("FILE MANAGEMENT TESTS")
        
        # Test folder creation
        response = self.make_request("/execute/file_management", "POST", {
            "action": "create_folder",
            "parameters": {"folder_name": "TestDeploymentFolder"}
        })
        
        if response["success"] and response["status_code"] == 200:
            data = response["data"]
            if data.get("status") == "success":
                self.print_test("Create Folder", "PASS", data.get("message", ""))
            else:
                self.print_test("Create Folder", "FAIL", data.get("message", ""))
        else:
            self.print_test("Create Folder", "FAIL", response.get("error", "Request failed"))
        
        # Test file listing
        response = self.make_request("/execute/file_management", "POST", {
            "action": "list_files"
        })
        
        if response["success"] and response["status_code"] == 200:
            data = response["data"]
            if data.get("status") == "success":
                file_count = data.get("total_items", 0)
                self.print_test("List Files", "PASS", f"Found {file_count} items")
            else:
                self.print_test("List Files", "FAIL", data.get("message", ""))
        else:
            self.print_test("List Files", "FAIL", response.get("error", "Request failed"))
        
        # Test file creation
        response = self.make_request("/execute/file_management", "POST", {
            "action": "create_file",
            "parameters": {
                "file_name": "test_deployment.txt",
                "content": "This is a test file created during deployment testing."
            }
        })
        
        if response["success"] and response["status_code"] == 200:
            data = response["data"]
            if data.get("status") == "success":
                self.print_test("Create File", "PASS", data.get("message", ""))
            else:
                self.print_test("Create File", "FAIL", data.get("message", ""))
        else:
            self.print_test("Create File", "FAIL", response.get("error", "Request failed"))
    
    def test_smart_command_execution(self):
        """Test smart command execution"""
        self.print_header("SMART COMMAND EXECUTION TESTS")
        
        test_commands = [
            "Create a folder named SmartTestFolder",
            "List all files in the current directory",
            "Schedule a meeting with the team tomorrow at 2pm"
        ]
        
        for command in test_commands:
            response = self.make_request("/execute/smart_command", "POST", {"command": command})
            
            if response["success"] and response["status_code"] == 200:
                data = response["data"]
                processed_command = data.get("processed_command", {})
                execution_result = data.get("execution_result", {})
                
                intent_label = processed_command.get("intent", {}).get("label", "Unknown")
                exec_status = execution_result.get("status", "unknown")
                
                if exec_status in ["success", "info"]:
                    self.print_test(f"Smart: {command[:25]}...", "PASS", 
                                  f"Intent: {intent_label}, Status: {exec_status}")
                else:
                    self.print_test(f"Smart: {command[:25]}...", "FAIL", 
                                  execution_result.get("message", "Execution failed"))
            else:
                self.print_test(f"Smart: {command[:25]}...", "FAIL", 
                              response.get("error", "Request failed"))
    
    def test_rag_system(self):
        """Test RAG system functionality"""
        self.print_header("RAG SYSTEM TESTS")
        
        # Test adding context
        test_context = "The deployment test was successful on " + time.strftime("%Y-%m-%d %H:%M:%S")
        response = self.make_request("/add_context", "POST", {"text": test_context})
        
        if response["success"] and response["status_code"] == 201:
            self.print_test("Add Context", "PASS", "Context added successfully")
        else:
            self.print_test("Add Context", "FAIL", response.get("error", "Failed to add context"))
        
        # Test retrieving context
        time.sleep(1)  # Brief pause to ensure indexing
        response = self.make_request("/get_context", "POST", {
            "query": "deployment test", 
            "k": 3
        })
        
        if response["success"] and response["status_code"] == 200:
            data = response["data"]
            if data.get("status") == "success":
                results = data.get("results", [])
                self.print_test("Retrieve Context", "PASS", f"Found {len(results)} relevant results")
            else:
                self.print_test("Retrieve Context", "FAIL", data.get("message", ""))
        else:
            self.print_test("Retrieve Context", "FAIL", response.get("error", "Request failed"))
        
        # Test RAG statistics
        response = self.make_request("/system/rag/stats")
        if response["success"] and response["status_code"] == 200:
            data = response["data"]
            doc_count = data.get("total_documents", 0)
            model_type = data.get("model_type", "unknown")
            self.print_test("RAG Statistics", "PASS", 
                          f"Documents: {doc_count}, Model: {model_type}")
        else:
            self.print_test("RAG Statistics", "FAIL", response.get("error", "Request failed"))
    
    def test_data_analysis(self):
        """Test data analysis functionality"""
        self.print_header("DATA ANALYSIS TESTS")
        
        # Test quick summary of sample data
        response = self.make_request("/execute/data_analysis", "POST", {
            "action": "quick_summary",
            "parameters": {
                "file_path": "/usr/src/app/data/output/sample_data.csv"
            }
        })
        
        if response["success"] and response["status_code"] == 200:
            data = response["data"]
            if data.get("status") == "success":
                shape = data.get("shape", [0, 0])
                columns = len(data.get("columns", []))
                self.print_test("Data Quick Summary", "PASS", 
                              f"Shape: {shape[0]}x{shape[1]}, Columns: {columns}")
            else:
                self.print_test("Data Quick Summary", "FAIL", data.get("message", ""))
        else:
            self.print_test("Data Quick Summary", "FAIL", response.get("error", "Request failed"))
    
    def test_calendar_integration(self):
        """Test calendar integration"""
        self.print_header("CALENDAR INTEGRATION TESTS")
        
        # Test meeting creation from command
        response = self.make_request("/execute/calendar", "POST", {
            "action": "create_from_command",
            "parameters": {
                "command": "Schedule a test meeting tomorrow at 10am"
            }
        })
        
        if response["success"] and response["status_code"] == 200:
            data = response["data"]
            if data.get("status") == "success":
                event_id = data.get("event_id", "unknown")
                self.print_test("Create Meeting", "PASS", f"Event ID: {event_id}")
            else:
                self.print_test("Create Meeting", "FAIL", data.get("message", ""))
        else:
            self.print_test("Create Meeting", "FAIL", response.get("error", "Request failed"))
        
        # Test getting schedule
        response = self.make_request("/execute/calendar", "POST", {
            "action": "get_schedule"
        })
        
        if response["success"] and response["status_code"] == 200:
            data = response["data"]
            if data.get("status") == "success":
                events = data.get("events", [])
                self.print_test("Get Schedule", "PASS", f"Found {len(events)} events")
            else:
                self.print_test("Get Schedule", "FAIL", data.get("message", ""))
        else:
            self.print_test("Get Schedule", "FAIL", response.get("error", "Request failed"))
    
    def test_system_stats(self):
        """Test system statistics"""
        self.print_header("SYSTEM STATISTICS TESTS")
        
        response = self.make_request("/system/stats")
        if response["success"] and response["status_code"] == 200:
            data = response["data"]
            system_info = data.get("system_info", {})
            resources = data.get("resources", {})
            
            if system_info:
                platform = system_info.get("platform", "unknown")
                python_version = system_info.get("python_version", "unknown")
                self.print_test("System Info", "PASS", 
                              f"Platform: {platform}, Python: {python_version}")
                
                if resources:
                    cpu_percent = resources.get("cpu_percent", 0)
                    memory_percent = resources.get("memory_percent", 0)
                    self.print_test("Resource Usage", "PASS", 
                                  f"CPU: {cpu_percent}%, Memory: {memory_percent}%")
                else:
                    self.print_test("Resource Usage", "PASS", "Basic stats available")
            else:
                self.print_test("System Info", "FAIL", "No system info available")
        else:
            self.print_test("System Statistics", "FAIL", response.get("error", "Request failed"))
    
    def run_all_tests(self):
        """Run all test suites"""
        print("\n🤖 Autonomous AI Assistant - Deployment Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run test suites
        self.test_system_health()
        self.test_nlp_processing()
        self.test_file_management()
        self.test_smart_command_execution()
        self.test_rag_system()
        self.test_data_analysis()
        self.test_calendar_integration()
        self.test_system_stats()
        
        # Print summary
        end_time = time.time()
        duration = end_time - start_time
        
        self.print_header("TEST SUMMARY")
        
        total_tests = self.passed + self.failed
        pass_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests:     {total_tests}")
        print(f"Passed:          \033[92m{self.passed}\033[0m")
        print(f"Failed:          \033[91m{self.failed}\033[0m")
        print(f"Pass Rate:       {pass_rate:.1f}%")
        print(f"Duration:        {duration:.2f} seconds")
        
        if self.failed == 0:
            print(f"\n🎉 \033[92mAll tests passed! Deployment is successful.\033[0m")
            return True
        else:
            print(f"\n❌ \033[91m{self.failed} tests failed. Please check the issues above.\033[0m")
            return False
    
    def generate_report(self, filename: str = "test_report.json"):
        """Generate detailed test report"""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": self.passed + self.failed,
                "passed": self.passed,
                "failed": self.failed,
                "pass_rate": (self.passed / (self.passed + self.failed) * 100) if (self.passed + self.failed) > 0 else 0
            },
            "test_results": self.test_results
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Test report saved to: {filename}")
        except Exception as e:
            print(f"\n⚠️  Failed to save test report: {e}")


def main():
    """Main function to run tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Autonomous AI Assistant deployment')
    parser.add_argument('--url', default='http://localhost:5000', 
                       help='Base URL for the application (default: http://localhost:5000)')
    parser.add_argument('--report', default='test_report.json', 
                       help='Output file for test report (default: test_report.json)')
    parser.add_argument('--wait', type=int, default=0,
                       help='Wait time in seconds before starting tests')
    
    args = parser.parse_args()
    
    if args.wait > 0:
        print(f"Waiting {args.wait} seconds for services to be ready...")
        time.sleep(args.wait)
    
    tester = DeploymentTester(args.url)
    success = tester.run_all_tests()
    tester.generate_report(args.report)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()