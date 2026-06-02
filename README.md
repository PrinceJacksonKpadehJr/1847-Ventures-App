# 1847 Ventures App

A cocoa-farm investor-monitoring web application built with **Django** and **Django REST Framework**. It connects investors with cocoa farmers, allows field agents to record on-the-ground activities, and surfaces consolidated performance data through a **Power BI** dashboard.

## Key Roles

| Role | Description |
|---|---|
| **Investor** | Views farm performance, harvests, and investment portfolio via Power BI reports |
| **Farmer** | Manages their own farm profile and activity records |
| **Field Agent** | Registers farmers/farms, logs farm activities, submits reports |
| **Local Administration** | Approves farmer registrations and views regional aggregates |
| **System Admin** | Full management of all users, farms, and system settings |

## Tech Stack

- **Backend:** Python / Django 5 + Django REST Framework
- **Database:** SQLite (development) → PostgreSQL (production target)
- **Frontend:** Django server-rendered templates
- **Reporting:** Power BI embedded dashboard

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run the development server
python manage.py runserver
```

## Documentation

| Document | Description |
|---|---|
| [Diagram Requirements](docs/diagrams/DIAGRAM_REQUIREMENTS.md) | Complete requirements for all UML and system-design diagrams: Use Case, Activity, Sequence, ER, Class, and Data Flow Diagrams |
