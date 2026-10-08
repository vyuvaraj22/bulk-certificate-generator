# Bulk Certificate Generator

A complete, polished full-stack application to generate professional bulk PDF certificates. 
This project was built to demonstrate a clean architecture, reliable background processing, 
excellent UI/UX, and robust API design.

## Project Overview

The Bulk Certificate Generator allows event organizers to create a job, upload a list of recipients 
(manually or via CSV), and generate professional PDF certificates in the background. The application 
handles errors gracefully—if one certificate fails, the rest of the batch continues.

## Features

**Core Requirements:**
- Accept bulk certificate generation requests.
- Validate recipient data.
- Create generation jobs.
- Generate professional landscape A4 PDF certificates using a predefined template.
- Process recipients independently.
- Track job progress in real-time.
- View successful and failed generations.
- Download individual certificates.
- Modern dashboard UI built with React.

**Optional Features Implemented:**
- Drag-and-drop CSV Import with validation preview.
- CSV Template Download.
- Duplicate certificate ID detection.
- Retry Failed Certificates.
- ZIP Download of all successful certificates.
- Auto-generation of Certificate IDs.
- Job Statistics on the dashboard.
- Elegant Toast Notifications.

## Architecture

The system uses a clean separation of concerns:

```text
Frontend (React + Vite)
   ↓
REST API (FastAPI)
   ↓
Service Layer (Business Logic)
   ↓
Background Processor (ThreadPoolExecutor)
   ↓
Certificate Generator (ReportLab)
   ↓
Database (SQLite) + File Storage (Local FS)
```

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, Pydantic, ReportLab.
- **Frontend:** React, Vite, React Router, Axios, Lucide Icons, Vanilla CSS (Design System).

## Setup & Running

### Backend

```bash
cd backend
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```
The backend will run on `http://127.0.0.1:8000`
Swagger UI available at `http://127.0.0.1:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```
The frontend will run on `http://localhost:5173`

### Run Tests

```bash
cd backend
pytest
```

## API Usage Example

Create a job:

```http
POST /api/jobs
Content-Type: application/json

{
  "event_name": "Python Backend Workshop",
  "certificate_title": "Certificate of Completion",
  "organization": "ABC Organization",
  "issue_date": "2026-10-08",
  "description": "Outstanding performance in backend engineering",
  "recipients": [
    {
      "name": "John Doe",
      "email": "john@example.com",
      "certificate_id": "CERT-001"
    }
  ]
}
```

Response:

```json
{
  "job_id": "84c8a5a4-56b9...",
  "status": "QUEUED",
  "total": 1,
  "completed": 0,
  "successful": 0,
  "failed": 0,
  "message": "Job accepted. Certificate generation started in the background."
}
```

Get Job Status:

```http
GET /api/jobs/84c8a5a4-56b9...
```

## Design Decisions

- **Why FastAPI:** It provides fast REST API development, Pydantic validation, automatic OpenAPI documentation, and native async/background processing support.
- **Why Background Processing:** PDF generation is CPU intensive. For large batches (e.g., 1000 recipients), the API would timeout if processed synchronously. Background tasks return a job ID immediately.
- **Why Independent Certificate Processing:** A single invalid character or missing file for one recipient should not stop the remaining 999 certificates from being generated. Each is processed in a try/except block.
- **Why Relational Database & SQLite:** Jobs and certificates have a strict 1-to-many relationship with state transitions. SQLite keeps the assignment simple to set up locally, but SQLAlchemy allows it to be swapped for PostgreSQL trivially.
- **Why ThreadPoolExecutor:** Instead of Celery/Redis, a ThreadPoolExecutor keeps the system self-contained for the interview assignment while still proving concurrent background execution.

## Future Improvements

- **Redis/Celery:** For distributed worker queues when scaling horizontally.
- **Object Storage:** Store PDFs in AWS S3 instead of local disk.
- **Authentication/Authorization:** Add JWT-based logins to secure the admin panel.
- **Multiple Templates:** Allow the user to select from different template designs.
- **Email Delivery:** Automatically email the generated PDF directly to the recipient's email address.
