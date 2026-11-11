from dataclasses import dataclass

INCIDENT_DOCUMENT_SQL = """
SELECT i.incident_id, i.incident_number, i.title, i.description, i.reported_at, i.severity, i.status,
       COALESCE(comp.components, '') AS components, COALESCE(resolutions.resolutions, '') AS resolutions
FROM incident i
LEFT JOIN (
 SELECT ic.incident_id, string_agg(DISTINCT c.name || ' [' || c.asset_tag || '] / ' || cc.name, '; ' ORDER BY c.name || ' [' || c.asset_tag || '] / ' || cc.name) AS components
 FROM incident_component ic JOIN component c USING (component_id) JOIN component_category cc USING (category_id)
 GROUP BY ic.incident_id
) comp USING (incident_id)
LEFT JOIN (
 SELECT w.incident_id, string_agg(DISTINCT concat_ws(' | ', w.completion_notes, m.action_taken, m.outcome), '; ' ORDER BY concat_ws(' | ', w.completion_notes, m.action_taken, m.outcome)) AS resolutions
 FROM work_order w LEFT JOIN maintenance_record m USING (work_order_id)
 WHERE w.incident_id IS NOT NULL GROUP BY w.incident_id
) resolutions USING (incident_id)
ORDER BY i.incident_id
"""

@dataclass(frozen=True)
class IncidentDocument:
    incident_id: int; incident_number: str; title: str; description: str; reported_at: object
    severity: str; status: str; components: str; resolutions: str
    @property
    def text(self):
        return "\n".join((f"Incident {self.incident_number}", f"Title: {self.title}", f"Description: {self.description}", f"Severity: {self.severity}", f"Status: {self.status}", f"Affected components: {self.components or 'None documented'}", f"Documented resolutions: {self.resolutions or 'None documented'}"))

def fetch_incidents(connection):
    with connection.cursor() as cur:
        cur.execute(INCIDENT_DOCUMENT_SQL)
        return [IncidentDocument(*row) for row in cur.fetchall()]

def fetch_incidents_by_ids(connection, ids):
    if not ids: return {}
    with connection.cursor() as cur:
        cur.execute("""
        SELECT i.incident_id, i.incident_number, i.title, i.description, i.severity, i.status,
               COALESCE(r.resolutions, '') AS resolutions
        FROM incident i LEFT JOIN (
          SELECT w.incident_id, string_agg(DISTINCT concat_ws(' | ', w.completion_notes, m.action_taken, m.outcome), '; ') AS resolutions
          FROM work_order w LEFT JOIN maintenance_record m USING (work_order_id)
          WHERE w.incident_id = ANY(%s) GROUP BY w.incident_id
        ) r USING (incident_id) WHERE i.incident_id = ANY(%s)
        """, (ids, ids))
        cols = [d.name for d in cur.description]
        return {row[0]: dict(zip(cols, row)) for row in cur.fetchall()}
