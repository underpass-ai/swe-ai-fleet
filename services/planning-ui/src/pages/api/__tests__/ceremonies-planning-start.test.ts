/**
 * Unit tests for POST /api/ceremonies/planning/start
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as grpcClientModule from '../../../lib/grpc-client';
import * as grpcRequestBuilders from '../../../lib/grpc-request-builders';

vi.mock('../../../lib/grpc-client');
vi.mock('../../../lib/grpc-request-builders');

const mockBuildStartPlanningCeremonyRequest = vi.mocked(
  grpcRequestBuilders.buildStartPlanningCeremonyRequest
);

describe('POST /api/ceremonies/planning/start', () => {
  let mockClient: any;
  let mockGetPlanningClient: any;
  let mockPromisifyGrpcCall: any;
  let mockGrpcErrorToHttpStatus: any;
  let mockIsServiceError: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockClient = {
      startPlanningCeremony: vi.fn(),
    };

    mockGetPlanningClient = vi.fn().mockResolvedValue(mockClient);
    mockPromisifyGrpcCall = vi.fn();
    mockGrpcErrorToHttpStatus = vi.fn((error: grpc.ServiceError) => {
      if (error.code === grpc.status.INVALID_ARGUMENT) return 400;
      if (error.code === grpc.status.FAILED_PRECONDITION) return 412;
      return 500;
    });
    mockIsServiceError = vi.fn((error: unknown) => {
      return (
        typeof error === 'object' &&
        error !== null &&
        'code' in error &&
        typeof (error as any).code === 'number'
      );
    });

    mockBuildStartPlanningCeremonyRequest.mockImplementation((payload) => payload as any);

    vi.mocked(grpcClientModule.getPlanningClient).mockImplementation(mockGetPlanningClient);
    vi.mocked(grpcClientModule.promisifyGrpcCall).mockImplementation(mockPromisifyGrpcCall);
    vi.mocked(grpcClientModule.grpcErrorToHttpStatus).mockImplementation(mockGrpcErrorToHttpStatus);
    vi.mocked(grpcClientModule.isServiceError).mockImplementation(mockIsServiceError);
  });

  it('starts planning ceremony successfully', async () => {
    const { POST } = await import('../ceremonies/planning/start');

    mockPromisifyGrpcCall.mockResolvedValue({
      instance_id: 'inst-123',
      status: 'accepted',
      message: 'Planning ceremony started',
    });

    const request = new Request('http://localhost/api/ceremonies/planning/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ceremony_id: 'ceremony-123',
        definition_name: 'e2e_multi_step',
        story_id: 'story-1',
        requested_by: 'planner@example.com',
        step_ids: ['deliberate'],
        correlation_id: 'corr-1',
        inputs: {
          input_data: '{"source":"planning-ui"}',
        },
      }),
    });

    const response = await POST({ request } as any);
    const data = await response.json();

    expect(response.status).toBe(202);
    expect(data.success).toBe(true);
    expect(data.instance_id).toBe('inst-123');
    expect(data.ceremony_id).toBe('ceremony-123');

    expect(mockBuildStartPlanningCeremonyRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        ceremony_id: 'ceremony-123',
        definition_name: 'e2e_multi_step',
        story_id: 'story-1',
        requested_by: 'planner@example.com',
        step_ids: ['deliberate'],
        correlation_id: 'corr-1',
        inputs: {
          input_data: '{"source":"planning-ui"}',
        },
      })
    );
  });

  it('auto-generates ceremony_id when not provided', async () => {
    const { POST } = await import('../ceremonies/planning/start');

    mockPromisifyGrpcCall.mockResolvedValue({
      instance_id: 'inst-123',
      status: 'accepted',
      message: 'Planning ceremony started',
    });

    const request = new Request('http://localhost/api/ceremonies/planning/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        definition_name: 'e2e_multi_step',
        story_id: 'story-1',
        requested_by: 'planner@example.com',
        step_ids: ['deliberate'],
      }),
    });

    const response = await POST({ request } as any);
    const data = await response.json();

    expect(response.status).toBe(202);
    expect(data.ceremony_id).toMatch(/^planning-e2e_multi_step-/);

    expect(mockBuildStartPlanningCeremonyRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        ceremony_id: expect.stringMatching(/^planning-e2e_multi_step-/),
      })
    );
  });

  it('rejects missing definition_name', async () => {
    const { POST } = await import('../ceremonies/planning/start');

    const request = new Request('http://localhost/api/ceremonies/planning/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        story_id: 'story-1',
        requested_by: 'planner@example.com',
        step_ids: ['deliberate'],
      }),
    });

    const response = await POST({ request } as any);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.success).toBe(false);
    expect(data.message).toBe('definition_name is required');
  });

  it('rejects missing story_id', async () => {
    const { POST } = await import('../ceremonies/planning/start');

    const request = new Request('http://localhost/api/ceremonies/planning/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        definition_name: 'e2e_multi_step',
        requested_by: 'planner@example.com',
        step_ids: ['deliberate'],
      }),
    });

    const response = await POST({ request } as any);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.success).toBe(false);
    expect(data.message).toBe('story_id is required');
  });

  it('rejects missing requested_by', async () => {
    const { POST } = await import('../ceremonies/planning/start');

    const request = new Request('http://localhost/api/ceremonies/planning/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        definition_name: 'e2e_multi_step',
        story_id: 'story-1',
        step_ids: ['deliberate'],
      }),
    });

    const response = await POST({ request } as any);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.success).toBe(false);
    expect(data.message).toBe('requested_by is required');
  });

  it('rejects empty step_ids', async () => {
    const { POST } = await import('../ceremonies/planning/start');

    const request = new Request('http://localhost/api/ceremonies/planning/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        definition_name: 'e2e_multi_step',
        story_id: 'story-1',
        requested_by: 'planner@example.com',
        step_ids: [],
      }),
    });

    const response = await POST({ request } as any);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.success).toBe(false);
    expect(data.message).toBe('step_ids is required and cannot be empty');
  });

  it('rejects invalid inputs shape', async () => {
    const { POST } = await import('../ceremonies/planning/start');

    const request = new Request('http://localhost/api/ceremonies/planning/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        definition_name: 'e2e_multi_step',
        story_id: 'story-1',
        requested_by: 'planner@example.com',
        step_ids: ['deliberate'],
        inputs: ['invalid'],
      }),
    });

    const response = await POST({ request } as any);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.success).toBe(false);
    expect(data.message).toBe('inputs must be a JSON object (key/value)');
  });

  it('maps gRPC ServiceError to HTTP status', async () => {
    const { POST } = await import('../ceremonies/planning/start');

    const error: grpc.ServiceError = {
      code: grpc.status.FAILED_PRECONDITION,
      message: 'Planning Ceremony Processor not configured',
      details: '',
      name: 'ServiceError',
    };
    mockPromisifyGrpcCall.mockRejectedValue(error);
    mockIsServiceError.mockReturnValue(true);
    mockGrpcErrorToHttpStatus.mockReturnValue(412);

    const request = new Request('http://localhost/api/ceremonies/planning/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        definition_name: 'e2e_multi_step',
        story_id: 'story-1',
        requested_by: 'planner@example.com',
        step_ids: ['deliberate'],
      }),
    });

    const response = await POST({ request } as any);
    const data = await response.json();

    expect(response.status).toBe(412);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Planning Ceremony Processor not configured');
  });

  it('handles unknown errors', async () => {
    const { POST } = await import('../ceremonies/planning/start');

    mockPromisifyGrpcCall.mockRejectedValue(new Error('Unexpected failure'));
    mockIsServiceError.mockReturnValue(false);

    const request = new Request('http://localhost/api/ceremonies/planning/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        definition_name: 'e2e_multi_step',
        story_id: 'story-1',
        requested_by: 'planner@example.com',
        step_ids: ['deliberate'],
      }),
    });

    const response = await POST({ request } as any);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Unexpected failure');
  });
});
