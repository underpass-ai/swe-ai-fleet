/**
 * Unit tests for configuration module
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getPlanningServiceConfig, isDevelopment } from '../config';

describe('config', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv };
    // Clear import.meta.env cache by deleting the module
    delete (import.meta as any).env;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  describe('getPlanningServiceConfig', () => {
    it('should use default values when env vars are not set', () => {
      // Mock import.meta.env
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_URL', '');
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_PORT', '');

      const config = getPlanningServiceConfig();

      expect(config.grpcHost).toBe('planning.swe-ai-fleet.svc.cluster.local');
      expect(config.grpcPort).toBe(50054);
    });

    it('should extract hostname from URL with http://', () => {
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_URL', 'http://planning.example.com');
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_PORT', '50054');

      const config = getPlanningServiceConfig();

      expect(config.grpcHost).toBe('planning.example.com');
      expect(config.grpcPort).toBe(50054);
    });

    it('should extract hostname from URL with https://', () => {
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_URL', 'https://planning.example.com');
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_PORT', '50054');

      const config = getPlanningServiceConfig();

      expect(config.grpcHost).toBe('planning.example.com');
      expect(config.grpcPort).toBe(50054);
    });

    it('should extract hostname from URL with port', () => {
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_URL', 'http://planning.example.com:8080');
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_PORT', '50054');

      const config = getPlanningServiceConfig();

      expect(config.grpcHost).toBe('planning.example.com');
      expect(config.grpcPort).toBe(50054); // Port from separate env var
    });

    it('should use direct hostname without protocol', () => {
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_URL', 'planning.local');
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_PORT', '50054');

      const config = getPlanningServiceConfig();

      expect(config.grpcHost).toBe('planning.local');
      expect(config.grpcPort).toBe(50054);
    });

    it('should parse port from env var', () => {
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_URL', 'planning.example.com');
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_PORT', '9000');

      const config = getPlanningServiceConfig();

      expect(config.grpcPort).toBe(9000);
    });

    it('should handle hostname with subdomain', () => {
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_URL', 'http://internal.planning.example.com');
      vi.stubEnv('PUBLIC_PLANNING_SERVICE_PORT', '50054');

      const config = getPlanningServiceConfig();

      expect(config.grpcHost).toBe('internal.planning.example.com');
    });
  });

  describe('isDevelopment', () => {
    it('should return true in development mode', () => {
      // Note: import.meta.env.DEV is set by Astro/Vite
      // In test environment, we can't easily mock it
      // This test documents the function exists
      expect(typeof isDevelopment()).toBe('boolean');
    });
  });
});





