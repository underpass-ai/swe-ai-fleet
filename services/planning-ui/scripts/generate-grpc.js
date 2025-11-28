#!/usr/bin/env node
/**
 * Generate gRPC TypeScript/JavaScript code from .proto files
 * This script runs during Docker build (context: /app)
 */

import { execSync } from 'child_process';
import { existsSync, mkdirSync, writeFileSync } from 'fs';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Resolve project root even when script runs outside Docker build context
const PROJECT_ROOT = resolve(__dirname, '..');
const MONOREPO_ROOT = resolve(PROJECT_ROOT, '..', '..');
const SPEC_CANDIDATES = [
  `${PROJECT_ROOT}/specs`,
  `${MONOREPO_ROOT}/specs`,
];

const resolvedSpecDir = SPEC_CANDIDATES.find((candidate) =>
  existsSync(`${candidate}/fleet/planning/v2/planning.proto`)
);

if (!resolvedSpecDir) {
  console.error('❌ Unable to locate specs/fleet/planning/v2/planning.proto in known paths.');
  process.exit(1);
}

const PROTO_FILE = `${resolvedSpecDir}/fleet/planning/v2/planning.proto`;
const OUT_DIR = `${PROJECT_ROOT}/gen/fleet/planning/v2`;
const PROTO_DIR = resolvedSpecDir;
const PROTOC_BIN = `${PROJECT_ROOT}/node_modules/.bin/grpc_tools_node_protoc`;
const PLUGIN_PATH = `${PROJECT_ROOT}/node_modules/.bin/grpc_tools_node_protoc_plugin`;
const OUT_PACKAGE_FILE = `${OUT_DIR}/package.json`;

console.log('🔧 Generating gRPC code from protobuf...');
console.log(`   Proto file: ${PROTO_FILE}`);
console.log(`   Output dir: ${OUT_DIR}`);

// Create output directory
if (!existsSync(OUT_DIR)) {
  mkdirSync(OUT_DIR, { recursive: true });
}

// Check if proto file exists
if (!existsSync(PROTO_FILE)) {
  console.error(`❌ Proto file not found: ${PROTO_FILE}`);
  process.exit(1);
}

try {
  // Generate JavaScript code using grpc-tools
  // This generates:
  // - planning_pb.js (protobuf messages)
  // - planning_grpc_pb.js (gRPC service client)
  execSync(
    `${PROTOC_BIN} \
      --js_out=import_style=commonjs,binary:${OUT_DIR} \
      --grpc_out=grpc_js:${OUT_DIR} \
      --plugin=protoc-gen-grpc=${PLUGIN_PATH} \
      -I ${PROTO_DIR}/fleet/planning/v2 \
      -I ${PROTO_DIR} \
      ${PROTO_FILE}`,
    { stdio: 'inherit', cwd: PROJECT_ROOT }
  );

  console.log('✅ gRPC code generated successfully');
  console.log(`   Output directory: ${OUT_DIR}`);

  // Ensure generated files are treated as CommonJS despite the root project using ESM
  writeFileSync(
    OUT_PACKAGE_FILE,
    JSON.stringify(
      {
        name: '@generated/fleet-planning-v2',
        private: true,
        type: 'commonjs',
      },
      null,
      2
    )
  );
  console.log(`   Created CommonJS boundary at ${OUT_PACKAGE_FILE}`);
} catch (error) {
  console.error('❌ Failed to generate gRPC code:', error.message);
  process.exit(1);
}
