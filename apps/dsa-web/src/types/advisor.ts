export interface AdvisorStageItem {
  id: string;
  name: string;
  time: string;
  objective: string;
  pushPolicy: string;
}

export interface AdvisorCandidateItem {
  type: string;
  status: string;
  rule: string;
}

export interface AdvisorNotificationChannel {
  channel: string;
  success: boolean;
  errorCode?: string | null;
  latencyMs?: number | null;
}

export interface AdvisorNotificationResult {
  success: boolean;
  status: string;
  message?: string | null;
  channels: AdvisorNotificationChannel[];
}

export interface AdvisorSnapshotItem {
  id: string;
  stage: string;
  stageName: string;
  generatedAt: string;
  title: string;
  actionLevel: string;
  marketMode: string;
  primaryTheme: string;
  summary: string;
  candidates: AdvisorCandidateItem[];
  watchpoints: string[];
  riskControls: string[];
  nextActions: string[];
  markdown: string;
  notification?: AdvisorNotificationResult | null;
}

export interface AdvisorStatusResponse {
  enabled: boolean;
  mode: string;
  notificationReady: boolean;
  notificationChannels: string[];
  stages: AdvisorStageItem[];
  nextStage: AdvisorStageItem;
  latestSnapshot?: AdvisorSnapshotItem | null;
}

export interface AdvisorSnapshotListResponse {
  items: AdvisorSnapshotItem[];
}

export interface AdvisorRunRequest {
  stage: string;
  sendNotification: boolean;
}

export interface AdvisorRunResponse {
  snapshot: AdvisorSnapshotItem;
  notification?: AdvisorNotificationResult | null;
}
