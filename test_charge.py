from locust import HttpUser, task, between

class ChatbotUser(HttpUser):
    wait_time = between(15, 20)

    @task
    def send_message(self):
        self.client.post("/chatbot/message", params={
            "employee_id": 45,
            "message": "Quel est mon solde de congés ?"
        })
'''   
from locust import HttpUser, task, between

class EmployeeListUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def get_employees(self):
        self.client.get("/employees/")   
'''     