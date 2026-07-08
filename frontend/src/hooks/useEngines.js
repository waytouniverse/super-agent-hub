import { useState, useEffect, useCallback } from 'react';
import { fetchEngines } from '../api';

export function useEngines() {
  const [engines, setEngines] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEngines()
      .then(data => setEngines(data.engines || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return { engines, loading };
}
