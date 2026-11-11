import { buildEditablePayload, localDateTime } from "./payload";

const payload = buildEditablePayload(
  [
    { name: "asset_tag" },
    { name: "location_id" },
    { name: "category_id" },
    { name: "name" },
    { name: "status" },
    { name: "installed_on" },
  ],
  {
    component_id: 9,
    updated_at: "now",
    id: 9,
    __id: 9,
    asset_tag: "TEST-INFRA-001",
    location_id: 2,
    category_id: 3,
    name: "Test pump",
    status: "DEGRADED",
    installed_on: "2025-01-01",
  },
);

if (
  "component_id" in payload ||
  "updated_at" in payload ||
  "id" in payload ||
  "__id" in payload
) {
  throw new Error("Read-only component fields leaked into update payload");
}
if (
  payload.asset_tag !== "TEST-INFRA-001" ||
  payload.location_id !== 2 ||
  payload.category_id !== 3
) {
  throw new Error("Editable component fields were not preserved");
}

const cleared = buildEditablePayload(
  [
    { name: "technician_id", nullable: true },
    { name: "installed_on", nullable: true },
  ],
  { technician_id: "", installed_on: "" },
);
if (cleared.technician_id !== null || cleared.installed_on !== null)
  throw Error("Nullable values must be clearable");
const converted = buildEditablePayload(
  [
    { name: "actual_cost", type: "number" },
    { name: "reported_at", type: "datetime-local" },
  ],
  { actual_cost: "12.50", reported_at: "2026-11-11T10:30" },
);
if (converted.actual_cost !== 12.5)
  throw Error("Numeric fields must send numbers");
if (converted.reported_at !== new Date("2026-11-11T10:30").toISOString())
  throw Error("Local timestamps must send ISO timestamps");
if (
  localDateTime(new Date("2026-11-11T10:30").toISOString()) !==
  "2026-11-11T10:30"
)
  throw Error("Date editor must preserve local time");

const preciseDate = new Date(2026, 10, 11, 10, 30, 45, 123);
if (localDateTime(preciseDate.toISOString()) !== "2026-11-11T10:30:45.123")
  throw Error("Date editor must retain seconds and milliseconds");
const untouched = "2026-11-11T10:30:45.123456+00:00";
const preserved = buildEditablePayload(
  [{ name: "reported_at", type: "datetime-local" }],
  { reported_at: untouched },
);
if (preserved.reported_at !== untouched)
  throw Error("Unchanged timestamps must preserve PostgreSQL microseconds");
for (const value of ["Infinity", "NaN", "not a number"]) {
  let rejected = false;
  try {
    buildEditablePayload([{ name: "actual_cost", type: "number" }], {
      actual_cost: value,
    });
  } catch {
    rejected = true;
  }
  if (!rejected)
    throw Error(`Invalid number was silently serialized: ${value}`);
}
for (const value of ["1.5", "-1", "9007199254740993"]) {
  let rejected = false;
  try {
    buildEditablePayload([{ name: "component_id", type: "number" }], {
      component_id: value,
    });
  } catch {
    rejected = true;
  }
  if (!rejected) throw Error(`Invalid ID was silently rounded: ${value}`);
}
