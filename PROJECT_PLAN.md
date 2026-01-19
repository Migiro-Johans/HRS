# Payroll and Leave Management System - Implementation Plan

## Project Overview
**Organization:** House of Procurement Limited
**Target Users:** ~50 Employees
**Tech Stack:** Django + React + PostgreSQL + Azure

---

## Phase 1: Backend Foundation (Current)
### 1.1 Project Setup
- [x] Create project structure
- [ ] Initialize Django project
- [ ] Configure PostgreSQL database
- [ ] Set up environment configuration

### 1.2 Core Models
- [ ] Employee model (linked to Microsoft 365)
- [ ] Department model
- [ ] Payroll models (PayrollPeriod, PayrollEntry)
- [ ] Leave models (LeaveType, LeaveBalance, LeaveRequest)
- [ ] Audit log model

### 1.3 Kenyan Payroll Rules (2024/2025)
**Statutory Deductions:**
| Deduction | Rate/Amount |
|-----------|-------------|
| PAYE | Progressive (10%-35%) |
| Personal Relief | KES 2,400/month |
| Insurance Relief | 15% of premiums (max KES 5,000/month) |
| NSSF (Tier I) | 6% up to KES 7,000 |
| NSSF (Tier II) | 6% of KES 7,001 - 36,000 |
| SHA (Social Health Authority) | 2.75% of gross |
| Housing Levy | 1.5% of gross |

**PAYE Tax Bands (Monthly):**
| Annual Income (KES) | Monthly (KES) | Rate |
|---------------------|---------------|------|
| 0 - 288,000 | 0 - 24,000 | 10% |
| 288,001 - 388,000 | 24,001 - 32,333 | 25% |
| 388,001 - 6,000,000 | 32,334 - 500,000 | 30% |
| 6,000,001 - 9,600,000 | 500,001 - 800,000 | 32.5% |
| Above 9,600,000 | Above 800,000 | 35% |

---

## Phase 2: Authentication
- [ ] Microsoft Entra ID (Azure AD) integration
- [ ] SSO with company Microsoft 365 accounts
- [ ] Role-based access control (Employee, HOD, HR, Accounts, Management)
- [ ] Department-based permissions

---

## Phase 3: Payroll Engine
- [ ] Gross pay calculation (basic + allowances + benefits)
- [ ] PAYE computation with reliefs
- [ ] NSSF calculation (Tier I & II)
- [ ] SHA calculation
- [ ] Housing Levy calculation
- [ ] Custom deductions (loans, advances, SACCO)
- [ ] Net pay calculation
- [ ] Approval workflow (Accounts → HR → Management)

---

## Phase 4: Leave Management
- [ ] Leave types (Annual, Sick, Maternity, Paternity, Compassionate)
- [ ] Leave balance tracking
- [ ] Leave application workflow
- [ ] Approval chain (Employee → HOD → HR)
- [ ] Leave calendar/schedule view
- [ ] Accrual rules

---

## Phase 5: React Frontend
- [ ] Project setup with TypeScript
- [ ] Authentication flow with MSAL
- [ ] Role-based dashboards
- [ ] Employee self-service portal
- [ ] Payroll management interface
- [ ] Leave management interface
- [ ] Admin panels

---

## Phase 6: Document Generation
- [ ] Payslip PDF generation (WeasyPrint)
- [ ] P9A/G9 tax certificate generation
- [ ] Digital signatures/stamps
- [ ] Azure Blob Storage integration
- [ ] Document versioning

---

## Phase 7: Policies & SOPs
- [ ] Document upload and management
- [ ] Version control
- [ ] Department-based access control
- [ ] Acknowledgement tracking
- [ ] Dashboard integration

---

## Phase 8: Testing
- [ ] Unit tests for payroll calculations
- [ ] API integration tests
- [ ] Frontend component tests
- [ ] End-to-end tests
- [ ] Security testing

---

## Phase 9: Deployment
- [ ] Azure App Service setup
- [ ] Azure Database for PostgreSQL
- [ ] Azure Blob Storage
- [ ] CI/CD pipeline
- [ ] SSL/TLS configuration
- [ ] Monitoring and logging

---

## Database Schema Overview

```
┌─────────────────┐     ┌─────────────────┐
│   Department    │────<│    Employee     │
└─────────────────┘     └─────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  PayrollEntry   │   │  LeaveRequest   │   │   LeaveBalance  │
└─────────────────┘   └─────────────────┘   └─────────────────┘
        │
        ▼
┌─────────────────┐
│  PayrollPeriod  │
└─────────────────┘
```

---

## API Endpoints (Planned)

### Authentication
- `POST /api/auth/login/` - Microsoft SSO callback
- `POST /api/auth/logout/`
- `GET /api/auth/me/` - Current user info

### Employees
- `GET /api/employees/` - List employees (HR/Admin)
- `GET /api/employees/{id}/` - Employee details
- `PUT /api/employees/{id}/` - Update employee

### Payroll
- `GET /api/payroll/periods/` - List payroll periods
- `POST /api/payroll/periods/` - Create payroll period
- `GET /api/payroll/periods/{id}/entries/` - Payroll entries
- `POST /api/payroll/compute/` - Run payroll computation
- `POST /api/payroll/approve/` - Approve payroll
- `GET /api/payroll/payslips/` - Employee payslips
- `GET /api/payroll/p9a/{year}/` - Generate P9A

### Leave
- `GET /api/leave/types/` - Leave types
- `GET /api/leave/balance/` - Current user balance
- `POST /api/leave/requests/` - Apply for leave
- `GET /api/leave/requests/` - List requests
- `PUT /api/leave/requests/{id}/approve/` - Approve request

### Policies
- `GET /api/policies/` - List accessible policies
- `POST /api/policies/` - Upload policy (Admin)
- `POST /api/policies/{id}/acknowledge/` - Acknowledge policy
