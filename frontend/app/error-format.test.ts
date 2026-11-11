import {formatApiError} from './error-format';

const formatted = formatApiError({detail: [
  {loc: ['body', 'health_score'], msg: 'Input should be less than or equal to 100'},
  {loc: ['body', 'component_id'], msg: 'Field required'},
]});

if (formatted !== 'body.health_score: Input should be less than or equal to 100 • body.component_id: Field required') {
  throw new Error(`Validation formatter regression: ${formatted}`);
}
