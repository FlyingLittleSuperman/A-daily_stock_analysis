import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AdvisorPage from '../AdvisorPage';

const { getStatus, listSnapshots, runStage, notifyTest } = vi.hoisted(() => ({
  getStatus: vi.fn(),
  listSnapshots: vi.fn(),
  runStage: vi.fn(),
  notifyTest: vi.fn(),
}));

vi.mock('../../api/advisor', () => ({
  advisorApi: {
    getStatus,
    listSnapshots,
    runStage,
    notifyTest,
  },
}));

const stage = {
  id: 'open_confirm',
  name: '开盘主线确认',
  time: '10:00',
  objective: '判断题材是真启动还是短暂拉升。',
  pushPolicy: '只在关键变化时推送。',
};

const snapshot = {
  id: 'snap-1',
  stage: 'open_confirm',
  stageName: '开盘主线确认',
  generatedAt: '2026-07-04T10:00:00',
  title: '开盘主线确认 - AI投顾值班快照',
  actionLevel: '条件参与',
  marketMode: '确认主线',
  primaryTheme: '等待数据确认的当日主线',
  summary: '开盘主线确认已生成。',
  candidates: [
    { type: '龙头', status: '等待确认', rule: '最先启动、最强封单。' },
  ],
  watchpoints: ['板块是否连续强于指数。'],
  riskControls: ['不因单条新闻直接追高。'],
  nextActions: ['执行八维+紫苏叶+缠论组合复核。'],
  markdown: '# 开盘主线确认',
  notification: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  getStatus.mockResolvedValue({
    enabled: true,
    mode: 'advisor_copilot_mvp',
    notificationReady: true,
    notificationChannels: ['feishu'],
    stages: [stage],
    nextStage: stage,
    latestSnapshot: snapshot,
  });
  listSnapshots.mockResolvedValue({ items: [snapshot] });
  runStage.mockResolvedValue({
    snapshot: { ...snapshot, id: 'snap-2', summary: '新的值班快照。' },
    notification: null,
  });
  notifyTest.mockResolvedValue({
    snapshot: {
      ...snapshot,
      id: 'snap-3',
      notification: { success: true, status: 'sent', channels: [{ channel: 'feishu', success: true }] },
    },
    notification: { success: true, status: 'sent', channels: [{ channel: 'feishu', success: true }] },
  });
});

describe('AdvisorPage', () => {
  it('loads status, latest snapshot and schedule stages', async () => {
    render(<AdvisorPage />);

    expect(await screen.findByText('AI投顾值班室')).toBeInTheDocument();
    expect(screen.getAllByText('开盘主线确认').length).toBeGreaterThan(0);
    expect(screen.getAllByText('条件参与').length).toBeGreaterThan(0);
    expect(screen.getByText('板块是否连续强于指数。')).toBeInTheDocument();
  });

  it('runs the selected advisor stage', async () => {
    render(<AdvisorPage />);

    fireEvent.click(await screen.findByRole('button', { name: /运行阶段/ }));

    await waitFor(() => expect(runStage).toHaveBeenCalledWith({
      stage: 'auto',
      sendNotification: false,
    }));
    expect((await screen.findAllByText('新的值班快照。')).length).toBeGreaterThan(0);
  });

  it('sends a notification test using the latest snapshot', async () => {
    render(<AdvisorPage />);

    fireEvent.click(await screen.findByRole('button', { name: /推送测试/ }));

    await waitFor(() => expect(notifyTest).toHaveBeenCalled());
    expect(await screen.findByText('推送测试成功')).toBeInTheDocument();
    expect(screen.getAllByText('sent · 1/1').length).toBeGreaterThan(0);
  });
});
