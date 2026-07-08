import { useState, useEffect } from 'react';
import { fetchStats } from '../api';

export function useStats(days = 7) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchStats(days)
      .then(data => setStats(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [days]);

  return { stats, loading };
}
