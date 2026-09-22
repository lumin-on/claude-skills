// Subagent 출력 JSON을 선언형 JSON Schema로 검증한다.
//
// 왜 필요한가:
//   scripts/core.mjs 는 검증 규칙(필수 키, status 허용값, null↔판단 보류 짝,
//   evidence 비어 있지 않음 …)을 JS 코드에 하드코딩해 두었다. 규칙이 늘어날수록
//   코드가 길어지고 어떤 규칙이 적용 중인지 읽기 어려웠다.
//   ajv (https://github.com/ajv-validator/ajv) 로 규칙을 schemas/*.json 에 선언해
//   사람이 읽을 수 있게 분리하고, 위반 위치를 JSON Pointer 로 정확히 얻는다.
//
// 사용:
//   node scripts/validate_schema.mjs --schema schemas/analyst-output.schema.json \
//        --json runs/test-03/chunks/c1-analyst-output.json [--json ...] [--out report.json]
//
// 종료 코드: 위반이 있으면 1

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let Ajv;
try {
  Ajv = require('ajv');
} catch {
  console.error('ajv 가 필요합니다: npm install ajv  (https://github.com/ajv-validator/ajv)');
  process.exit(2);
}

const argv = process.argv.slice(2);
const get = (flag) => { const i = argv.indexOf(flag); return i >= 0 ? argv[i + 1] : null; };
const getAll = (flag) => argv.reduce((acc, v, i) => (v === flag ? [...acc, argv[i + 1]] : acc), []);

const schemaPath = get('--schema');
const jsonPaths = getAll('--json');
const outPath = get('--out');
if (!schemaPath || jsonPaths.length === 0) {
  console.error('사용: node scripts/validate_schema.mjs --schema <schema.json> --json <a.json> [--json <b.json>] [--out <report.json>]');
  process.exit(2);
}

const ajv = new Ajv({ allErrors: true, strict: false, allowUnionTypes: true });
const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));
const validate = ajv.compile(schema);

const results = [];
let totalErrors = 0;
for (const p of jsonPaths) {
  const data = JSON.parse(fs.readFileSync(p, 'utf8'));
  const ok = validate(data);
  const errors = ok ? [] : validate.errors.map(e => ({
    at: e.instancePath || '(root)',
    rule: e.keyword,
    message: e.message,
    params: e.params,
  }));
  totalErrors += errors.length;
  results.push({ file: p.replace(/\\/g, '/'), valid: ok, error_count: errors.length, errors });
  const label = path.basename(p);
  console.log(`${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : `  위반 ${errors.length}건`}`);
  for (const e of errors.slice(0, 10)) console.log(`       ${e.at}  ${e.rule}: ${e.message}`);
}

const report = {
  schema: schemaPath.replace(/\\/g, '/'),
  schema_id: schema.$id ?? null,
  tool: 'ajv-validator/ajv (https://github.com/ajv-validator/ajv)',
  ajv_version: require('ajv/package.json').version,
  files_checked: results.length,
  total_errors: totalErrors,
  results,
  generated_at: new Date().toISOString(),
};
if (outPath) fs.writeFileSync(outPath, JSON.stringify(report, null, 2));

console.log(`\n스키마 ${schema.$id ?? path.basename(schemaPath)} — 파일 ${results.length}개, 위반 ${totalErrors}건`);
process.exit(totalErrors ? 1 : 0);
