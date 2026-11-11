"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import { request, RequestScope } from "./request";
import { buildEditablePayload, localDateTime } from "./payload";
const primaryKeys: Record<string, string> = {
  components: "component_id",
  incidents: "incident_id",
  technicians: "technician_id",
  locations: "location_id",
  categories: "category_id",
  assessments: "assessment_id",
  "work-orders": "work_order_id",
  "maintenance-records": "maintenance_id",
  "sensor-readings": "reading_id",
  "maintenance-alerts": "alert_id",
  "audit-logs": "audit_id",
};
type Resource = {
  key: string;
  label: string;
  fields: {
    name: string;
    label: string;
    type?: string;
    options?: string[];
    nullable?: boolean;
    optional?: boolean;
  }[];
};
const resources: Resource[] = [
  {
    key: "components",
    label: "Components",
    fields: [
      { name: "asset_tag", label: "Asset tag" },
      { name: "location_id", label: "Location ID", type: "number" },
      { name: "category_id", label: "Category ID", type: "number" },
      { name: "name", label: "Name" },
      {
        name: "status",
        label: "Status",
        options: ["OPERATIONAL", "DEGRADED", "OUT_OF_SERVICE", "RETIRED"],
      },
      {
        name: "installed_on",
        label: "Installed on",
        type: "date",
        nullable: true,
      },
    ],
  },
  {
    key: "incidents",
    label: "Incidents",
    fields: [
      { name: "incident_number", label: "Incident number" },
      { name: "reported_at", label: "Reported at", type: "datetime-local" },
      {
        name: "severity",
        label: "Severity",
        options: ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
      },
      {
        name: "status",
        label: "Status",
        options: ["OPEN", "INVESTIGATING", "RESOLVED", "CLOSED"],
      },
      {
        name: "resolved_at",
        label: "Resolved at",
        type: "datetime-local",
        nullable: true,
      },
      { name: "title", label: "Title" },
      { name: "description", label: "Description", type: "textarea" },
    ],
  },
  {
    key: "technicians",
    label: "Technicians",
    fields: [
      { name: "employee_code", label: "Employee code" },
      { name: "full_name", label: "Full name" },
      { name: "email", label: "Email", type: "email" },
      { name: "specialty", label: "Specialty" },
      { name: "active", label: "Active", type: "checkbox" },
    ],
  },
  {
    key: "locations",
    label: "Locations",
    fields: [
      { name: "location_code", label: "Location code" },
      { name: "name", label: "Name" },
      { name: "address", label: "Address" },
      { name: "region", label: "Region" },
    ],
  },
  {
    key: "categories",
    label: "Categories",
    fields: [
      { name: "category_code", label: "Category code" },
      { name: "name", label: "Name" },
      {
        name: "description",
        label: "Description",
        type: "textarea",
        nullable: true,
      },
    ],
  },
  {
    key: "assessments",
    label: "Assessments",
    fields: [
      { name: "component_id", label: "Component ID", type: "number" },
      { name: "technician_id", label: "Technician ID", type: "number" },
      { name: "assessed_at", label: "Assessed at", type: "datetime-local" },
      { name: "health_score", label: "Health score", type: "number" },
      {
        name: "condition_status",
        label: "Condition",
        options: ["GOOD", "FAIR", "POOR", "CRITICAL"],
      },
      { name: "findings", label: "Findings", type: "textarea" },
    ],
  },
  {
    key: "work-orders",
    label: "Work orders",
    fields: [
      { name: "work_order_number", label: "Work-order number" },
      {
        name: "incident_id",
        label: "Incident ID",
        type: "number",
        nullable: true,
      },
      {
        name: "component_id",
        label: "Component ID",
        type: "number",
        nullable: true,
      },
      {
        name: "technician_id",
        label: "Technician ID",
        type: "number",
        nullable: true,
      },
      {
        name: "work_type",
        label: "Type",
        options: ["CORRECTIVE", "PREVENTIVE"],
      },
      {
        name: "status",
        label: "Status",
        options: [
          "PLANNED",
          "ASSIGNED",
          "IN_PROGRESS",
          "COMPLETED",
          "CANCELLED",
        ],
      },
      { name: "planned_start", label: "Planned start", type: "date" },
      {
        name: "planned_end",
        label: "Planned end",
        type: "date",
        nullable: true,
      },
      { name: "estimated_cost", label: "Estimated cost", type: "number" },
      {
        name: "completion_notes",
        label: "Completion notes",
        type: "textarea",
        nullable: true,
      },
    ],
  },
  {
    key: "maintenance-records",
    label: "Maintenance records",
    fields: [
      { name: "work_order_id", label: "Work order ID", type: "number" },
      { name: "technician_id", label: "Technician ID", type: "number" },
      { name: "performed_at", label: "Performed at", type: "datetime-local" },
      { name: "action_taken", label: "Action taken", type: "textarea" },
      { name: "actual_cost", label: "Actual cost", type: "number" },
      {
        name: "outcome",
        label: "Outcome",
        options: ["SUCCESSFUL", "PARTIAL", "UNSUCCESSFUL"],
      },
    ],
  },
  {
    key: "sensor-readings",
    label: "Sensor readings",
    fields: [
      { name: "component_id", label: "Component ID", type: "number" },
      { name: "recorded_at", label: "Recorded at", type: "datetime-local" },
      { name: "sensor_type", label: "Sensor type" },
      { name: "reading_value", label: "Reading", type: "number" },
      { name: "unit", label: "Unit" },
    ],
  },
  {
    key: "maintenance-alerts",
    label: "Maintenance alerts",
    fields: [
      {
        name: "status",
        label: "Status",
        options: ["OPEN", "ACKNOWLEDGED", "RESOLVED"],
      },
    ],
  },
];
const tone = (v: string) => String(v || "").toLowerCase();
function Form({
  resource,
  initial,
  onSaved,
  onCancel,
}: {
  resource: Resource;
  initial: any;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const defaults = () =>
    Object.fromEntries(
      resource.fields
        .filter((f) => f.type === "checkbox")
        .map((f) => [f.name, true]),
    );
  const [form, setForm] = useState<any>(initial || defaults()),
    [error, setError] = useState(""),
    [saving, setSaving] = useState(false);
  useEffect(() => {
    setForm(initial || defaults());
    setError("");
  }, [initial?.__id, initial?.__complete]);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const body = form.__complete
        ? { ...form }
        : buildEditablePayload(resource.fields, form);
      delete body.__complete;
      if (form.__complete) {
        await request(`/api/work-orders/${initial.__id}/complete`, {
          method: "POST",
          body: JSON.stringify({
            technician_id: Number(body.technician_id),
            action_taken: body.action_taken,
            actual_cost: Number(body.actual_cost),
            outcome: body.outcome,
            completed_at: new Date(body.completed_at).toISOString(),
            completion_notes: body.completion_notes,
          }),
        });
      } else
        await request(
          initial?.__id
            ? `/api/${resource.key}/${initial.__id}`
            : `/api/${resource.key}`,
          {
            method: initial?.__id ? "PATCH" : "POST",
            body: JSON.stringify(body),
          },
        );
      onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  const completing = resource.key === "work-orders" && !!form.__complete;
  return (
    <form className="form" onSubmit={submit}>
      {error && <div className="error">{error}</div>}
      {!completing &&
        resource.fields.map((f) => (
          <label key={f.name}>
            {f.label}
            {f.type === "checkbox" ? (
              <input
                type="checkbox"
                checked={!!form[f.name]}
                onChange={(e) =>
                  setForm({ ...form, [f.name]: e.target.checked })
                }
              />
            ) : f.options ? (
              <select
                required={!f.nullable && !f.optional}
                value={form[f.name] ?? ""}
                onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
              >
                <option value="">Select…</option>
                {f.options.map((o) => (
                  <option
                    key={o}
                    disabled={
                      resource.key === "work-orders" &&
                      o === "COMPLETED" &&
                      initial?.status !== "COMPLETED"
                    }
                  >
                    {o}
                  </option>
                ))}
              </select>
            ) : f.type === "textarea" ? (
              <textarea
                required={!f.nullable && !f.optional}
                value={form[f.name] ?? ""}
                onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
              />
            ) : (
              <input
                required={!f.nullable && !f.optional}
                step={
                  f.type === "datetime-local"
                    ? "0.001"
                    : f.type === "number"
                      ? f.name.endsWith("_id")
                        ? "1"
                        : "any"
                      : undefined
                }
                type={f.type || "text"}
                value={
                  f.type === "datetime-local"
                    ? localDateTime(form[f.name])
                    : (form[f.name] ?? "")
                }
                onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
              />
            )}
          </label>
        ))}
      {completing && (
        <>
          <div className="completion-context">
            <b>{initial.work_order_number}</b>
            <span>Current status: {initial.status}</span>
            <span>Component ID: {initial.component_id ?? "—"}</span>
          </div>
          <label>
            Technician ID
            <input
              required
              type="number"
              value={form.technician_id ?? ""}
              onChange={(e) =>
                setForm({ ...form, technician_id: e.target.value })
              }
            />
          </label>
          <label>
            Action taken / maintenance notes
            <textarea
              required
              value={form.action_taken ?? ""}
              onChange={(e) =>
                setForm({ ...form, action_taken: e.target.value })
              }
            />
          </label>
          <label>
            Actual repair cost
            <input
              required
              min="0"
              step="0.01"
              type="number"
              value={form.actual_cost ?? ""}
              onChange={(e) =>
                setForm({ ...form, actual_cost: e.target.value })
              }
            />
          </label>
          <label>
            Outcome
            <select
              required
              value={form.outcome ?? ""}
              onChange={(e) => setForm({ ...form, outcome: e.target.value })}
            >
              <option value="">Select…</option>
              <option>SUCCESSFUL</option>
              <option>PARTIAL</option>
              <option>UNSUCCESSFUL</option>
            </select>
          </label>
          <label>
            Completed at
            <input
              required
              step="0.001"
              type="datetime-local"
              value={localDateTime(form.completed_at)}
              onChange={(e) =>
                setForm({ ...form, completed_at: e.target.value })
              }
            />
          </label>
          <label>
            Resolution notes
            <textarea
              required
              value={form.completion_notes ?? ""}
              onChange={(e) =>
                setForm({ ...form, completion_notes: e.target.value })
              }
            />
          </label>
        </>
      )}
      <div className="form-actions">
        {resource.key === "work-orders" &&
          initial?.__id &&
          !["COMPLETED", "CANCELLED"].includes(initial.status) &&
          !completing && (
            <button
              type="button"
              className="primary"
              onClick={() => setForm({ ...form, __complete: true })}
            >
              Complete Work Order
            </button>
          )}
        <button type="button" className="ghost" onClick={onCancel}>
          Cancel
        </button>
        <button disabled={saving} className="primary">
          {saving
            ? completing
              ? "Completing…"
              : "Saving…"
            : completing
              ? "Complete Work Order"
              : "Save record"}
        </button>
      </div>
    </form>
  );
}
function Management({ resource }: { resource: Resource }) {
  const readOnly = resource.key === "audit-logs";
  const generated = resource.key === "maintenance-alerts";
  const [items, setItems] = useState<any[]>([]),
    [selected, setSelected] = useState<any>(),
    [edit, setEdit] = useState<any>(),
    [add, setAdd] = useState(false);
  const [q, setQ] = useState(""),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [deleting, setDeleting] = useState(false);
  const [offset, setOffset] = useState(0),
    [appliedSearch, setAppliedSearch] = useState("");
  const reads = useRef(new RequestScope());
  function doSearch() {
    if (offset === 0 && appliedSearch === q) load();
    else {
      setOffset(0);
      setAppliedSearch(q);
    }
  }
  async function load() {
    const controller = reads.current.start();
    setLoading(true);
    setError("");
    try {
      const records = await request(
        `/api/${resource.key}?limit=25&offset=${offset}&search=${encodeURIComponent(appliedSearch)}`,
        { signal: controller.signal },
      );
      if (reads.current.isCurrent(controller)) {
        setItems(records);
        setSelected((current: any) => {
          if (!current) return current;
          const fresh = records.find(
            (record: any) => record[primaryKeys[resource.key]] === current.id,
          );
          return fresh ? { ...fresh, id: current.id } : undefined;
        });
      }
    } catch (e) {
      if (reads.current.isCurrent(controller)) setError((e as Error).message);
    } finally {
      if (reads.current.isCurrent(controller)) setLoading(false);
    }
  }
  useEffect(() => {
    setSelected(undefined);
    setEdit(undefined);
    setAdd(false);
    load();
    return () => reads.current.cancel();
  }, [resource.key, offset, appliedSearch]);
  async function remove(id: number) {
    if (
      deleting ||
      !confirm(
        "Delete this record? PostgreSQL will protect historical records where required.",
      )
    )
      return;
    setDeleting(true);
    try {
      await request(`/api/${resource.key}/${id}`, { method: "DELETE" });
      setSelected(undefined);
      if (items.length === 1 && offset > 0) setOffset(offset - 25);
      else load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeleting(false);
    }
  }
  return (
    <section className="content">
      <header>
        <div>
          <p className="eyebrow">MANAGEMENT / {resource.label.toUpperCase()}</p>
          <h1>{resource.label}</h1>
          <p className="muted">
            Live records from PostgreSQL. Mutations refresh after API
            confirmation.
          </p>
        </div>
        {!readOnly && !generated && (
          <button
            className="primary"
            onClick={() => {
              setEdit(undefined);
              setAdd(true);
            }}
          >
            ＋ Add
          </button>
        )}
      </header>
      {error && <div className="error">{error}</div>}
      <div className="toolbar">
        <input
          placeholder={`Search ${resource.label.toLowerCase()}…`}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch()}
        />
        <button className="ghost" onClick={doSearch}>
          Search
        </button>
      </div>
      <div className="toolbar">
        <button
          className="ghost"
          disabled={loading || offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 25))}
        >
          Previous
        </button>
        <span>Page {offset / 25 + 1}</span>
        <button
          className="ghost"
          disabled={loading || items.length < 25}
          onClick={() => setOffset(offset + 25)}
        >
          Next
        </button>
      </div>
      <div className="management-grid">
        <section className="panel">
          <div className="table">
            {loading ? (
              <div className="empty">Loading records…</div>
            ) : !items.length ? (
              <div className="empty">No records found.</div>
            ) : (
              items.map((x) => {
                const id = x[primaryKeys[resource.key]];
                return (
                  <button
                    className={`record-row ${selected?.id === id ? "chosen" : ""}`}
                    key={id}
                    onClick={() => {
                      setAdd(false);
                      setEdit(undefined);
                      setSelected({ ...x, id });
                    }}
                  >
                    <span className="record-title">
                      {x.name ||
                        x.title ||
                        x.incident_number ||
                        x.work_order_number ||
                        x.asset_tag ||
                        `Record ${id}`}
                    </span>
                    <span className="pill">
                      {x.status ||
                        x.condition_status ||
                        x.severity ||
                        "ID " + id}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </section>
        <aside className="detail panel">
          {!readOnly && (add || edit) && (
            <>
              <div className="panel-head">
                <h2>
                  {edit ? "Edit" : "New"} {resource.label}
                </h2>
              </div>
              <Form
                resource={resource}
                initial={edit}
                onCancel={() => {
                  setAdd(false);
                  setEdit(undefined);
                }}
                onSaved={() => {
                  setAdd(false);
                  setEdit(undefined);
                  setSelected(undefined);
                  load();
                }}
              />
            </>
          )}
          {!add && !edit && !selected && (
            <div className="empty">Select a record to inspect details.</div>
          )}
          {!add && !edit && selected && (
            <>
              <div className="panel-head">
                <h2>Record detail</h2>
                {!readOnly && (
                  <button
                    className="link"
                    onClick={() => setEdit({ ...selected, __id: selected.id })}
                  >
                    Edit
                  </button>
                )}
              </div>
              {Object.entries(selected)
                .filter(([k]) => k !== "id")
                .map(([k, v]) => (
                  <div className="detail-line" key={k}>
                    <small>{k.replaceAll("_", " ")}</small>
                    <span>
                      {v !== null && typeof v === "object"
                        ? JSON.stringify(v, null, 2)
                        : String(v ?? "—")}
                    </span>
                  </div>
                ))}
              {!readOnly && !generated && (
                <button
                  disabled={deleting}
                  className="danger"
                  onClick={() => remove(selected.id)}
                >
                  {deleting ? "Deleting…" : "Delete record"}
                </button>
              )}
            </>
          )}
        </aside>
      </div>
    </section>
  );
}
function Overview() {
  const [data, setData] = useState<any>(),
    [incidents, setIncidents] = useState<any[]>([]),
    [query, setQuery] = useState(""),
    [error, setError] = useState("");
  const [searchLoading, setSearchLoading] = useState(false),
    [searched, setSearched] = useState(false),
    [loading, setLoading] = useState(true);
  const reads = useRef(new RequestScope());
  async function load() {
    const controller = reads.current.start();
    setLoading(true);
    setSearchLoading(false);
    setError("");
    try {
      const [d, i] = await Promise.all([
        request("/api/dashboard", { signal: controller.signal }),
        request("/api/incidents?limit=8", { signal: controller.signal }),
      ]);
      if (reads.current.isCurrent(controller)) {
        setData(d);
        setIncidents(i);
        setSearched(false);
      }
    } catch (e) {
      if (reads.current.isCurrent(controller)) setError((e as Error).message);
    } finally {
      if (reads.current.isCurrent(controller)) setLoading(false);
    }
  }
  useEffect(() => {
    load();
    return () => reads.current.cancel();
  }, []);
  async function search() {
    if (!query.trim() || searchLoading || loading) return;
    const controller = reads.current.start();
    setSearchLoading(true);
    setError("");
    try {
      const records = await request(
        `/api/search/incidents?query=${encodeURIComponent(query)}&limit=5`,
        { signal: controller.signal },
      );
      if (reads.current.isCurrent(controller)) {
        setIncidents(records);
        setSearched(true);
      }
    } catch (e) {
      if (reads.current.isCurrent(controller)) setError((e as Error).message);
    } finally {
      if (reads.current.isCurrent(controller)) setSearchLoading(false);
    }
  }
  return (
    <section className="content">
      <header>
        <div>
          <p className="eyebrow">MONITORING / LIVE SYSTEM</p>
          <h1>Infrastructure overview</h1>
          <p className="muted">
            Condition, failures and response readiness from the live database.
          </p>
        </div>
        <button className="ghost" onClick={load}>
          ↻ Refresh
        </button>
      </header>
      {error && <div className="error">{error}</div>}
      <div className="cards">
        {[
          ["Assets monitored", data?.components],
          ["Open incidents", data?.open_incidents],
          ["Active work orders", data?.active_work_orders],
          ["Maintenance alerts", data?.active_alerts],
        ].map(([a, b]) => (
          <div className="card" key={String(a)}>
            <p>{a}</p>
            <strong>{b ?? "—"}</strong>
            <small>Live PostgreSQL count</small>
          </div>
        ))}
      </div>
      <div className="search">
        <div>
          <p className="eyebrow">INTELLIGENT SEARCH</p>
          <h2>Find similar incidents</h2>
        </div>
        <div className="searchbar">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="pump vibrating and leaking"
          />
          <button disabled={searchLoading || loading} onClick={search}>
            <span className={searchLoading ? "button-loading" : ""}>
              {searchLoading ? "Searching…" : "Search ↗"}
            </span>
          </button>
        </div>
      </div>
      <section className="panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">INCIDENT MONITOR</p>
            <h2>{searched ? "Search results" : "Recent incidents"}</h2>
          </div>
        </div>
        <div className="table">
          {loading ? (
            <div className="empty">Loading incidents…</div>
          ) : !incidents.length ? (
            <div className="empty">No incidents found.</div>
          ) : null}
          {!loading &&
            incidents.map((x, i) => (
              <div className="row" key={x.incident_number || i}>
                <div className="incident-id">
                  {x.incident_number}
                  <span className={`dot ${tone(x.severity)}`} />
                </div>
                <div>
                  <b>{x.title}</b>
                  <p>{x.description}</p>
                  {x.resolutions && (
                    <small className="resolution">
                      Historical resolution: {x.resolutions}
                    </small>
                  )}
                </div>
                <span className={`pill ${tone(x.status)}`}>{x.status}</span>
                <span className={`severity ${tone(x.severity)}`}>
                  {x.severity}
                </span>
              </div>
            ))}
        </div>
      </section>
    </section>
  );
}
export default function Home() {
  const [page, setPage] = useState("overview");
  const resource = resources.find((r) => r.key === page);
  return (
    <main>
      <aside>
        <div className="brand">
          <span>◆</span> InfraAssess
        </div>
        <p className="eyebrow">OPERATIONS CONSOLE</p>
        <nav>
          <button
            aria-current={page === "overview" ? "page" : undefined}
            className={page === "overview" ? "active" : ""}
            onClick={() => setPage("overview")}
          >
            Overview
          </button>
          {resources.map((r) => (
            <button
              key={r.key}
              aria-current={page === r.key ? "page" : undefined}
              className={page === r.key ? "active" : ""}
              onClick={() => setPage(r.key)}
            >
              {r.label}
            </button>
          ))}
          <button
            aria-current={page === "audit-logs" ? "page" : undefined}
            className={page === "audit-logs" ? "active" : ""}
            onClick={() => setPage("audit-logs")}
          >
            Audit history
          </button>
        </nav>
        <div className="sidebar-note">
          PostgreSQL authoritative
          <br />
          <small>Every mutation is confirmed by the API</small>
        </div>
      </aside>
      {page === "overview" ? (
        <Overview />
      ) : resource ? (
        <Management key={resource.key} resource={resource} />
      ) : (
        <Management
          key="audit-logs"
          resource={{ key: "audit-logs", label: "Audit history", fields: [] }}
        />
      )}
    </main>
  );
}
// completion action is rendered by the work-order detail form
// The work-order editor exposes the dedicated completion action inside its detail form.
