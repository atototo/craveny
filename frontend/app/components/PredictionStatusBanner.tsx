"use client";

import { useEffect, useState } from "react";

interface PredictionStatus {
  has_active_tasks: boolean;
  active_tasks: {
    [key: string]: {
      status: string;
      total: number;
      completed: number;
      failed: number;
      description: string;
    };
  };
}

export default function PredictionStatusBanner() {
  const [status, setStatus] = useState<PredictionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // 초기 로드
    fetchStatus();

    // 5초마다 폴링
    const interval = setInterval(fetchStatus, 5000);

    return () => clearInterval(interval);
  }, []);

  async function fetchStatus() {
    try {
      const res = await fetch("/api/ab-test/prediction-status");
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
        setIsLoading(data.has_active_tasks);
      }
    } catch (error) {
      console.error("Failed to fetch prediction status:", error);
    }
  }

  if (!status || !status.has_active_tasks) {
    return null;
  }

  const activeTasks = Object.values(status.active_tasks);
  if (activeTasks.length === 0) {
    return null;
  }

  const task = activeTasks[0];
  const progress = task.total > 0 ? Math.round(((task.completed + task.failed) / task.total) * 100) : 0;

  return (
    <div className="fixed top-16 left-0 right-0 z-50 bg-blue-600 text-white px-4 py-3 shadow-lg">
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
          <div>
            <div className="font-medium">{task.description}</div>
            <div className="text-sm text-blue-100">
              {task.completed + task.failed} / {task.total} 완료 ({progress}%)
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-48 bg-blue-700 rounded-full h-2">
            <div
              className="bg-white h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
}
