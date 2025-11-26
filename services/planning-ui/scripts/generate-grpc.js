#!/usr/bin/env node
/**
 * Generate gRPC TypeScript/JavaScript code from .proto files
 * This script runs during Docker build (context: /app)
 */

import { execSync } from 'child_process';
import { existsSync, mkdirSync } from 'fs';

// Docker build context: /app (project root)
const PROJECT_ROOT = '/app';
const PROTO_FILE = `${PROJECT_ROOT}/specs/fleet/planning/v2/planning.proto`;
const OUT_DIR = `${PROJECT_ROOT}/gen/fleet/planning/v2`;
const PROTO_DIR = `${PROJECT_ROOT}/specs`;
const PROTOC_BIN = `${PROJECT_ROOT}/node_modules/.bin/grpc_tools_node_protoc`;
const PLUGIN_PATH = `${PROJECT_ROOT}/node_modules/.bin/grpc_tools_node_protoc_plugin`;

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
} catch (error) {
  console.error('❌ Failed to generate gRPC code:', error.message);
  process.exit(1);
}
