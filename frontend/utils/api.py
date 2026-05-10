import requests

BASE_URL = "http://127.0.0.1:8000"

# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

def login(email: str, password: str):
    response = requests.post(f"{BASE_URL}/auth/login", params={
        "email": email,
        "password": password
    })
    return response.json() if response.status_code == 200 else None

# ══════════════════════════════════════════════════════════════════════════════
# EMPLOYEES
# ══════════════════════════════════════════════════════════════════════════════

def get_all_employees():
    response = requests.get(f"{BASE_URL}/employees/")
    return response.json() if response.status_code == 200 else []

def get_employee(employee_id: int):
    response = requests.get(f"{BASE_URL}/employees/{employee_id}")
    return response.json() if response.status_code == 200 else None

def get_manager_team(manager_id: int):
    response = requests.get(f"{BASE_URL}/employees/manager/{manager_id}/team")
    return response.json() if response.status_code == 200 else []

def update_employee_status(employee_id: int, new_status: str):
    response = requests.put(f"{BASE_URL}/employees/{employee_id}/status",
                           params={"new_status": new_status})
    return response.json() if response.status_code == 200 else None

# ══════════════════════════════════════════════════════════════════════════════
# LEAVE REQUESTS
# ══════════════════════════════════════════════════════════════════════════════

def submit_leave(employee_id: int, leave_type: str, start_date: str,
                 end_date: str, duration_days: int, comment: str = None):
    response = requests.post(f"{BASE_URL}/leaves/submit",
        params={"employee_id": employee_id},
        json={
            "leave_type":       leave_type,
            "start_date":       start_date,
            "end_date":         end_date,
            "duration_days":    duration_days,
            "employee_comment": comment
        }
    )
    return response.json() if response.status_code == 200 else None

def get_my_leaves(employee_id: int):
    response = requests.get(f"{BASE_URL}/leaves/my-requests/{employee_id}")
    return response.json() if response.status_code == 200 else []

def get_pending_manager_leaves(manager_id: int):
    response = requests.get(f"{BASE_URL}/leaves/pending-manager/{manager_id}")
    return response.json() if response.status_code == 200 else []

def get_pending_hr_leaves(city: str):
    response = requests.get(f"{BASE_URL}/leaves/pending-hr/{city}")
    return response.json() if response.status_code == 200 else []

def manager_decision(request_id: int, decision: str, comment: str = None):
    params = {"decision": decision}
    if comment:
        params["comment"] = comment
    response = requests.put(
        f"{BASE_URL}/leaves/{request_id}/manager-decision",
        params=params
    )
    return response.json() if response.status_code == 200 else None

def hr_approve_leave(request_id: int):
    response = requests.put(f"{BASE_URL}/leaves/{request_id}/hr-approve")
    return response.json() if response.status_code == 200 else None

def upload_certificate(request_id: int, file_bytes, filename: str):
    response = requests.post(
        f"{BASE_URL}/leaves/{request_id}/upload-certificate",
        files={"file": (filename, file_bytes, "application/pdf")}
    )
    return response.json() if response.status_code == 200 else None

# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT REQUESTS
# ══════════════════════════════════════════════════════════════════════════════

def submit_document_request(employee_id: int, document_type: str, purpose: str = None):
    response = requests.post(f"{BASE_URL}/documents/submit",
        params={"employee_id": employee_id},
        json={
            "document_type": document_type,
            "purpose":       purpose
        }
    )
    return response.json() if response.status_code == 200 else None

def get_my_documents(employee_id: int):
    response = requests.get(f"{BASE_URL}/documents/my-requests/{employee_id}")
    return response.json() if response.status_code == 200 else []

def get_pending_documents(city: str):
    response = requests.get(f"{BASE_URL}/documents/pending/{city}")
    return response.json() if response.status_code == 200 else []

def get_all_documents(city: str):
    response = requests.get(f"{BASE_URL}/documents/all/{city}")
    return response.json() if response.status_code == 200 else []

def generate_document(doc_request_id: int):
    response = requests.put(f"{BASE_URL}/documents/{doc_request_id}/generate")
    return response.json() if response.status_code == 200 else None

# ══════════════════════════════════════════════════════════════════════════════
# CHATBOT
# ══════════════════════════════════════════════════════════════════════════════

def send_chat_message(employee_id: int, message: str):
    response = requests.post(f"{BASE_URL}/chatbot/message", params={
        "employee_id": employee_id,
        "message":     message
    })
    return response.json() if response.status_code == 200 else None

def get_chat_history(employee_id: int):
    response = requests.get(f"{BASE_URL}/chat/history/{employee_id}")
    return response.json() if response.status_code == 200 else []

def clear_chat_history(employee_id: int):
    response = requests.delete(f"{BASE_URL}/chat/history/{employee_id}/clear")
    return response.json() if response.status_code == 200 else None

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def get_kpis():
    response = requests.get(f"{BASE_URL}/dashboard/kpis")
    return response.json() if response.status_code == 200 else {}

def get_leaves_by_department():
    response = requests.get(f"{BASE_URL}/dashboard/leaves-by-department")
    return response.json() if response.status_code == 200 else []

def get_leaves_by_type():
    response = requests.get(f"{BASE_URL}/dashboard/leaves-by-type")
    return response.json() if response.status_code == 200 else []

def get_leaves_by_status():
    response = requests.get(f"{BASE_URL}/dashboard/leaves-by-status")
    return response.json() if response.status_code == 200 else []

def get_monthly_trends():
    response = requests.get(f"{BASE_URL}/dashboard/monthly-trends")
    return response.json() if response.status_code == 200 else []

def get_documents_by_type():
    response = requests.get(f"{BASE_URL}/dashboard/documents-by-type")
    return response.json() if response.status_code == 200 else []

def get_burnout_risk():
    response = requests.get(f"{BASE_URL}/dashboard/burnout-risk")
    return response.json() if response.status_code == 200 else {}

def get_absence_predictions():
    response = requests.get(f"{BASE_URL}/dashboard/absence-predictions")
    return response.json() if response.status_code == 200 else {}

def get_department_alerts():
    response = requests.get(f"{BASE_URL}/dashboard/department-alerts")
    return response.json() if response.status_code == 200 else {}

def get_city_stats(city: str):
    response = requests.get(f"{BASE_URL}/dashboard/city-stats/{city}")
    return response.json() if response.status_code == 200 else {}

# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def analyze_document(file_bytes, filename: str):
    response = requests.post(
        f"{BASE_URL}/analysis/upload",
        files={"file": (filename, file_bytes, "application/pdf")}
    )
    return response.json() if response.status_code == 200 else None

def confirm_leave_from_analysis(employee_id: int, leave_type: str,
                                 start_date: str, end_date: str,
                                 duration_days: int, comment: str = None):
    response = requests.post(f"{BASE_URL}/analysis/confirm-leave", params={
        "employee_id":    employee_id,
        "leave_type":     leave_type,
        "start_date":     start_date,
        "end_date":       end_date,
        "duration_days":  duration_days,
        "employee_comment": comment
    })
    return response.json() if response.status_code == 200 else None