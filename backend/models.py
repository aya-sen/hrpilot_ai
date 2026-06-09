from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Enum, Text
from backend.database import Base
from sqlalchemy.sql import func

class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    gender = Column(Enum('Male', 'Female'), nullable=False)
    birth_date = Column(Date, nullable=False)
    city = Column(String(50), nullable=False)
    department = Column(String(50), nullable=False)
    position = Column(String(100), nullable=False)
    manager_id = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)
    contract_type = Column(Enum('CDI', 'CDD', 'Stage'), nullable=False)
    hire_date = Column(Date, nullable=False)
    salary = Column(Numeric(10, 2), nullable=False)
    leave_balance_days = Column(Integer, nullable=False, default=28)
    status = Column(Enum('Active', 'On Leave','On leave', 'Resigned'), nullable=False, default='Active')
    role = Column(Enum('Employee', 'Manager', 'HR'), nullable=True, default='Employee')
    


class LeaveRequest(Base):
    __tablename__ = "leave_request"

    request_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    manager_id  = Column(Integer, ForeignKey("employees.employee_id"), nullable=True)
    leave_type = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_days = Column(Integer , nullable=True)
    status = Column(String(20), nullable=False, default='Pending_Manager')
    submission_date = Column(Date, nullable=False)
    employee_comment  = Column(Text, nullable=True)        
    certificate_file_path = Column(String(255), nullable=True)
    manager_comment = Column(Text, nullable=True)


class DocumentRequest(Base):
    __tablename__ = "document_request"

    doc_request_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String(100), nullable=False)
    purpose = Column(String(255) , nullable=True)
    status = Column(String(20), nullable=False, default='Pending')
    request_date = Column(Date, nullable=False)
    generated_file_path = Column(String(255), nullable=True)
    delivery_date = Column(Date, nullable=True) 


class ChatHistory(Base):
    __tablename__ = "chat_history"

    chat_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)
    message  = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)


class InternalRule(Base):
    __tablename__ = "internal_rules"

    rule_id    = Column(Integer, primary_key=True, index=True)
    category   = Column(String(100), nullable=False)
    title      = Column(String(255), nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

    