# TODO - Secure temp password workflow (HR add -> email -> forced change)

## Backend (FastAPI)
- [x] Add `must_change_password` column to `backend/models.py` (Employee model)
- [ ] Update DB schema for existing MySQL table `employees` (add boolean column)
- [x] Add email sender utility file (e.g. `backend/mailer.py`) that picks SMTP config from env vars.
- [ ] Update `backend/routers/employees.py`

  - [ ] In `POST /employees/add`: generate random temp password, bcrypt-hash, set `must_change_password=True`
  - [ ] Enforce city security: require `hr_city` and validate `data['city'] == hr_city`
  - [ ] Send temp password email (plain once) using SMTP creds selected by `hr_city`
  - [ ] In `PUT /employees/{id}/change-password`: set `must_change_password=False` after success
- [x] Update `backend/routers/auth.py` `POST /auth/login` to return `must_change_password` in response.


## Frontend (Streamlit)
- [x] Create dedicated forced page: `frontend/pages/employee/first_login_change_password.py`
  - [x] UI: current password + new + confirm
  - [x] On success: logout (clear session) + rerun back to login
- [x] Update `frontend/app.py` routing:
  - [x] If logged in + `must_change_password=True` and role is Employee → show dedicated page only.
- [x] Update `frontend/login.py`:
  - [x] Store `must_change_password` from backend response into session_state.
- [x] Update `frontend/pages/hr/employees.py`:
  - [x] Include `hr_city: st.session_state.city` in payload passed to `add_employee`.
- [x] Remove hardcoded `st.info("**Password123!**")` from `frontend/login.py`.

## Testing
- [ ] Create HR users and ensure each adds employees only in their city
- [ ] Add employee: verify random password emailed
- [ ] Employee first login: must be redirected to forced change page
- [ ] After change: employee forced to login again, then can access Accueil


