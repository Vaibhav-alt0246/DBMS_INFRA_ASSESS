import {buildEditablePayload} from './payload';

const payload = buildEditablePayload(
  [{name: 'asset_tag'}, {name: 'location_id'}, {name: 'category_id'}, {name: 'name'}, {name: 'status'}, {name: 'installed_on'}],
  {component_id: 9, updated_at: 'now', id: 9, __id: 9, asset_tag: 'TEST-INFRA-001', location_id: 2, category_id: 3, name: 'Test pump', status: 'DEGRADED', installed_on: '2025-01-01'},
);

if ('component_id' in payload || 'updated_at' in payload || 'id' in payload || '__id' in payload) {
  throw new Error('Read-only component fields leaked into update payload');
}
if (payload.asset_tag !== 'TEST-INFRA-001' || payload.location_id !== 2 || payload.category_id !== 3) {
  throw new Error('Editable component fields were not preserved');
}
