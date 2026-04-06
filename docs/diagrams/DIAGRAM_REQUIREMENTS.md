# 1847 Ventures App — Diagram Requirements

> **Single entry-point document** for all UML and system-design diagram requirements.
> Use this document to plan, draw, and review every diagram artifact for the project.

---

## Table of Contents

1. [Project Overview & Stakeholders](#1-project-overview--stakeholders)
2. [Feature → Diagram Mapping](#2-feature--diagram-mapping)
3. [Use Case Diagram](#3-use-case-diagram)
4. [Activity Diagram](#4-activity-diagram)
5. [Sequence Diagram](#5-sequence-diagram)
6. [Entity-Relationship (ER) Diagram](#6-entity-relationship-er-diagram)
7. [Class Diagram](#7-class-diagram)
8. [Data Flow Diagram (DFD)](#8-data-flow-diagram-dfd)
9. [Reviewer Checklist](#9-reviewer-checklist)

---

## 1. Project Overview & Stakeholders

**1847 Ventures** is a cocoa-farm investor-monitoring web application built with Django and Django REST Framework. It connects investors with cocoa farmers, allows field agents to record on-the-ground activities, and surfaces consolidated performance data through a Power BI dashboard.

### Actors / Roles

| Actor | System Role | Key Responsibilities |
|---|---|---|
| **Investor** | Read-only stakeholder | Views farm performance, harvests, investments, Power BI reports |
| **Farmer** | Primary data subject | Manages their own farm and activity records |
| **Field Agent** | Data collector | Registers farmers/farms, logs activities, submits reports |
| **Local Administration** | Regional overseer | Approves farmer registrations, views regional aggregates |
| **System Admin** | Super-user | Full CRUD on all entities, manages user approvals and announcements |

### System Platform

- **Backend:** Django 5 + Django REST Framework  
- **Database:** SQLite (development) → PostgreSQL (production target)  
- **Frontend:** Django templates (server-rendered)  
- **Reporting:** Power BI embedded dashboard (data pushed via REST API or scheduled export)  
- **Auth:** Custom user model (`Farmer` extends `AbstractUser`); role stored in `UserProfile.role`

---

## 2. Feature → Diagram Mapping

| Feature / Module | Use Case | Activity | Sequence | ER | Class | DFD |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| User registration & approval | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Login / authentication | ✓ | ✓ | ✓ | | ✓ | ✓ |
| Farm management (CRUD) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Crop & harvest recording | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Farm activity logging | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Investment tracking | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Messaging (farmer ↔ agent) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Announcements | ✓ | ✓ | | ✓ | ✓ | |
| Power BI reporting | ✓ | ✓ | ✓ | | | ✓ |
| Admin dashboard | ✓ | ✓ | ✓ | | ✓ | |

---

## 3. Use Case Diagram

### Purpose
Show every type of user (actor) and the actions (use cases) they can perform within the system boundary, including include/extend relationships between related use cases.

### System Boundary
The single boundary is the **1847 Ventures Web Application** (backend API + browser UI + Power BI integration).

### Required Actors
- Investor
- Farmer
- Field Agent
- Local Administration
- System Admin
- *(External system)* Power BI Service

### Required Use Cases per Actor

**Investor**
- UC-01 Log In
- UC-02 View Farm Performance Dashboard (Power BI)
- UC-03 View Investment Portfolio
- UC-04 View Harvest History
- UC-05 Send Message to Field Agent

**Farmer**
- UC-01 Log In
- UC-06 View Own Farm Details
- UC-07 View Own Activity Log
- UC-08 Receive Announcement
- UC-09 Send/Receive Message

**Field Agent**
- UC-01 Log In
- UC-10 Register New Farmer *(includes UC-11)*
- UC-11 Create Farmer Profile
- UC-12 Register Farm for Farmer
- UC-13 Log Farm Activity (Planting/Pruning/Spraying/Harvesting)
- UC-14 Record Harvest
- UC-15 Send Announcement
- UC-09 Send/Receive Message

**Local Administration**
- UC-01 Log In
- UC-16 Approve / Reject Farmer Registration
- UC-17 View Regional Farm Summary
- UC-08 Receive Announcement

**System Admin**
- UC-01 Log In
- UC-18 Manage All Users (CRUD)
- UC-19 Approve / Reject Any User
- UC-20 Manage Farms (CRUD)
- UC-21 Manage Investments (CRUD)
- UC-22 Create/Edit Announcement
- UC-23 View Audit/System Logs

**Power BI Service (external)**
- UC-24 Pull Aggregated Data (API call / scheduled export)

### Required Relationships / Notations
- `«include»` UC-10 → UC-11 (registering a farmer always creates a profile)
- `«extend»` UC-13 → UC-16 (activity log may trigger an approval notification)
- Generalisation: System Admin generalises Local Administration (inherits all admin use cases)
- Draw using standard UML oval notation inside a rectangle for the system boundary

### Inputs Needed from Stakeholders
- Confirm whether Local Administration can also approve investments (or only farmers)
- Confirm whether Investors can message Farmers directly or only via Field Agents

### Outputs / Acceptance Criteria
- [ ] All five human actors and the Power BI external system are visible
- [ ] Every actor has at least two connected use cases
- [ ] At least two `«include»` and one `«extend»` relationships are labelled
- [ ] System boundary rectangle is clearly drawn and labelled "1847 Ventures Web App"

---

## 4. Activity Diagram

### Purpose
Model the step-by-step workflow for key business processes including decision points, parallel activities, and exception paths.

### Required Activity Flows

#### AF-01 — User Registration & Approval
```
[Start]
  → User fills registration form (choose role)
  → System validates input
    ─ [Invalid] → Show validation errors → loop back
    ─ [Valid] → Create Farmer + UserProfile (is_approved = False)
  → System notifies Admin/Local Admin of pending approval
  → Admin reviews request
    ─ [Rejected] → Notify user → [End]
    ─ [Approved] → Set is_approved = True → Notify user
  → User can now log in
[End]
```

#### AF-02 — Login & Role-Based Redirect
```
[Start]
  → User submits credentials
  → System authenticates
    ─ [Fail] → Show error → loop back
    ─ [Success] → Load UserProfile
  → Check role
    ─ farmer → Farmer Dashboard
    ─ investor → Investor/Partner Dashboard
    ─ field_agent → Agent Dashboard
    ─ admin → Admin Dashboard
[End]
```

#### AF-03 — Farm Activity Logging (Field Agent)
```
[Start]
  → Field Agent selects Farmer
  → Field Agent selects Farm
  → Field Agent chooses Activity Type (Planting/Pruning/Spraying/Harvesting)
  → Enters date, inputs used, quantity, notes
  → System validates
    ─ [Invalid] → Show errors → loop back
    ─ [Valid] → Save FarmActivity record
  → System checks if activity is Harvesting
    ─ [Yes] → Prompt to create Harvest record (Harvest weight, quality grade)
    ─ [No] → Skip
  → Activity saved; dashboard updated
[End]
```

#### AF-04 — Investor Views Performance (Power BI)
```
[Start]
  → Investor logs in
  → System loads Partner Dashboard
  → Dashboard requests Power BI embed token
    ─ [Token error] → Show fallback data table
    ─ [Token OK] → Render embedded Power BI report
  → Investor filters by farm / date range
  → Investor exports or prints report (optional)
[End]
```

#### AF-05 — Messaging between Roles
```
[Start]
  → Sender composes message (selects receiver, types content)
  → System validates (non-empty content, valid receiver)
  → System saves Message record
  → Receiver notification generated
  → Receiver opens inbox → marks message as read (is_read = True)
[End]
```

### Required Notations
- UML swimlane (partition) per actor involved in each flow
- Filled circle for start; bullseye for end
- Diamond for decision nodes; thick bar for forks/joins (parallel flows)
- Guard conditions in square brackets `[condition]`

### Inputs Needed from Stakeholders
- Should there be a supervisor sign-off step in AF-03 before saving?
- What happens when a Field Agent is offline — is there a draft/sync queue?

### Outputs / Acceptance Criteria
- [ ] All five flows (AF-01 to AF-05) are diagrammed
- [ ] Each flow has at least one decision node with labelled guards
- [ ] Swimlanes correctly identify which actor performs each action
- [ ] Start and end nodes are present and correctly styled

---

## 5. Sequence Diagram

### Purpose
Show the time-ordered message exchanges between participants (browser UI, Django views, Django REST API, database, and Power BI) for each key interaction.

### Required Sequence Scenarios

#### SD-01 — Login
Participants: Browser, LoginView (Django), Database, UserProfile  
Messages:
1. Browser → LoginView: `POST /login/ {username, password}`
2. LoginView → Database: `authenticate(username, password)`
3. Database → LoginView: Farmer object | `None`
4. LoginView → Database: `UserProfile.objects.get(user=farmer)`
5. LoginView → Browser: `302 Redirect → role_dashboard`  
Alternative: authentication failure → `200 Login page with error message`

#### SD-02 — Field Agent Logs a Farm Activity
Participants: Browser (Agent), FarmActivityViewSet (DRF), Database  
Messages:
1. Browser → FarmActivityViewSet: `POST /api/activities/ {farmer, activity_type, date, …}`
2. FarmActivityViewSet → Database: `check IsAuthenticated + approved_user_required`
3. FarmActivityViewSet → Database: `FarmActivity.objects.create(…)`
4. Database → FarmActivityViewSet: saved FarmActivity
5. FarmActivityViewSet → Browser: `201 Created {id, activity_type, …}`  
Alternative: unapproved user → `403 Forbidden`

#### SD-03 — Investor Views Power BI Dashboard
Participants: Browser (Investor), PartnerDashboardView, Power BI REST API  
Messages:
1. Browser → PartnerDashboardView: `GET /partner-dashboard/`
2. PartnerDashboardView → Power BI REST API: `POST /generateToken`
3. Power BI REST API → PartnerDashboardView: `embed token`
4. PartnerDashboardView → Browser: `200 HTML with embed token injected`
5. Browser → Power BI CDN: `load report iframe`  
Alternative: Power BI token failure → render fallback static table

#### SD-04 — Admin Approves a Farmer
Participants: Browser (Admin), AdminView, Database, Notification Service  
Messages:
1. Browser → AdminView: `POST /approve-user/{id}/`
2. AdminView → Database: `UserProfile.objects.filter(user_id=id).update(is_approved=True)`
3. Database → AdminView: success
4. AdminView → Notification Service: `send approval email/message`
5. AdminView → Browser: `302 Redirect → admin dashboard`

#### SD-05 — Farmer Sends Message to Field Agent
Participants: Browser (Farmer), MessageViewSet, Database  
Messages:
1. Browser → MessageViewSet: `POST /api/messages/ {receiver_id, content}`
2. MessageViewSet → Database: `Message.objects.create(sender=request.user, …)`
3. Database → MessageViewSet: saved Message
4. MessageViewSet → Browser: `201 Created`

### Required Notations
- Lifelines for each participant as vertical dashed lines
- Synchronous messages as solid arrows with filled arrowhead
- Return messages as dashed arrows
- Activation boxes on lifelines during processing
- Alt/Opt combined fragments for alternative flows
- Self-calls (loops) where validation happens inside the same object

### Inputs Needed from Stakeholders
- Is there an email/SMS notification service integrated, or just in-app?
- What is the exact Power BI API endpoint and auth method (Service Principal / AAD token)?

### Outputs / Acceptance Criteria
- [ ] All five scenarios (SD-01 to SD-05) are diagrammed
- [ ] Each diagram has at least three participants
- [ ] Alternative flows are shown using `alt` combined fragment boxes
- [ ] Return messages are labelled with HTTP status or return value
- [ ] Power BI integration is visible in SD-03

---

## 6. Entity-Relationship (ER) Diagram

### Purpose
Model the persistent data entities, their attributes, primary keys, foreign keys, and cardinality relationships for the complete database schema.

### Required Entities & Attributes

| Entity | PK | Key Attributes |
|---|---|---|
| **Farmer** (User) | `id` (int) | `username`, `email`, `phone_number`, `farmer_id` (UUID), `password`, `registration_date` |
| **UserProfile** | `id` (int) | `user_id` (FK→Farmer), `role` (enum), `is_approved` (bool) |
| **Farm** | `id` (int) | `name`, `owner_id` (FK→Farmer), `location`, `size_in_hectares`, `created_at` |
| **Crop** | `id` (int) | `farm_id` (FK→Farm), `name`, `planting_date`, `harvest_date`, `expected_yield_kg` |
| **Harvest** | `id` (int) | `farm_id` (FK→Farm), `date_of_harvest`, `tons_produced`, `quality_grade` |
| **Investment** | `id` (int) | `investor_id` (FK→Farmer), `farm_id` (FK→Farm), `amount`, `expected_return_percentage`, `invested_at` |
| **FarmActivity** | `id` (int) | `farmer_id` (FK→Farmer), `activity_type` (enum), `date`, `inputs_used`, `quantity`, `notes` |
| **Announcement** | `id` (int) | `title`, `message`, `created_by_id` (FK→Farmer), `created_at`, `is_active` |
| **Message** | `id` (int) | `sender_id` (FK→Farmer), `receiver_id` (FK→Farmer), `content`, `created_at`, `is_read` |

### Required Relationships & Cardinalities

| Relationship | Cardinality | Notes |
|---|---|---|
| Farmer **has** UserProfile | 1 : 1 | Auto-created via Django signal on Farmer save |
| Farmer **owns** Farm | 1 : N | `Farm.owner_id` → `Farmer.id` |
| Farm **grows** Crop | 1 : N | `Crop.farm_id` → `Farm.id` |
| Farm **produces** Harvest | 1 : N | `Harvest.farm_id` → `Farm.id` |
| Farmer (investor) **makes** Investment | 1 : N | `Investment.investor_id` → `Farmer.id` |
| Farm **receives** Investment | 1 : N | `Investment.farm_id` → `Farm.id` |
| Farmer **logs** FarmActivity | 1 : N | `FarmActivity.farmer_id` → `Farmer.id` |
| Farmer **creates** Announcement | 1 : N | `Announcement.created_by_id` → `Farmer.id` |
| Farmer **sends/receives** Message | M : N (via Message table) | Two FK columns `sender_id` and `receiver_id` both → `Farmer.id` |

### Required Notations
- Crow's foot notation (or Chen notation — pick one and be consistent)
- All PKs underlined; FKs marked with dashed underline or FK label
- Enumerations (role, activity_type) noted as attribute domain constraint
- Weak entities (if any) shown with double rectangle

### Inputs Needed from Stakeholders
- Will Crops and Harvests always be linked to the same Farm, or can a Harvest span multiple farms?
- Is there a separate `Region` or `District` entity for Local Administration, or is location a free-text string?
- Will the Investment entity eventually include a status (active/closed/pending)?

### Outputs / Acceptance Criteria
- [ ] All nine entities are present with complete attribute lists
- [ ] All nine relationships are drawn with correct cardinality notation
- [ ] PKs and FKs are clearly labelled
- [ ] The `Message` entity correctly shows two separate FK lines to `Farmer`
- [ ] The `UserProfile.role` enumeration values are documented (farmer, investor, field_agent, admin)

---

## 7. Class Diagram

### Purpose
Show the object-oriented design of the Django domain model: classes, attributes (with types), methods, access modifiers, and relationships (inheritance, association, composition).

### Required Classes

#### `Farmer` (extends `AbstractUser`)
```
+ phone_number: CharField
+ farmer_id: UUIDField
+ registration_date: DateTimeField
---
+ __str__() : str
```

#### `UserProfile`
```
+ user: OneToOneField(Farmer)
+ role: CharField  [farmer | investor | field_agent | admin]
+ is_approved: BooleanField
---
+ __str__() : str
```

#### `Farm`
```
+ name: CharField
+ owner: ForeignKey(Farmer)
+ location: CharField
+ size_in_hectares: FloatField
+ created_at: DateTimeField
---
+ __str__() : str
```

#### `Crop`
```
+ farm: ForeignKey(Farm)
+ name: CharField
+ planting_date: DateField
+ harvest_date: DateField  [nullable]
+ expected_yield_kg: DecimalField
---
+ __str__() : str
```

#### `Harvest`
```
+ farm: ForeignKey(Farm)
+ date_of_harvest: DateField
+ tons_produced: FloatField
+ quality_grade: CharField
---
+ __str__() : str
```

#### `Investment`
```
+ investor: ForeignKey(Farmer)
+ farm: ForeignKey(Farm)
+ amount: DecimalField
+ expected_return_percentage: DecimalField
+ invested_at: DateTimeField
```

#### `FarmActivity`
```
+ farmer: ForeignKey(Farmer)
+ activity_type: CharField  [planting | pruning | spraying | harvesting]
+ date: DateField
+ inputs_used: TextField
+ quantity: FloatField
+ notes: TextField
---
+ __str__() : str
```

#### `Announcement`
```
+ title: CharField
+ message: TextField
+ created_by: ForeignKey(Farmer)
+ created_at: DateTimeField
+ is_active: BooleanField
---
+ __str__() : str
```

#### `Message`
```
+ sender: ForeignKey(Farmer)
+ receiver: ForeignKey(Farmer)
+ content: TextField
+ created_at: DateTimeField
+ is_read: BooleanField
---
+ __str__() : str
```

#### Serializers (DRF — show as `<<interface>>` or `<<serializer>>`)
- `FarmerSerializer`, `FarmSerializer`, `HarvestSerializer`, `InvestmentSerializer`, `FarmActivitySerializer`, `AnnouncementSerializer`, `MessageSerializer`, `FarmerRegistrationSerializer`

#### ViewSets / Views
- `FarmerViewSet`, `FarmViewSet`, `HarvestViewSet`, `InvestmentViewSet`, `FarmActivityViewSet`, `AnnouncementViewSet`, `MessageViewSet`
- `CustomLoginView`, `role_redirect_view`, `farmer_dashboard`, `agent_dashboard`, `partner_dashboard`

### Required Relationships
- `Farmer` **inherits** `AbstractUser` (generalisation arrow)
- `UserProfile` **has-a** `Farmer` (composition, 1:1)
- `Farm` **has-a** `Farmer` as owner (association)
- `Crop` **belongs-to** `Farm` (composition)
- `Harvest` **belongs-to** `Farm` (composition)
- `FarmActivity` **belongs-to** `Farmer` (association)
- `Investment` **associates** `Farmer` ↔ `Farm`
- `Message` **associates** `Farmer` (sender) ↔ `Farmer` (receiver)
- Each ViewSet **uses** its corresponding Model and Serializer (dependency arrows)

### Required Notations
- UML class box with three compartments (name | attributes | methods)
- Access modifiers: `+` public, `-` private, `#` protected
- Generalisation (inheritance): hollow triangle arrowhead
- Composition: filled diamond at the whole end
- Association: plain arrow
- Multiplicity on association ends (e.g., `1`, `0..*`, `1..*`)

### Inputs Needed from Stakeholders
- Will `FarmActivity` ever be associated with a `Farm` directly (in addition to a `Farmer`)?
- Are there any planned mixins or abstract base classes beyond `AbstractUser`?

### Outputs / Acceptance Criteria
- [ ] All nine domain model classes are present
- [ ] `Farmer → AbstractUser` generalisation is visible
- [ ] Serializer and ViewSet classes are shown (even as simplified boxes)
- [ ] Multiplicity is labelled on every association
- [ ] Compositions are distinguished from plain associations

---

## 8. Data Flow Diagram (DFD)

### Purpose
Show how data moves through the system: external entities that produce or consume data, processes that transform data, and data stores that persist data. Identifies sensitive data flows for security review.

### Level 0 — Context Diagram

**External Entities:**
- Farmer (data input: farm, activity, harvest data)
- Field Agent (data input: registration, activity reports)
- Investor (data consumer: dashboards, reports)
- Local Administration (data consumer/approver)
- System Admin (full bidirectional)
- Power BI Service (data consumer: aggregated analytics)

**Central Process:** `1847 Ventures Web Application`

**Flows into system:**
- Farmer registration + credentials
- Farm details, crop data, harvest records
- Activity logs, inputs used
- Messages
- Investment requests

**Flows out of system:**
- Authenticated session / access token
- Farm performance reports
- Approval notifications
- Aggregated dataset (to Power BI)
- Messages / announcements

---

### Level 1 — Decomposition

| Process ID | Process Name | Inputs | Outputs | Data Store(s) |
|---|---|---|---|---|
| P1 | User Authentication & Authorisation | Credentials (username, password) | Session token, role redirect | DS1: Farmer, DS2: UserProfile |
| P2 | Farmer & Farm Registration | Farmer profile data, Farm details | Confirmation, pending approval | DS1: Farmer, DS2: UserProfile, DS3: Farm |
| P3 | Approval Management | Approval decision | Updated is_approved, notification | DS2: UserProfile |
| P4 | Farm Activity Logging | Activity type, date, inputs, quantity | Saved activity record | DS4: FarmActivity |
| P5 | Harvest Recording | Harvest date, tons, quality grade | Saved harvest record | DS5: Harvest |
| P6 | Investment Management | Investment amount, farm, investor | Saved investment record, portfolio | DS6: Investment |
| P7 | Reporting & Analytics | Aggregated data from DS3–DS6 | Power BI dataset push, dashboard embed | External: Power BI Service |
| P8 | Messaging | Sender, receiver, content | Saved message, notification | DS7: Message |
| P9 | Announcement Management | Title, message, target audience | Published announcement | DS8: Announcement |

### Data Stores

| ID | Data Store | Sensitive Data? |
|---|---|---|
| DS1 | Farmer (User table) | ✓ PII (name, email, phone) |
| DS2 | UserProfile | Role, approval status |
| DS3 | Farm | Location data |
| DS4 | FarmActivity | Operational data |
| DS5 | Harvest | Financial-adjacent |
| DS6 | Investment | ✓ Financial data (amount, return %) |
| DS7 | Message | ✓ Private communications |
| DS8 | Announcement | Public/broadcast |

### Security & Privacy Annotations
- DS1, DS6, DS7 require encryption at rest and access-role filtering
- All flows between Browser and Backend cross a trust boundary → HTTPS required
- Power BI data export must be aggregated/anonymised before leaving the system boundary (no PII in Power BI dataset)
- Approval flows (P3) must be logged for audit purposes

### Required Notations
- Gane & Sarson or Yourdon-DeMarco notation (pick one, be consistent)
- Rectangles for external entities
- Rounded rectangles (or circles) for processes
- Open-ended rectangles for data stores
- Labelled arrows showing data flow direction
- Trust boundary drawn as dashed line around the web application

### Inputs Needed from Stakeholders
- Is there a batch/scheduled job that pushes data to Power BI, or is it triggered on-demand?
- What specific fields are pushed to Power BI (confirm aggregation level to avoid PII leakage)?
- Is there a notification service (email, SMS, in-app) that is a separate external system?

### Outputs / Acceptance Criteria
- [ ] Level 0 context diagram shows all six external entities and the central process
- [ ] Level 1 diagram contains all nine processes (P1–P9)
- [ ] All eight data stores (DS1–DS8) are present in Level 1
- [ ] Every data store is connected to at least one process
- [ ] Power BI Service appears as both an external entity and a consumer in the reporting flow
- [ ] Trust boundary is drawn and labelled
- [ ] Sensitive data stores are annotated

---

## 9. Reviewer Checklist

Use this checklist when reviewing any submitted diagram artifact.

### General (all diagrams)
- [ ] Diagram title and version date are present
- [ ] Diagram type and notation standard are identified
- [ ] Legend/key is provided if custom symbols are used
- [ ] All actors/entities mentioned in this document are represented
- [ ] Naming is consistent with model field names in `Farmers/models.py`
- [ ] No application code has been modified

### Use Case Diagram
- [ ] All five human actors and Power BI external system are shown
- [ ] System boundary rectangle is present and labelled
- [ ] `«include»` and `«extend»` relationships are labelled
- [ ] Every use case has a verb-noun name (e.g., "Log In", "Record Harvest")

### Activity Diagram
- [ ] All five flows (AF-01 to AF-05) are present
- [ ] Swimlanes identify actors for each action
- [ ] Decision nodes have labelled guard conditions
- [ ] Start (filled circle) and end (bullseye) nodes are present

### Sequence Diagram
- [ ] All five scenarios (SD-01 to SD-05) are present
- [ ] HTTP methods and paths are labelled on messages
- [ ] `alt` fragments cover alternative/error flows
- [ ] Power BI API interaction is modelled in SD-03

### ER Diagram
- [ ] All nine entities are present with attribute lists
- [ ] PK/FK labels are present on every relationship
- [ ] Cardinality notation is consistent (all crow's foot or all Chen)
- [ ] `Message` entity has two FK arrows to `Farmer`

### Class Diagram
- [ ] All nine domain classes are present
- [ ] `Farmer → AbstractUser` inheritance is shown
- [ ] Multiplicity is labelled on every association/composition
- [ ] ViewSet and Serializer classes are included

### Data Flow Diagram
- [ ] Level 0 and Level 1 diagrams are both present
- [ ] All nine Level 1 processes are labelled (P1–P9)
- [ ] Trust boundary is visible
- [ ] Sensitive data stores are annotated

---

*Last updated: 2026-04-06 | Maintained by: System Architect / Technical Lead*
