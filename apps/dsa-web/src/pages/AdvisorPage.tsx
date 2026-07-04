import type React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { BellRing, Clock3, Play, Radar, RefreshCw, Send, ShieldCheck } from 'lucide-react';
import { advisorApi } from '../api/advisor';
import { getParsedApiError, type ParsedApiError } from '../api/error';
import {
  ApiErrorAlert,
  AppPage,
  Badge,
  Button,
  Card,
  EmptyState,
  InlineAlert,
  Loading,
  PageHeader,
  StatCard,
} from '../components/common';
import type {
  AdvisorNotificationResult,
  AdvisorSnapshotItem,
  AdvisorStageItem,
  AdvisorStatusResponse,
} from '../types/advisor';

function formatDateTime(value?: string | null): string {
  if (!value) return '--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function notificationText(result?: AdvisorNotificationResult | null): string {
  if (!result) return '未推送';
  const ok = result.channels.filter((item) => item.success).length;
  const total = result.channels.length;
  return `${result.status} · ${ok}/${total || 0}`;
}

const AdvisorPage: React.FC = () => {
  const [status, setStatus] = useState<AdvisorStatusResponse | null>(null);
  const [snapshots, setSnapshots] = useState<AdvisorSnapshotItem[]>([]);
  const [selectedStage, setSelectedStage] = useState('auto');
  const [sendNotification, setSendNotification] = useState(false);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [testingNotification, setTestingNotification] = useState(false);
  const [error, setError] = useState<ParsedApiError | null>(null);
  const [notice, setNotice] = useState<{ type: 'success' | 'warning' | 'danger'; title: string; message: string } | null>(null);

  useEffect(() => {
    document.title = 'AI投顾值班室 - DSA';
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusPayload, snapshotPayload] = await Promise.all([
        advisorApi.getStatus(),
        advisorApi.listSnapshots(12),
      ]);
      setStatus(statusPayload);
      setSnapshots(snapshotPayload.items);
    } catch (requestError: unknown) {
      setError(getParsedApiError(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const latestSnapshot = snapshots[0] ?? status?.latestSnapshot ?? null;
  const stageOptions = useMemo(
    () => [
      { value: 'auto', label: status?.nextStage ? `自动：${status.nextStage.name}` : '自动识别当前阶段' },
      ...(status?.stages ?? []).map((stage) => ({ value: stage.id, label: `${stage.time} ${stage.name}` })),
    ],
    [status?.nextStage, status?.stages],
  );

  const runStage = async () => {
    setRunning(true);
    setError(null);
    setNotice(null);
    try {
      const result = await advisorApi.runStage({
        stage: selectedStage,
        sendNotification,
      });
      setSnapshots((prev) => [result.snapshot, ...prev.filter((item) => item.id !== result.snapshot.id)].slice(0, 12));
      setStatus((prev) => prev ? { ...prev, latestSnapshot: result.snapshot } : prev);
      setNotice({
        type: result.notification?.success === false ? 'warning' : 'success',
        title: sendNotification ? '值班快照已生成并尝试推送' : '值班快照已生成',
        message: sendNotification ? notificationText(result.notification) : '你可以在下方查看最新快照，也可以再执行推送测试。',
      });
    } catch (requestError: unknown) {
      setError(getParsedApiError(requestError));
    } finally {
      setRunning(false);
    }
  };

  const runNotificationTest = async () => {
    setTestingNotification(true);
    setError(null);
    setNotice(null);
    try {
      const result = await advisorApi.notifyTest();
      setSnapshots((prev) => [result.snapshot, ...prev.filter((item) => item.id !== result.snapshot.id)].slice(0, 12));
      setStatus((prev) => prev ? { ...prev, latestSnapshot: result.snapshot } : prev);
      setNotice({
        type: result.notification?.success ? 'success' : 'danger',
        title: result.notification?.success ? '推送测试成功' : '推送测试未成功',
        message: notificationText(result.notification),
      });
    } catch (requestError: unknown) {
      setError(getParsedApiError(requestError));
    } finally {
      setTestingNotification(false);
    }
  };

  return (
    <AppPage className="space-y-5">
      <PageHeader
        eyebrow="Advisor Copilot"
        title="AI投顾值班室"
        description="让系统按竞价、开盘、午盘、尾盘、收盘五个阶段主动生成交易值班快照，并通过已配置通知渠道推送关键变化。"
        actions={(
          <>
            <Button variant="secondary" size="sm" onClick={() => void loadData()} disabled={loading}>
              <RefreshCw className="h-4 w-4" />
              刷新
            </Button>
            <Button variant="action-primary" size="sm" onClick={() => void runStage()} isLoading={running} loadingText="运行中">
              <Play className="h-4 w-4" />
              运行阶段
            </Button>
          </>
        )}
      />

      {error ? <ApiErrorAlert error={error} onDismiss={() => setError(null)} /> : null}
      {notice ? (
        <InlineAlert
          variant={notice.type}
          title={notice.title}
          message={notice.message}
          action={(
            <button type="button" className="text-sm underline" onClick={() => setNotice(null)}>
              关闭
            </button>
          )}
        />
      ) : null}

      {loading ? <Loading label="正在加载 AI 投顾值班室" /> : null}

      {!loading ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="当前阶段"
              value={status?.nextStage?.name ?? '--'}
              hint={status?.nextStage ? `${status.nextStage.time} · ${status.nextStage.objective}` : '等待状态加载'}
              icon={<Clock3 className="h-5 w-5" />}
              tone="primary"
            />
            <StatCard
              label="通知状态"
              value={status?.notificationReady ? '已配置' : '未配置'}
              hint={status?.notificationChannels?.length ? status.notificationChannels.join(', ') : '先在设置里配置飞书/企业微信等渠道'}
              icon={<BellRing className="h-5 w-5" />}
              tone={status?.notificationReady ? 'success' : 'warning'}
            />
            <StatCard
              label="最新快照"
              value={latestSnapshot?.stageName ?? '暂无'}
              hint={formatDateTime(latestSnapshot?.generatedAt)}
              icon={<Radar className="h-5 w-5" />}
              tone="default"
            />
            <StatCard
              label="人工介入"
              value="确认制"
              hint="系统给条件和纪律，买卖仍由你确认"
              icon={<ShieldCheck className="h-5 w-5" />}
              tone="warning"
            />
          </div>

          <Card variant="bordered" padding="md">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-foreground">运行阶段</span>
                  <select
                    value={selectedStage}
                    onChange={(event) => setSelectedStage(event.target.value)}
                    className="input-surface input-focus-glow h-10 w-full rounded-xl border bg-transparent px-3 text-sm text-foreground outline-none"
                  >
                    {stageOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
                <label className="flex h-10 items-center gap-2 rounded-xl border border-subtle bg-surface/60 px-3 text-sm text-secondary-text">
                  <input
                    type="checkbox"
                    checked={sendNotification}
                    onChange={(event) => setSendNotification(event.target.checked)}
                    className="chat-skill-checkbox"
                  />
                  生成后立即推送
                </label>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" size="sm" onClick={() => void runNotificationTest()} isLoading={testingNotification} loadingText="测试中">
                  <Send className="h-4 w-4" />
                  推送测试
                </Button>
              </div>
            </div>
          </Card>

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
            <Card title="最新值班快照" subtitle="Active brief" variant="bordered" padding="md">
              {latestSnapshot ? (
                <div className="space-y-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="info">{latestSnapshot.stageName}</Badge>
                    <Badge variant="warning">{latestSnapshot.actionLevel}</Badge>
                    <Badge variant="default">{latestSnapshot.marketMode}</Badge>
                    <span className="text-sm text-muted-text">{formatDateTime(latestSnapshot.generatedAt)}</span>
                  </div>
                  <p className="text-sm leading-6 text-secondary-text">{latestSnapshot.summary}</p>

                  <section>
                    <h3 className="text-sm font-semibold text-foreground">候选分层</h3>
                    <div className="mt-3 grid gap-3 md:grid-cols-3">
                      {latestSnapshot.candidates.map((item) => (
                        <div key={`${item.type}-${item.status}`} className="rounded-xl border border-border/55 bg-background/35 p-3">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-semibold text-foreground">{item.type}</span>
                            <Badge variant="default">{item.status}</Badge>
                          </div>
                          <p className="mt-2 text-xs leading-5 text-secondary-text">{item.rule}</p>
                        </div>
                      ))}
                    </div>
                  </section>

                  <section className="grid gap-4 lg:grid-cols-3">
                    <SnapshotList title="关键观察点" items={latestSnapshot.watchpoints} />
                    <SnapshotList title="风控纪律" items={latestSnapshot.riskControls} />
                    <SnapshotList title="下一步" items={latestSnapshot.nextActions} />
                  </section>
                </div>
              ) : (
                <EmptyState
                  icon={<Radar className="h-6 w-6" />}
                  title="暂无值班快照"
                  description="点击“运行阶段”生成第一份 AI 投顾值班快照。"
                />
              )}
            </Card>

            <Card title="阶段时间表" subtitle="Trading desk rhythm" variant="bordered" padding="md">
              <div className="space-y-3">
                {(status?.stages ?? []).map((stage: AdvisorStageItem) => (
                  <div
                    key={stage.id}
                    className="rounded-xl border border-border/55 bg-background/35 p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold text-foreground">{stage.name}</p>
                        <p className="mt-1 text-xs text-muted-text">{stage.time}</p>
                      </div>
                      {status?.nextStage?.id === stage.id ? <Badge variant="info">当前</Badge> : null}
                    </div>
                    <p className="mt-2 text-xs leading-5 text-secondary-text">{stage.objective}</p>
                    <p className="mt-2 text-xs leading-5 text-muted-text">{stage.pushPolicy}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <Card title="历史快照" subtitle="Recent snapshots" variant="bordered" padding="md">
            {snapshots.length ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="border-b border-border/60 text-xs uppercase text-muted-text">
                    <tr>
                      <th className="px-3 py-2 font-medium">时间</th>
                      <th className="px-3 py-2 font-medium">阶段</th>
                      <th className="px-3 py-2 font-medium">行动级别</th>
                      <th className="px-3 py-2 font-medium">摘要</th>
                      <th className="px-3 py-2 font-medium">推送</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {snapshots.map((item) => (
                      <tr key={item.id}>
                        <td className="px-3 py-3 whitespace-nowrap">{formatDateTime(item.generatedAt)}</td>
                        <td className="px-3 py-3">{item.stageName}</td>
                        <td className="px-3 py-3">{item.actionLevel}</td>
                        <td className="px-3 py-3 text-secondary-text">{item.summary}</td>
                        <td className="px-3 py-3">{notificationText(item.notification)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                icon={<Clock3 className="h-6 w-6" />}
                title="暂无历史快照"
                description="运行后这里会保留最近的值班记录。"
              />
            )}
          </Card>
        </>
      ) : null}
    </AppPage>
  );
};

const SnapshotList: React.FC<{ title: string; items: string[] }> = ({ title, items }) => (
  <div className="rounded-xl border border-border/55 bg-background/35 p-3">
    <h3 className="text-sm font-semibold text-foreground">{title}</h3>
    <ul className="mt-3 space-y-2 text-xs leading-5 text-secondary-text">
      {items.map((item) => (
        <li key={item} className="flex gap-2">
          <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-cyan" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  </div>
);

export default AdvisorPage;
