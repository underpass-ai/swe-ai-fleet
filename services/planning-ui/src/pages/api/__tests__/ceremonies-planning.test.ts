/**
 * Unit tests for GET /api/ceremonies/planning
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as grpcClientModule from '../../../lib/grpc-client';
import * as grpcRequestBuilders from '../../../lib/grpc-request-builders';

vi.mock('../../../lib/grpc-client');
vi.mock('../../../lib/grpc-request-builders');

const mockBuildListPlanningCeremoniesRequest = vi.mocked(
  grpcRequestBuilders.buildListPlanningCeremoniesRequest
);

describe('GET /api/ceremonies/planning', () => {
  let mockClient: any;
  let mockGetPlanningClient: any;
  let mockPromisifyGrpcCall: any;
  let mockGrpcErrorToHttpStatus: any;
  let mockIsServiceError: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockClient = {
      listPlanningCeremonies: vi.fn(),
    };

    mockGetPlanningClient = vi.fn().mockResolvedValue(mockClient);
    mockPromisifyGrpcCall = vi.fn();
    mockGrpcErrorToHttpStatus = vi.fn((error: grpc.ServiceError) => {
      if (error.code === grpc.status.INVALID_ARGUMENT) return 400;
      if (error.code === grpc.status.UNAVAILABLE) return 503;
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

    mockBuildListPlanningCeremoniesRequest.mockImplementation((payload) => payload as any);

    vi.mocked(grpcClientModule.getPlanningClient).mockImplementation(mockGetPlanningClient);
    vi.mocked(grpcClientModule.promisifyGrpcCall).mockImplementation(mockPromisifyGrpcCall);
    vi.mocked(grpcClientModule.grpcErrorToHttpStatus).mockImplementation(mockGrpcErrorToHttpStatus);
    vi.mocked(grpcClientModule.isServiceError).mockImplementation(mockIsServiceError);
  });

  it('lists planning ceremonies successfully', async () => {
    const { GET } = await import('../ceremonies/planning/index');

    mockPromisifyGrpcCall.mockResolvedValue({
      success: true,
      total_count: 1,
      ceremonies: [
        {
          instance_id: 'cer-1:story-1',
          ceremony_id: 'cer-1',
          story_id: 'story-1',
          definition_name: 'e2e_multi_step',
          current_state: 'in_progress',
          status: 'IN_PROGRESS',
          correlation_id: 'corr-1',
          step_status: { deliberate: 'COMPLETED' },
          step_outputs: {},
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:01:00Z',
        },
      ],
    });

    const url = new URL('http://localhost/api/ceremonies/planning?status=IN_PROGRESS&limit=20&offset=0');
    const response = await GET({ url } as any);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.success).toBe(true);
    expect(data.total_count).toBe(1);
    expect(data.ceremonies[0].instance_id).toBe('cer-1:story-1');
    expect(mockBuildListPlanningCeremoniesRequest).toHaveBeenCalledWith({
      limit: 20,
      offset: 0,
      state_filter: 'IN_PROGRESS',
      definition_filter: undefined,
      story_id: undefined,
    });
  });

  it('maps gRPC ServiceError to HTTP status', async () => {
    const { GET } = await import('../ceremonies/planning/index');

    const error: grpc.ServiceError = {
      code: grpc.status.UNAVAILABLE,
      message: 'processor unavailable',
      details: '',
      name: 'ServiceError',
    };
    mockPromisifyGrpcCall.mockRejectedValue(error);
    mockIsServiceError.mockReturnValue(true);
    mockGrpcErrorToHttpStatus.mockReturnValue(503);

    const url = new URL('http://localhost/api/ceremonies/planning');
    const response = await GET({ url } as any);
    const data = await response.json();

    expect(response.status).toBe(503);
    expect(data.success).toBe(false);
    expect(data.message).toBe('processor unavailable');
  });

  it('handles unknown errors', async () => {
    const { GET } = await import('../ceremonies/planning/index');

    mockPromisifyGrpcCall.mockRejectedValue(new Error('Unexpected failure'));
    mockIsServiceError.mockReturnValue(false);

    const url = new URL('http://localhost/api/ceremonies/planning');
    const response = await GET({ url } as any);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Unexpected failure');
  });
});
