export type EditableField = { name: string; type?: string; nullable?: boolean };

/** Copies only fields declared by the request form/schema; response metadata is excluded. */
export function buildEditablePayload(
  fields: EditableField[],
  values: Record<string, unknown>,
): Record<string, unknown> {
  return Object.fromEntries(
    fields.flatMap((field) => {
      const value = values[field.name];
      if (value === undefined) return [];
      if (value === "") return field.nullable ? [[field.name, null]] : [];
      if (["estimated_cost", "actual_cost", "reading_value", "min_value", "max_value"].includes(field.name) && value !== null) {
        const decimal = String(value);
        if (!/^-?\d+(\.\d+)?$/.test(decimal)) throw Error(`${field.name} must be a decimal number.`);
        return [[field.name, decimal]];
      }
      if (field.type === "number" && value !== null) {
        const number = Number(value);
        if (!Number.isFinite(number))
          throw Error(
            `${field.name.replace(/_/g, " ")} must be a finite number.`,
          );
        if (
          field.name.endsWith("_id") &&
          (!Number.isSafeInteger(number) || number <= 0)
        ) {
          throw Error(
            `${field.name.replace(/_/g, " ")} must be a positive integer.`,
          );
        }
        return [[field.name, number]];
      }
      if (field.type === "datetime-local" && value) {
        // Unchanged API timestamps can have microseconds that JavaScript Date
        // cannot represent. Preserve them when editing unrelated fields.
        const text = String(value);
        if (/(?:Z|[+-]\d{2}:\d{2})$/i.test(text)) return [[field.name, text]];
        return [[field.name, new Date(text).toISOString()]];
      }
      return [[field.name, value]];
    }),
  );
}

/** datetime-local controls use local wall-clock time, while the API uses ISO timestamps. */
export function localDateTime(value: unknown): string {
  if (!value) return "";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return "";
  const pad = (number: number) => String(number).padStart(2, "0");
  const minute = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  if (!date.getSeconds() && !date.getMilliseconds()) return minute;
  const fraction = date.getMilliseconds()
    ? `.${String(date.getMilliseconds()).padStart(3, "0")}`
    : "";
  return `${minute}:${pad(date.getSeconds())}${fraction}`;
}
