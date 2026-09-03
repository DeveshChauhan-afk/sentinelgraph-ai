import React, { useEffect, useState, useCallback } from 'react';
import { analyticsApi, complaintsApi, graphApi } from '../api';
import {
  GraphSummary,
  IncidentListResponse,
  SharedEntityAnalysis,
  TopConnectedEntity,
  TopRiskEntityResponse,
} from '../types';
import { KpiGrid } from '../components/overview/KpiGrid';
import { HighestRiskTable } from '../components/overview/HighestRiskTable';
import { FraudHubsList } from '../components/overview/FraudHubsList';
import { SharedInfrastructureCard } from '../components/overview/SharedInfrastructureCard';
import { RecentComplaintsTable } from '../components/overview/RecentComplaintsTable';
import { RefreshCw, ShieldAlert, Cpu } from 'lucide-react';

interface RiskOverviewPageProps {
  onNavigateToInvestigate?: (entityValue?: string) => void;
}

export const RiskOverviewPage: React.FC<RiskOverviewPageProps> = ({
  onNavigateToInvestigate,
}) => {
  // Section 1: Summary KPIs
  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState<boolean>(true);
  const [errorSummary, setErrorSummary] = useState<string | null>(null);

  // Section 2: Top Risk Entities
  const [topRisk, setTopRisk] = useState<TopRiskEntityResponse[] | null>(null);
  const [loadingTopRisk, setLoadingTopRisk] = useState<boolean>(true);
  const [errorTopRisk, setErrorTopRisk] = useState<string | null>(null);

  // Section 3: Fraud Hubs (Top Connected)
  const [topConnected, setTopConnected] = useState<TopConnectedEntity[] | null>(null);
  const [loadingTopConnected, setLoadingTopConnected] = useState<boolean>(true);
  const [errorTopConnected, setErrorTopConnected] = useState<string | null>(null);

  // Section 4: Shared Infrastructure
  const [sharedEntities, setSharedEntities] = useState<SharedEntityAnalysis[] | null>(null);
  const [loadingSharedEntities, setLoadingSharedEntities] = useState<boolean>(true);
  const [errorSharedEntities, setErrorSharedEntities] = useState<string | null>(null);

  // Section 5: Recent Complaints
  const [complaints, setComplaints] = useState<IncidentListResponse[] | null>(null);
  const [loadingComplaints, setLoadingComplaints] = useState<boolean>(true);
  const [errorComplaints, setErrorComplaints] = useState<string | null>(null);

  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Individual Fetch Handlers for independent resilience
  const fetchSummary = useCallback(async () => {
    setLoadingSummary(true);
    setErrorSummary(null);
    try {
      const data = await analyticsApi.getSummary();
      setSummary(data);
    } catch (err: any) {
      setErrorSummary(err.message || 'Unable to retrieve network summary.');
    } finally {
      setLoadingSummary(false);
    }
  }, []);

  const fetchTopRisk = useCallback(async () => {
    setLoadingTopRisk(true);
    setErrorTopRisk(null);
    try {
      const data = await graphApi.getTopRiskEntities(10);
      setTopRisk(data);
    } catch (err: any) {
      setErrorTopRisk(err.message || 'Unable to retrieve top-risk entities.');
    } finally {
      setLoadingTopRisk(false);
    }
  }, []);

  const fetchTopConnected = useCallback(async () => {
    setLoadingTopConnected(true);
    setErrorTopConnected(null);
    try {
      const data = await analyticsApi.getTopConnected(10);
      setTopConnected(data);
    } catch (err: any) {
      setErrorTopConnected(err.message || 'Unable to retrieve connected hubs.');
    } finally {
      setLoadingTopConnected(false);
    }
  }, []);

  const fetchSharedEntities = useCallback(async () => {
    setLoadingSharedEntities(true);
    setErrorSharedEntities(null);
    try {
      const data = await analyticsApi.getSharedEntities(2);
      setSharedEntities(data);
    } catch (err: any) {
      setErrorSharedEntities(err.message || 'Unable to retrieve shared infrastructure.');
    } finally {
      setLoadingSharedEntities(false);
    }
  }, []);

  const fetchComplaints = useCallback(async () => {
    setLoadingComplaints(true);
    setErrorComplaints(null);
    try {
      const data = await complaintsApi.listComplaints(0, 25);
      setComplaints(data);
    } catch (err: any) {
      setErrorComplaints(err.message || 'Unable to retrieve complaints feed.');
    } finally {
      setLoadingComplaints(false);
    }
  }, []);

  // Coordinated Refresh
  const handleRefreshAll = useCallback(async () => {
    setIsRefreshing(true);
    await Promise.allSettled([
      fetchSummary(),
      fetchTopRisk(),
      fetchTopConnected(),
      fetchSharedEntities(),
      fetchComplaints(),
    ]);
    setIsRefreshing(false);
  }, [
    fetchSummary,
    fetchTopRisk,
    fetchTopConnected,
    fetchSharedEntities,
    fetchComplaints,
  ]);

  useEffect(() => {
    handleRefreshAll();
  }, [handleRefreshAll]);

  const handleEntitySelect = (entityValue: string) => {
    if (onNavigateToInvestigate) {
      onNavigateToInvestigate(entityValue);
    }
  };

  return (
    <div className="space-y-5 pb-8">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-sentinel-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-sentinel-accent" />
            <h2 className="text-lg font-bold text-sentinel-text tracking-tight">
              Risk Overview
            </h2>
          </div>
          <p className="text-xs text-sentinel-muted mt-0.5">
            Network-wide fraud and abuse intelligence
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-sentinel-surface border border-sentinel-border text-[11px] font-mono text-sentinel-dim">
            <Cpu className="w-3.5 h-3.5 text-blue-400" />
            <span>Graph-RAG Engine Active</span>
          </div>

          <button
            onClick={handleRefreshAll}
            disabled={isRefreshing}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-sentinel-text bg-sentinel-surface hover:bg-sentinel-surfaceHover border border-sentinel-border rounded transition-colors disabled:opacity-50"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-sentinel-muted ${
                isRefreshing ? 'animate-spin text-sentinel-accent' : ''
              }`}
            />
            <span>Refresh Intelligence</span>
          </button>
        </div>
      </div>

      {/* KPI Row (5 Cards) */}
      <KpiGrid
        summary={summary}
        topRisk={topRisk}
        loading={loadingSummary || loadingTopRisk}
        error={errorSummary}
        onRetry={fetchSummary}
      />

      {/* Main Content: Two-Column Responsive Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left / Larger Column (7 of 12 cols): Highest Risk Entities */}
        <div className="lg:col-span-7">
          <HighestRiskTable
            data={topRisk}
            loading={loadingTopRisk}
            error={errorTopRisk}
            onRetry={fetchTopRisk}
            onSelectEntity={handleEntitySelect}
          />
        </div>

        {/* Right / Smaller Column (5 of 12 cols): Fraud Hubs + Shared Infrastructure */}
        <div className="lg:col-span-5 space-y-5">
          <FraudHubsList
            data={topConnected}
            loading={loadingTopConnected}
            error={errorTopConnected}
            onRetry={fetchTopConnected}
            onSelectEntity={handleEntitySelect}
          />

          <SharedInfrastructureCard
            data={sharedEntities}
            loading={loadingSharedEntities}
            error={errorSharedEntities}
            onRetry={fetchSharedEntities}
            onSelectEntity={handleEntitySelect}
          />
        </div>
      </div>

      {/* Recent Complaints: Full-Width Section */}
      <div className="pt-2">
        <RecentComplaintsTable
          data={complaints}
          loading={loadingComplaints}
          error={errorComplaints}
          onRetry={fetchComplaints}
          onSelectComplaint={(complaintId) => handleEntitySelect(complaintId)}
        />
      </div>
    </div>
  );
};
