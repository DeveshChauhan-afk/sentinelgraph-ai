import { useEffect, useState } from 'react';
import { healthApi } from '../api';
import { HealthSummaryResponse } from '../types';

export function useHealth() {
  const [health, setHealth] = useState<HealthSummaryResponse | null>(null);
  const [version, setVersion] = useState<string>('0.1.0');
  const [loading, setLoading] = useState<boolean>(true);
  const [isOnline, setIsOnline] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;

    async function checkHealth() {
      try {
        const [healthData, versionData] = await Promise.allSettled([
          healthApi.getHealth(),
          healthApi.getVersion(),
        ]);

        if (!mounted) return;

        if (healthData.status === 'fulfilled') {
          setHealth(healthData.value);
          setIsOnline(healthData.value.status !== 'UNHEALTHY');
        } else {
          setIsOnline(false);
        }

        if (versionData.status === 'fulfilled') {
          setVersion(versionData.value.version);
        }
      } catch {
        if (mounted) {
          setIsOnline(false);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Poll every 30s
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return { health, version, loading, isOnline };
}
