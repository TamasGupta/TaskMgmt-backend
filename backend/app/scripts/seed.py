"""
LinkDem Seed Script
===================
Run once after migrations to seed:
1. Standard roles (global_admin, event_manager, team_member)
2. Permissions (CRUD × resources) and role-permission assignments
3. Link user@example.com (already in Supabase Auth) → users table + global_admin role
4. Sample "Birthday Party" workflow
5. Sample "Indian Marriage" workflow
6. Self-test: verify global admin status + test login

Usage:
    cd backend
    python -m app.scripts.seed
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

# Ensure 'backend/' is on path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.supabase import anon_client, service_client
from app.models.role import Role, Permission, RolePermission, RoleMember
from app.models.user import User
from app.models.workflow import Workflow, WorkflowState, WorkflowTransition


# ---------------------------------------------------------------------------
# Engine – service-role connection for seed (bypasses RLS)
# ---------------------------------------------------------------------------
_CONNECT_ARGS = {
    "statement_cache_size": 0,           # required for PgBouncer transaction mode
    "prepared_statement_cache_size": 0,  # asyncpg >= 0.28
}
_db_url = settings.DATABASE_URL
if "prepared_statement_cache_size" not in _db_url:
    _db_url += ("&" if "?" in _db_url else "?") + "prepared_statement_cache_size=0"

engine = create_async_engine(
    _db_url,
    echo=False,
    json_serializer=json.dumps,
    json_deserializer=json.loads,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_or_create_role(db: AsyncSession, name: str, is_global: bool = False, description: str = "") -> Role:
    result = await db.execute(select(Role).where(Role.name == name, Role.deleted_at.is_(None)))
    role = result.scalar_one_or_none()
    if role:
        print(f"  Role exists: {name}")
        return role
    role = Role(name=name, is_global=is_global, description=description)
    db.add(role)
    await db.flush()
    print(f"  Created role: {name} (is_global={is_global})")
    return role


async def get_or_create_permission(db: AsyncSession, resource: str, action: str) -> Permission:
    result = await db.execute(
        select(Permission).where(Permission.resource == resource, Permission.action == action)
    )
    perm = result.scalar_one_or_none()
    if perm:
        return perm
    perm = Permission(resource=resource, action=action, description=f"{action} on {resource}")
    db.add(perm)
    await db.flush()
    return perm


async def assign_permission(db: AsyncSession, role: Role, perm: Permission) -> None:
    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == perm.id,
            RolePermission.deleted_at.is_(None),
        )
    )
    if not result.scalar_one_or_none():
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        await db.flush()


async def seed_roles_and_permissions(db: AsyncSession) -> dict[str, Role]:
    print("\n[1] Seeding roles and permissions...")
    global_admin = await get_or_create_role(db, "global_admin", is_global=True, description="Full system access")
    event_manager = await get_or_create_role(db, "event_manager", is_global=False, description="Manages assigned events")
    team_member = await get_or_create_role(db, "team_member", is_global=False, description="Executes assigned tasks")

    resources = ["events", "tasks", "users", "workflows", "roles", "audit_logs"]
    actions = ["create", "read", "update", "delete"]

    # Global admin gets everything
    for res in resources:
        for act in actions:
            perm = await get_or_create_permission(db, res, act)
            await assign_permission(db, global_admin, perm)

    # Event manager gets: events (RU), tasks (CRUD), users (R), workflows (R)
    em_perms = {
        "events": ["read", "update"],
        "tasks": ["create", "read", "update"],
        "users": ["read"],
        "workflows": ["read"],
        "audit_logs": ["read"],
    }
    for res, acts in em_perms.items():
        for act in acts:
            perm = await get_or_create_permission(db, res, act)
            await assign_permission(db, event_manager, perm)

    # Team member gets: tasks (RU), events (R)
    tm_perms = {
        "tasks": ["read", "update"],
        "events": ["read"],
    }
    for res, acts in tm_perms.items():
        for act in acts:
            perm = await get_or_create_permission(db, res, act)
            await assign_permission(db, team_member, perm)

    print("  Permissions assigned.")
    return {"global_admin": global_admin, "event_manager": event_manager, "team_member": team_member}


async def seed_admin_user(db: AsyncSession, global_admin_role: Role) -> User:
    """
    Link user@example.com (pre-existing in Supabase Auth) to users table
    and assign global_admin role.
    """
    print(f"\n[2] Seeding admin user: {settings.SUPABASE_AUTH_EMAIL}")

    # Look up auth UID from Supabase Admin API
    auth_uid: uuid.UUID | None = None
    try:
        resp = service_client.auth.admin.list_users()
        # resp may be a list or paginated; handle both
        users_list = resp if isinstance(resp, list) else getattr(resp, "users", [])
        for u in users_list:
            if getattr(u, "email", None) == settings.SUPABASE_AUTH_EMAIL:
                auth_uid = uuid.UUID(u.id)
                break
    except Exception as e:
        print(f"  Warning: Could not list Supabase users: {e}")

    if auth_uid is None:
        print(f"  Warning: Could not find Supabase auth user for {settings.SUPABASE_AUTH_EMAIL}.")
        print("  Creating local user profile without auth_uid (will link on first login).")

    # Check if user already exists in DB
    query = select(User).where(User.email == settings.SUPABASE_AUTH_EMAIL, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user:
        print(f"  User profile exists: {user.email} (id={user.id})")
        if auth_uid and user.auth_uid != auth_uid:
            await db.execute(update(User).where(User.id == user.id).values(auth_uid=auth_uid, access_level="global"))
            await db.flush()
            print("  Updated auth_uid and set access_level=global.")
        elif user.access_level != "global":
            await db.execute(update(User).where(User.id == user.id).values(access_level="global"))
            await db.flush()
            print("  Set access_level=global.")
    else:
        user = User(
            auth_uid=auth_uid,
            email=settings.SUPABASE_AUTH_EMAIL,
            name="System Admin",
            is_active=True,
            access_level="global",
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        print(f"  Created user profile: {user.email} (id={user.id})")

    # Reload after potential update
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # Assign global_admin role
    existing_rm = await db.execute(
        select(RoleMember).where(
            RoleMember.user_id == user.id,
            RoleMember.role_id == global_admin_role.id,
            RoleMember.deleted_at.is_(None),
        )
    )
    if not existing_rm.scalar_one_or_none():
        db.add(RoleMember(role_id=global_admin_role.id, user_id=user.id))
        await db.flush()
        print(f"  Assigned global_admin role to {user.email}.")
    else:
        print(f"  global_admin role already assigned to {user.email}.")

    return user


async def seed_workflow(
    db: AsyncSession,
    name: str,
    states: list[dict],
    transitions: list[dict],
    created_by: uuid.UUID | None = None,
) -> Workflow:
    """Idempotent: skip if workflow with this name already exists."""
    result = await db.execute(select(Workflow).where(Workflow.name == name, Workflow.deleted_at.is_(None)))
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  Workflow already exists: {name}")
        return existing

    wf = Workflow(name=name, created_by=created_by)
    db.add(wf)
    await db.flush()

    for i, s in enumerate(states):
        ws = WorkflowState(
            workflow_id=wf.id,
            key=s["key"],
            name=s["name"],
            type=s.get("type", "todo"),
            position=i,
        )
        db.add(ws)

    await db.flush()

    for t in transitions:
        auto_tasks = t.get("auto_create_tasks") or None
        wt = WorkflowTransition(
            workflow_id=wf.id,
            from_state_key=t["from"],
            to_state_key=t["to"],
            auto_create_tasks=auto_tasks,
        )
        db.add(wt)

    await db.flush()
    print(f"  Created workflow: {name} ({len(states)} states, {len(transitions)} transitions)")
    return wf


async def seed_sample_workflows(db: AsyncSession, admin_user: User) -> None:
    print("\n[3] Seeding sample workflows...")

    # ---- Birthday Party Workflow ----
    birthday_states = [
        {"key": "todo",       "name": "To Do",     "type": "todo"},
        {"key": "in_progress","name": "In Progress","type": "in_progress"},
        {"key": "blocked",    "name": "Blocked",    "type": "todo"},
        {"key": "validate",   "name": "Validate",   "type": "in_progress"},
        {"key": "done",       "name": "Done",       "type": "done"},
    ]
    birthday_transitions = [
        {"from": "todo",        "to": "in_progress", "auto_create_tasks": None},
        {"from": "in_progress", "to": "blocked",     "auto_create_tasks": None},
        {"from": "blocked",     "to": "in_progress", "auto_create_tasks": None},
        {"from": "in_progress", "to": "validate",    "auto_create_tasks": None},
        {"from": "validate",    "to": "in_progress", "auto_create_tasks": None},
        {
            "from": "validate",
            "to": "done",
            "auto_create_tasks": [
                {"title": "Post-event cleanup", "state_key": "todo", "priority": "low"},
                {"title": "Send thank-you messages", "state_key": "todo", "priority": "low"},
            ],
        },
    ]
    await seed_workflow(db, "Birthday Party", birthday_states, birthday_transitions, admin_user.id)

    # ---- Indian Marriage Workflow ----
    marriage_states = [
        {"key": "planning",       "name": "Planning",         "type": "todo"},
        {"key": "vendor_booking", "name": "Vendor Booking",   "type": "todo"},
        {"key": "in_progress",    "name": "In Progress",      "type": "in_progress"},
        {"key": "blocked",        "name": "Blocked",          "type": "todo"},
        {"key": "decoration",     "name": "Decoration Setup", "type": "in_progress"},
        {"key": "catering",       "name": "Catering Setup",   "type": "in_progress"},
        {"key": "ceremony",       "name": "Ceremony",         "type": "in_progress"},
        {"key": "validate",       "name": "Validate",         "type": "in_progress"},
        {"key": "done",           "name": "Done",             "type": "done"},
    ]
    marriage_transitions = [
        {"from": "planning",       "to": "vendor_booking",  "auto_create_tasks": None},
        {"from": "vendor_booking", "to": "in_progress",     "auto_create_tasks": None},
        {"from": "in_progress",    "to": "blocked",         "auto_create_tasks": None},
        {"from": "blocked",        "to": "in_progress",     "auto_create_tasks": None},
        {"from": "in_progress",    "to": "decoration",      "auto_create_tasks": None},
        {"from": "in_progress",    "to": "catering",        "auto_create_tasks": None},
        {"from": "decoration",     "to": "ceremony",        "auto_create_tasks": None},
        {"from": "catering",       "to": "ceremony",        "auto_create_tasks": None},
        {"from": "ceremony",       "to": "validate",        "auto_create_tasks": None},
        {"from": "validate",       "to": "in_progress",     "auto_create_tasks": None},
        {
            "from": "validate",
            "to": "done",
            "auto_create_tasks": [
                {"title": "Venue closeout and cleanup",   "state_key": "todo", "priority": "medium"},
                {"title": "Photographer handoff",         "state_key": "todo", "priority": "low"},
                {"title": "Guest feedback collection",    "state_key": "todo", "priority": "low"},
                {"title": "Vendor payment settlement",    "state_key": "todo", "priority": "high"},
            ],
        },
    ]
    await seed_workflow(db, "Indian Marriage", marriage_states, marriage_transitions, admin_user.id)


async def verify_admin(db: AsyncSession, user: User) -> None:
    print(f"\n[4] Verifying global admin status for {user.email}...")
    result = await db.execute(
        text(
            """
            SELECT COUNT(*) FROM role_members rm
            JOIN roles r ON r.id = rm.role_id
            WHERE rm.user_id = :uid
              AND r.is_global = true
              AND rm.deleted_at IS NULL
              AND r.deleted_at IS NULL
            """
        ),
        {"uid": str(user.id)},
    )
    count = result.scalar() or 0
    if count > 0:
        print(f"  ✓ {user.email} is a confirmed global admin.")
    else:
        print(f"  ✗ Warning: {user.email} is NOT a global admin – check seed data!")


async def test_login() -> None:
    print(f"\n[5] Testing login for {settings.SUPABASE_AUTH_EMAIL}...")
    try:
        resp = anon_client.auth.sign_in_with_password(
            {"email": settings.SUPABASE_AUTH_EMAIL, "password": settings.SUPABASE_AUTH_PASSWORD}
        )
        if resp.session:
            tok = resp.session.access_token[:40] + "..."
            print(f"  ✓ Login successful. Access token (truncated): {tok}")
        else:
            print("  ✗ Login returned no session – check email/password in .env")
    except Exception as e:
        print(f"  ✗ Login failed: {e}")


async def main() -> None:
    print("=" * 60)
    print("LinkDem Seed Script")
    print("=" * 60)

    async with SessionFactory() as db:
        async with db.begin():
            roles = await seed_roles_and_permissions(db)
            admin_user = await seed_admin_user(db, roles["global_admin"])
            await seed_sample_workflows(db, admin_user)

    async with SessionFactory() as db:
        result = await db.execute(
            select(User).where(User.email == settings.SUPABASE_AUTH_EMAIL)
        )
        admin = result.scalar_one_or_none()
        if admin:
            await verify_admin(db, admin)

    await test_login()

    print("\n" + "=" * 60)
    print("Seed complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
