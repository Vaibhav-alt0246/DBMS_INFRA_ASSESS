export type EditableField = {name: string};

/** Copies only fields declared by the request form/schema; response metadata is excluded. */
export function buildEditablePayload(fields: EditableField[], values: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(fields.filter(field => values[field.name] !== '' && values[field.name] !== undefined).map(field => [field.name, values[field.name]]));
}
