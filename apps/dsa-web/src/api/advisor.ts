import apiClient from './index';
import { toCamelCase } from './utils';
import type {
  AdvisorRunRequest,
  AdvisorRunResponse,
  AdvisorSnapshotListResponse,
  AdvisorStatusResponse,
} from '../types/advisor';

function toRunPayload(payload: AdvisorRunRequest): Record<string, unknown> {
  return {
    stage: payload.stage,
    send_notification: payload.sendNotification,
  };
}

export const advisorApi = {
  async getStatus(): Promise<AdvisorStatusResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/advisor/status');
    return toCamelCase<AdvisorStatusResponse>(response.data);
  },

  async listSnapshots(limit = 20): Promise<AdvisorSnapshotListResponse> {
    const response = await apiClient.get<Record<string, unknown>>('/api/v1/advisor/snapshots', {
      params: { limit },
    });
    return toCamelCase<AdvisorSnapshotListResponse>(response.data);
  },

  async runStage(payload: AdvisorRunRequest): Promise<AdvisorRunResponse> {
    const response = await apiClient.post<Record<string, unknown>>(
      '/api/v1/advisor/run',
      toRunPayload(payload),
    );
    return toCamelCase<AdvisorRunResponse>(response.data);
  },

  async notifyTest(): Promise<AdvisorRunResponse> {
    const response = await apiClient.post<Record<string, unknown>>('/api/v1/advisor/notify-test');
    return toCamelCase<AdvisorRunResponse>(response.data);
  },
};
