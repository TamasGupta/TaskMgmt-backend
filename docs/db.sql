BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ===========================
-- HELPER FUNCTIONS
-- ===========================

CREATE OR REPLACE FUNCTION app_current_user_id()
RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT (auth.uid())::uuid;
$$;
REVOKE EXECUTE ON FUNCTION app_current_user_id() FROM PUBLIC, authenticated, anon;

CREATE OR REPLACE FUNCTION app_is_event_member(p_event_id uuid, p_user_id uuid)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT EXISTS (
    SELECT 1 FROM event_memberships em
    WHERE em.event_id = p_event_id
      AND em.user_id = p_user_id
      AND em.deleted_at IS NULL
  );
$$;
REVOKE EXECUTE ON FUNCTION app_is_event_member(uuid, uuid) FROM PUBLIC, authenticated, anon;

CREATE OR REPLACE FUNCTION app_is_global_admin(p_user_id uuid)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT EXISTS (
    SELECT 1 FROM role_members rm
    JOIN roles r ON r.id = rm.role_id
    WHERE rm.user_id = p_user_id
      AND r.is_global = true
      AND rm.deleted_at IS NULL
  );
$$;
REVOKE EXECUTE ON FUNCTION app_is_global_admin(uuid) FROM PUBLIC, authenticated, anon;

CREATE OR REPLACE FUNCTION app_acquire_task_lock(p_task_id uuid, p_user_id uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  _now timestamptz := now();
BEGIN
  UPDATE tasks
  SET locked_by = p_user_id, locked_at = _now
  WHERE id = p_task_id
    AND (locked_by IS NULL OR locked_at < now() - interval '5 minutes')
    AND deleted_at IS NULL;
  RETURN FOUND;
END;
$$;
REVOKE EXECUTE ON FUNCTION app_acquire_task_lock(uuid, uuid) FROM PUBLIC, authenticated, anon;

CREATE OR REPLACE FUNCTION app_release_task_lock(p_task_id uuid, p_user_id uuid)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  UPDATE tasks
  SET locked_by = NULL, locked_at = NULL
  WHERE id = p_task_id AND locked_by = p_user_id;
  RETURN FOUND;
END;
$$;
REVOKE EXECUTE ON FUNCTION app_release_task_lock(uuid, uuid) FROM PUBLIC, authenticated, anon;

-- ===========================
-- ENUM TYPES
-- ===========================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_priority') THEN
    CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'workflow_state_type') THEN
    CREATE TYPE workflow_state_type AS ENUM ('todo', 'in_progress', 'done');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'permission_action') THEN
    CREATE TYPE permission_action AS ENUM ('create', 'read', 'update', 'delete');
  END IF;
END;
$$;

-- ===========================
-- CORE TABLES
-- ===========================

CREATE TABLE IF NOT EXISTS users (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  auth_uid    uuid UNIQUE,
  name        text,
  email       text UNIQUE NOT NULL,
  is_active   boolean NOT NULL DEFAULT TRUE,
  access_level text NOT NULL DEFAULT 'event',
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz
);
CREATE INDEX IF NOT EXISTS idx_users_authuid ON users(auth_uid);
CREATE INDEX IF NOT EXISTS idx_users_email   ON users(email);

CREATE TABLE IF NOT EXISTS workflows (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  created_by  uuid REFERENCES users(id),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz
);

CREATE TABLE IF NOT EXISTS workflow_states (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id uuid NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
  key         text NOT NULL,
  name        text NOT NULL,
  type        workflow_state_type NOT NULL DEFAULT 'todo',
  position    int,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_workflow_states_workflow_key
  ON workflow_states(workflow_id, key);

CREATE TABLE IF NOT EXISTS workflow_transitions (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id      uuid NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
  from_state_key   text NOT NULL,
  to_state_key     text NOT NULL,
  auto_create_tasks jsonb,
  created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wt_workflow ON workflow_transitions(workflow_id);

CREATE TABLE IF NOT EXISTS roles (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL UNIQUE,
  description text,
  is_global   boolean NOT NULL DEFAULT false,
  created_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz
);

CREATE TABLE IF NOT EXISTS transition_allowed_roles (
  transition_id uuid NOT NULL REFERENCES workflow_transitions(id) ON DELETE CASCADE,
  role_id       uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  PRIMARY KEY (transition_id, role_id)
);

CREATE TABLE IF NOT EXISTS events (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  description text,
  workflow_id uuid NOT NULL REFERENCES workflows(id),
  status      text,
  created_by  uuid REFERENCES users(id),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz
);
CREATE INDEX IF NOT EXISTS idx_events_workflow ON events(workflow_id);

CREATE TABLE IF NOT EXISTS event_memberships (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id   uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id    uuid REFERENCES roles(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  UNIQUE (event_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_event_members_user ON event_memberships(user_id, event_id);

CREATE TABLE IF NOT EXISTS tasks (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id        uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  title           text NOT NULL,
  description     text,
  assignee_id     uuid REFERENCES users(id),
  assignee_role_id uuid REFERENCES roles(id),
  state_key       text NOT NULL,
  priority        task_priority DEFAULT 'medium',
  due_date        timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  deleted_at      timestamptz,
  locked_by       uuid REFERENCES users(id),
  locked_at       timestamptz
);
CREATE INDEX IF NOT EXISTS idx_tasks_event    ON tasks(event_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX IF NOT EXISTS idx_tasks_state    ON tasks(state_key);

CREATE TABLE IF NOT EXISTS remarks (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id    uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  event_id   uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  user_id    uuid NOT NULL REFERENCES users(id),
  remark     text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_remarks_task ON remarks(task_id);

CREATE TABLE IF NOT EXISTS audit_logs (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id      uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  event_id     uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  from_state   text,
  to_state     text,
  performed_by uuid NOT NULL REFERENCES users(id),
  comment      text NOT NULL,
  warning      boolean NOT NULL DEFAULT false,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_logs(event_id);
CREATE INDEX IF NOT EXISTS idx_audit_task  ON audit_logs(task_id);

CREATE TABLE IF NOT EXISTS permissions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  resource    text NOT NULL,
  action      permission_action NOT NULL,
  description text
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_permissions_resource_action
  ON permissions(resource, action);

CREATE TABLE IF NOT EXISTS role_permissions (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  role_id       uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_id uuid NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
  created_at    timestamptz NOT NULL DEFAULT now(),
  deleted_at    timestamptz,
  UNIQUE (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS role_members (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  role_id    uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  UNIQUE (role_id, user_id)
);

-- ===========================
-- SOFT DELETE UTILITY
-- ===========================

CREATE OR REPLACE FUNCTION app_soft_delete(table_name text, row_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  IF    table_name = 'events' THEN UPDATE events SET deleted_at = now() WHERE id = row_id;
  ELSIF table_name = 'tasks'  THEN UPDATE tasks  SET deleted_at = now() WHERE id = row_id;
  ELSIF table_name = 'users'  THEN UPDATE users  SET deleted_at = now() WHERE id = row_id;
  ELSIF table_name = 'roles'  THEN UPDATE roles  SET deleted_at = now() WHERE id = row_id;
  ELSE  RAISE EXCEPTION 'Soft delete not implemented for %', table_name;
  END IF;
END;
$$;
REVOKE EXECUTE ON FUNCTION app_soft_delete(text, uuid) FROM PUBLIC, authenticated, anon;

-- ===========================
-- ROW LEVEL SECURITY POLICIES
-- ===========================

-- users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_select_authenticated ON users FOR SELECT TO authenticated
  USING (
    (deleted_at IS NULL) AND (
      app_is_global_admin((SELECT app_current_user_id()))
      OR id = (SELECT app_current_user_id())
    )
  );
CREATE POLICY users_update_self ON users FOR UPDATE TO authenticated
  USING (id = (SELECT app_current_user_id()))
  WITH CHECK (id = (SELECT app_current_user_id()));

-- events
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
CREATE POLICY events_select_by_membership ON events FOR SELECT TO authenticated
  USING (
    deleted_at IS NULL AND (
      app_is_global_admin((SELECT app_current_user_id()))
      OR app_is_event_member(id, (SELECT app_current_user_id()))
    )
  );
CREATE POLICY events_insert_authenticated ON events FOR INSERT TO authenticated
  WITH CHECK (
    deleted_at IS NULL AND (
      app_is_global_admin((SELECT app_current_user_id()))
      OR (created_by = (SELECT app_current_user_id()))
    )
  );
CREATE POLICY events_update_by_admin_or_creator ON events FOR UPDATE TO authenticated
  USING (
    deleted_at IS NULL AND (
      app_is_global_admin((SELECT app_current_user_id()))
      OR created_by = (SELECT app_current_user_id())
    )
  )
  WITH CHECK (deleted_at IS NULL);

-- event_memberships
ALTER TABLE event_memberships ENABLE ROW LEVEL SECURITY;
CREATE POLICY event_members_select ON event_memberships FOR SELECT TO authenticated
  USING (
    deleted_at IS NULL AND (
      app_is_global_admin((SELECT app_current_user_id()))
      OR user_id = (SELECT app_current_user_id())
      OR app_is_event_member(event_id, (SELECT app_current_user_id()))
    )
  );
CREATE POLICY event_members_insert ON event_memberships FOR INSERT TO authenticated
  WITH CHECK (
    deleted_at IS NULL AND (
      app_is_global_admin((SELECT app_current_user_id()))
      OR user_id = (SELECT app_current_user_id())
    )
  );

-- tasks
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY tasks_select_by_visibility ON tasks FOR SELECT TO authenticated
  USING (
    deleted_at IS NULL AND (
      app_is_global_admin((SELECT app_current_user_id()))
      OR assignee_id = (SELECT app_current_user_id())
      OR assignee_role_id IN (
        SELECT role_id FROM event_memberships em
        WHERE em.event_id = tasks.event_id
          AND em.user_id = (SELECT app_current_user_id())
          AND em.deleted_at IS NULL
      )
      OR app_is_event_member(event_id, (SELECT app_current_user_id()))
    )
  );
CREATE POLICY tasks_insert_authenticated ON tasks FOR INSERT TO authenticated
  WITH CHECK (
    deleted_at IS NULL AND (
      app_is_global_admin((SELECT app_current_user_id()))
      OR created_at IS NOT NULL
    )
  );
CREATE POLICY tasks_update_by_assignee_or_event ON tasks FOR UPDATE TO authenticated
  USING (
    deleted_at IS NULL AND (
      app_is_global_admin((SELECT app_current_user_id()))
      OR assignee_id = (SELECT app_current_user_id())
      OR app_is_event_member(event_id, (SELECT app_current_user_id()))
    )
  )
  WITH CHECK (deleted_at IS NULL);

-- remarks
ALTER TABLE remarks ENABLE ROW LEVEL SECURITY;
CREATE POLICY remarks_select_by_event ON remarks FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM events e
      WHERE e.id = remarks.event_id AND e.deleted_at IS NULL AND (
        app_is_global_admin((SELECT app_current_user_id()))
        OR app_is_event_member(e.id, (SELECT app_current_user_id()))
      )
    )
  );
CREATE POLICY remarks_insert_auth ON remarks FOR INSERT TO authenticated
  WITH CHECK (
    user_id = (SELECT app_current_user_id())
    AND remark IS NOT NULL AND remark <> ''
  );

-- audit_logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_select ON audit_logs FOR SELECT TO authenticated
  USING (
    app_is_global_admin((SELECT app_current_user_id()))
    OR app_is_event_member(event_id, (SELECT app_current_user_id()))
  );

-- roles
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY roles_select_admin ON roles FOR SELECT TO authenticated
  USING (deleted_at IS NULL AND app_is_global_admin((SELECT app_current_user_id())));

-- permissions
ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY permissions_select_admin ON permissions FOR SELECT TO authenticated
  USING (app_is_global_admin((SELECT app_current_user_id())));

-- role_members
ALTER TABLE role_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY role_members_admin ON role_members FOR ALL TO authenticated
  USING (app_is_global_admin((SELECT app_current_user_id())))
  WITH CHECK (app_is_global_admin((SELECT app_current_user_id())));

-- role_permissions
ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY role_permissions_admin ON role_permissions FOR ALL TO authenticated
  USING (app_is_global_admin((SELECT app_current_user_id())))
  WITH CHECK (app_is_global_admin((SELECT app_current_user_id())));

COMMIT;

-- End of db.sql
