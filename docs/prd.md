# LinkDem: Prescriptive Event Task Management for Small Teams

## TL;DR

LinkDem is a prescriptive task and event management platform designed for small teams (1–10 members) handling compact, high-dependency events with 10–20 tasks. It delivers workflow-driven task assignment, robust RBAC controls with Global and Event-only access levels, and in-depth visibility into task status via Kanban and workflow-DAG interfaces. The platform's core audience includes event managers, admin users, and individual team members seeking frictionless event execution through guided, compliant, and auditable task flows.

---

## Goals

### Business Goals

- Achieve 90% user task completion rate per event within 45 days post-launch.
- Reduce event management overhead for teams by at least 30% compared to manual or spreadsheet systems.
- Ensure 100% RBAC compliance and workflow conformance for all events.
- Demonstrate <2% error/incidence rates in task transitions and automations in the first quarter.

### User Goals

- Provide users with precise visibility over all tasks assigned to them or their roles, without clutter or distraction.
- Allow admins to flexibly and securely manage workflows, users, roles, and permissions across all events.
- Guarantee that every task update is traceable via mandatory remarks to boost accountability.
- Automate downstream task creation and reduce manual intervention using workflow-driven "next-step" auto functions.

### Non-Goals

- No support for multi-organization or cross-organizational events (single-tenant scope only).
- No support for tasks/events exceeding the 20-task or 10-user scope.
- No integration with generic calendar or chat tools beyond current functional scope.

---

## User Stories

### Personas

#### 1. Admin User ("Neha")

- As an Admin, I want to set up workflows as directed acyclic graphs (DAG), so that complex event dependencies and task flows are reflected exactly as intended for Birthday and Indian Marriage events.
- As an Admin, I want to create, assign, and manage roles in an RBAC matrix (CRUD x Functions), so that access and permissions align precisely across event and Global scopes.
- As an Admin, I want to view all events, all users, and every task irrespective of assignment, so that I have full audit/control capability.
- As an Admin, I want to reassign any task at any progression stage (except Done) with a mandatory remark, so handovers are traceable and compliant.
- As an Admin, I want to trigger and verify auto task-creation when a predecessor completes per workflow rules, to minimize manual orchestration.

#### 2. Event Manager ("Ravi")

- As an Event Manager with Event-only access, I want to see only those events I am assigned to, so my dashboard remains unambiguous and secure.
- As an Event Manager, I want to visualize the Kanban board showing only tasks relevant to my role or users, and tasks before/after my responsibilities in the workflow DAG, so I can anticipate dependencies.
- As an Event Manager, I want to assign, pick up, or reassign tasks (with required remarks), so responsibilities can shift within constraints during event execution.
- As an Event Manager, I want to view the event's workflow as a static DAG, so I understand the full event logic and my tasks' context.
- As an Event Manager, I want to validate a completed task and move it forward, ensuring workflow state transitions are respected.

#### 3. Team Member ("Simran")

- As a Team Member, I want to see only tasks directly assigned to me or my role, and their immediate blockings and successors, so I stay focused.
- As a Team Member, I want the ability to pick up unassigned TODO-state tasks within my role, so I can initiate work based on availability.
- As a Team Member, I want to update the status of my task (e.g., TODO -> WIP -> VALIDATE -> DONE) provided it follows permitted transitions, with remarks explaining every update.
- As a Team Member, I want to see clear error messaging if I attempt a forbidden action (e.g., skipping states or missing remarks).

---

## Functional Requirements

### Access & Roles (Priority: Critical)

- **Access Levels:** System must support "Global" (all events/tasks visibility) and "Event-only" (restricted to assigned events).
- Each user assigned an Access Level upon creation; enforced throughout UI/API.
- **Roles & RBAC Matrix:** Admins can define roles, with permissions via a CRUD x Functions matrix (e.g., Role1 - Users CR, Events RU).
- Matrix specifies which actions are available to which roles, per access level.

### Workflow & Events (Priority: Critical)

- **Workflow DAG Definition:** Admins can create and edit event workflows as DAGs, with two sample workflows (Birthday party, Indian marriage) viewable via React-Flow.
- **Event Creation:** On event creation, admin assigns one immutable workflow to the event; tasks inherit structure and roles from the workflow.
- **Task Management:** Tasks are instantiated manually (by admin) or automatically via workflow rules; each task bound to states (TODO, WIP, BLOCKED, VALIDATE, DONE).
- **Task Assignment/Ownership:** Each task must be assigned to one user (except TODO state which may be unassigned); reassignment and assignment always require a remark.
- **Task Visibility:** Users only view tasks assigned directly to them, their role, or adjacent steps within the DAG. Admins can see all.

### Automation & Validation (Priority: High)

- **Auto Functions:** On each relevant task update (e.g., moving to DONE), system triggers auto-creation/move of downstream tasks as defined by the workflow DAG.
- **State Transitions:** Enforce state machine: `TODO -> WIP <-> BLOCKED`, `WIP <-> VALIDATE -> DONE`, no skipping or non-permitted transitions.
- **Mandatory Remarks:** Every assignment or status change must be accompanied by a non-empty remark stored in audit log.
- **Validation:** All RBAC checks, task state transitions, DAG/assignment constraints, and remarks enforced at API level.

### UI, API, DB, Testing Team Guidance (Priority: High)

- **UI:** Kanban view for tasks (per role/user visibility), workflow-DAG visualization (static for event), context-sensitive action buttons, clear indications of access level and permissible actions.
- **API:** Expose RBAC-enforced endpoints for task/event/workflow/user management, with all business rules and validation outlined above.
- **DB:** Store users, roles, RBAC matrix, events, workflows (DAG), tasks (states, assignments), remarks, audit logs; ensure referential integrity.
- **Testing:** Check enforcement of all business constraints (access, RBAC, assignment, automations, state transitions); validate with sample workflows and typical error scenarios.

---

## User Experience

### Entry Point & First-Time User Experience

- Users access LinkDem via a secure login page; upon first login, the user's assigned access level and role dictate dashboard layout.
- New users complete a brief onboarding: walkthrough of "Access Level" and "Your Tasks/Events", highlighting Kanban, workflow-DAG, and permitted actions.
- Admins receive extra onboarding on workflow and RBAC setup; links to sample workflows (Birthday, Marriage).

### Core Experience

**Step 1: User lands on dashboard.**

- Kanban view lists only permitted events/tasks (see task visibility rules).
- UI foregrounds all tasks requiring action (e.g., "My Tasks Today"; "Unassigned TODOs in My Role").

**Step 2: User picks a task; sees full context.**

- Current state, previous/next steps in the workflow DAG, roles assigned, remarks log.
- Only see actions (e.g., "Start WIP", "Assign", "Validate/Complete") allowed by RBAC and state machine.

**Step 3: On updating a task (e.g., moving TODO → WIP), user must input a non-empty remark.**

- Save is blocked if remark is missing.
- Success triggers kanban refresh; if moving to DONE, any auto-generated tasks appear in TODO.

**Step 4: Admins and Event Managers can assign/reassign tasks.**

- "Assign" opens user/rule dropdown; requires remark explaining reassignment.
- Updating task assignment triggers audit log entry.

**Step 5: Workflow-DAG viewer overlays static event flow.**

- Shows all tasks, current states (color-coded), role-responsibilities, pending downstream tasks.

**Step 6: Unauthorized actions trigger clear descriptive error to user.**

**Step 7: Audit logs accessible to Admins.**

- Shows detailed assignment and remark trails for compliance review.

### Advanced Features & Edge Cases

- Admin can manually override/force-move tasks in emergencies (logged separately).
- System prevents creation of new events or tasks exceeding 10 members or 20 tasks per event.
- Expired/unusual sessions (e.g., demotion from Global to Event) handled gracefully with in-app notifications and re-authorization prompts.

### UI/UX Highlights

- Kanban columns reflect workflow state machine; color-coded state and role badges.
- Workflow-DAG visualization displays real-time task state for current event.
- All forms enforce robust validation (disabled buttons until remarks provided, access-level-dependent fields).
- On small screens, Kanban and DAG viewer adapt responsively (no horizontal scrolling for tasks).
- Accessibility: color contrast, keyboard navigation for task flows, and clear error feedback.

---

## Narrative

Neha, an experienced Admin, has just set up a new event in LinkDem for a client's Indian marriage—an event with complex, interdependent tasks. She selects the preconfigured "Indian Marriage" workflow-DAG from LinkDem's sample gallery. Instantly, 15 tasks are generated, each step assigned to the right role. Neha configures roles in the RBAC matrix: the decorator, caterer, and photographer all get custom CRUD permissions, with Ravi, the event manager, set with Event-only access.

On event day, Ravi's dashboard shows only the tasks critical to him—plus immediate predecessors and successors in the workflow, so he can manage handoffs. He notices the decorator's task is stuck in BLOCKED. Using his permissions, he reassigns it to Simran, adding a remark on the cause, which is instantly visible in the remarks log and on Kanban. Once Simran moves her task to DONE (with required remarks), the next dependent tasks auto-populate in TODO, reducing Ravi's manual workload and ensuring nothing falls through.

Every action—state change, assignment, or permission check—is validated by the platform's rules engine. Neha monitors progress through the Admin view: Kanban states, DAG view, and audit logs. Come event close, all tasks are marked DONE, every handover is accounted for, and team members report a simple, guided, and low-cognitive-load workflow. The event is a success—reliably executed, with traceable accountability and zero missing steps.

---

## Success Metrics

| Metric                   | Definition/Measurement                                          |
| ------------------------ | --------------------------------------------------------------- |
| User Retention Rate      | % of users returning to the app weekly/monthly                  |
| Task Completion Accuracy | % of tasks fully completed per event with all transitions legal |
| RBAC Violation Incidents | # of unauthorized actions attempted or permitted (target: zero) |
| Workflow Conformance     | % of events with zero manual overrides or skipped DAG steps     |
| Mean Time to Resolution  | Avg. duration from task TODO to DONE, tracked per event         |
| System Uptime            | % uptime (target: >99.9%) during active event periods           |

### User-Centric Metrics

- Active user rate (weekly/monthly by persona and access level)
- Median number of remarks per event (monitoring accountability)
- User satisfaction (via post-event in-app survey, feedback completeness)

### Business Metrics

- Reduction in manual task handover or error reports compared to prior methods
- Number of events managed/month post-deployment
- Audit compliance rate (all state transitions and reassignments traced)

### Technical Metrics

- System uptime >99.9% during business/event hours
- API response latency: <300ms on average
- Error rate on state transitions and automated task triggers <2%
- RBAC and workflow conformance validation (automated test runs/week)

---

## Tracking Plan

- User login and session events
- Event creation and workflow assignment
- Task creation/assignment, state changes, and remarks logging
- RBAC matrix edits and permission checks
- Audit log accesses and Admin overrides
- DAG-based workflow completions and auto-function triggers

---

## Technical Considerations

### Technical Needs

- **Core Components:** APIs for users, roles, RBAC matrix, events, tasks, workflows. Data models reflecting tasks, events, workflows (DAG-based), remarks, logs.
- **UI:** Role/context-aware layouts, dynamic Kanban, static workflow-DAG via React-Flow, rich forms enforcing validation for remarks and assignments.
- **RBAC Enforcement:** All actions must be permission-checked synchronously. Client must adapt UI actions/buttons based on current RBAC + access level.
- **Workflow Engine:** Must support DAG parsing, task state propagation, auto-creation/triggers on completion or state update.

### Integration Points

No required integrations beyond initial scope. Allow for modular DB, API, and UI layers. Optionally, stub hooks for Slack/email but not implemented now.

### Data Storage & Privacy

- Persist tasks, events, users, roles, RBAC matrices, workflows, and remarks in audited, relational structure.
- All audit logs are immutable and accessible only by Admins.
- Event and user assignment data encrypted at rest; user access level and RBAC checked on every data access.
- All logins and actions must be tracked for compliance.

### Scalability & Performance

- Designed for up to 10 users and 20 tasks/event; optimize for quick UI feedback (<1s board updates).
- API to handle bursts of workflow state changes with no disruption; error handling for overrun or misconfigured workflows.

### Potential Challenges

- Enforcing strict RBAC and workflow compliance at both API and UI—ensure no leaks or over-permissive actions.
- Validating non-empty remarks on every task update/assignment across all interfaces.
- Syncing Kanban with DAG state transitions and auto-function task creation in real-time.
- Handling corner cases (e.g., admin overrides, user role changes mid-event, stuck/blocked tasks).

---

## Milestones & Sequencing

### Project Estimate

Medium: 2–4 weeks (with optimized lean startup team leveraging agile sprints and demo-driven checkpoints).

### Team Size & Composition

Small Team: 2 total people

- 1 Product + Design + QA (overlapping responsibilities)
- 1 Engineering (front-end, back-end, DB/API, workflow logic, integrations)

### Suggested Phases

**Phase 1: Core Data Model, Roles, and Authentication (1 week)**

- Key Deliverables: Engineering, Product — base data models, RBAC matrix, user workflows, login and onboarding.
- Dependencies: Design of RBAC structure and user journey.

**Phase 2: Task/Event Engine & UI (1 week)**

- Key Deliverables: Engineering, Product — event creation, Kanban/task management UI, workflow DAG view (static), task assignment/reassignment, auto function triggers, remarks flows.
- Dependencies: Completion of data models, core UI scaffolding.

**Phase 3: Admin Functions, Audit, and Test Scenarios (1 week)**

- Key Deliverables: Product, QA, Engineering — admin matrix, audit logging, override management, workflow conformance testing, error handling.
- Dependencies: Prior phase UIs and business logic validated.

**Phase 4: Polish, Accessibility, and Documentation (0.5–1 week)**

- Key Deliverables: Team — UX/UI polish, accessibility validation, in-app tutorials, sample workflows preloaded, handoff to pilot users.
- Dependencies: Feature-complete application build.
