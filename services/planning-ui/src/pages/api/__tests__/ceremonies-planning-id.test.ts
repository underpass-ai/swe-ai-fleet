/**
 * Unit tests for GET /api/ceremonies/planning/[id]
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as grpcClientModule from '../../../lib/grpc-client';
import * as grpcRequestBuilders from '../../../lib/grpc-request-builders';

vi.mock('../../../lib/grpc-client');
vi.mock('../../../lib/grpc-request-builders');

const mockBuildGetPlanningCeremonyRequest = vi.mocked(
  grpcRequestBuilders.buildGetPlanningCeremonyRequest
);

describe('GET /api/ceremonies/planning/[id]', () => {
  let mockClient: any;
  let mockGetPlanningClient: any;
  let mockPromisifyGrpcCall: any;
  let mockGrpcErrorToHttpStatus: any;
  let mockIsServiceError: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockClient = {
      getPlanningCeremony: vi.fn(),
    };

    mockGetPlanningClient = vi.fn().mockResolvedValue(mockClient);
    mockPromisifyGrpcCall = vi.fn();
    mockGrpcErrorToHttpStatus = vi.fn((error: grpc.ServiceError) => {
      if (error.code === grpc.status.NOT_FOUND) return 404;
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

    mockBuildGetPlanningCeremonyRequest.mockImplementation((payload) => payload as any);

    vi.mocked(grpcClientModule.getPlanningClient).mockImplementation(mockGetPlanningClient);
    vi.mocked(grpcClientModule.promisifyGrpcCall).mockImplementation(mockPromisifyGrpcCall);
    vi.mocked(grpcClientModule.grpcErrorToHttpStatus).mockImplementation(mockGrpcErrorToHttpStatus);
    vi.mocked(grpcClientModule.isServiceError).mockImplementation(mockIsServiceError);
  });

  it('gets planning ceremony successfully', async () => {
    const { GET } = await import('../ceremonies/planning/[id]');

    mockPromisifyGrpcCall.mockResolvedValue({
      success: true,
      ceremony: {
        instance_id: 'cer-1:story-1',
        definition_name: 'e2e_multi_step',
        current_state: 'in_progress',
        status: 'IN_PROGRESS',
        correlation_id: 'corr-1',
        step_status: { deliberate: 'COMPLETED' },
        step_outputs: {},
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:01:00Z',
      },
    });

    const response = await GET({ params: { id: 'cer-1%3Astory-1' } } as any);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.success).toBe(true);
    expect(data.ceremony.instance_id).toBe('cer-1:story-1');
    expect(data.ceremony.ceremony_id).toBe('cer-1');
    expect(data.ceremony.story_id).toBe('story-1');
    expect(mockBuildGetPlanningCeremonyRequest).toHaveBeenCalledWith({
      instance_id: 'cer-1:story-1',
    });
  });

  it('returns 400 when id is missing', async () => {
    const { GET } = await import('../ceremonies/planning/[id]');
    const response = await GET({ params: {} } as any);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Instance ID required');
  });

  it('returns 404 when ceremony is not found', async () => {
    const { GET } = await import('../ceremonies/planning/[id]');

    mockPromisifyGrpcCall.mockResolvedValue({
      success: false,
      message: 'not found',
    });

    const response = await GET({ params: { id: 'missing' } } as any);
    const data = await response.json();

    expect(response.status).toBe(404);
    expect(data.success).toBe(false);
    expect(data.message).toBe('not found');
  });
});
