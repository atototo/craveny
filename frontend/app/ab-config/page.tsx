"use client";

import { useState, useEffect } from "react";

interface Model {
  id: number;
  name: string;
  provider: string;
  model_identifier: string;
}

interface ABConfig {
  id: number;
  model_a: Model;
  model_b: Model;
  is_active: boolean;
  created_at: string;
}

export default function ABConfigPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [currentConfig, setCurrentConfig] = useState<ABConfig | null>(null);
  const [selectedModelA, setSelectedModelA] = useState<number | null>(null);
  const [selectedModelB, setSelectedModelB] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState<ABConfig[]>([]);

  // 모델 목록 조회
  const fetchModels = async () => {
    try {
      const response = await fetch("/api/models?active_only=true");
      const data = await response.json();
      setModels(data);
    } catch (error) {
      console.error("모델 조회 실패:", error);
    }
  };

  // 현재 A/B 설정 조회
  const fetchABConfig = async () => {
    try {
      const response = await fetch("/api/ab-test/config");
      const data = await response.json();

      if (data.id) {
        setCurrentConfig(data);
        setSelectedModelA(data.model_a.id);
        setSelectedModelB(data.model_b.id);
      }
    } catch (error) {
      console.error("A/B 설정 조회 실패:", error);
    } finally {
      setLoading(false);
    }
  };

  // A/B 설정 이력 조회
  const fetchHistory = async () => {
    try {
      const response = await fetch("/api/ab-test/history");
      const data = await response.json();
      setHistory(data.history || []);
    } catch (error) {
      console.error("이력 조회 실패:", error);
    }
  };

  useEffect(() => {
    fetchModels();
    fetchABConfig();
    fetchHistory();
  }, []);

  // A/B 설정 변경
  const handleUpdateConfig = async () => {
    if (!selectedModelA || !selectedModelB) {
      alert("Model A와 Model B를 모두 선택해주세요.");
      return;
    }

    if (selectedModelA === selectedModelB) {
      alert("Model A와 Model B는 서로 다른 모델이어야 합니다.");
      return;
    }

    try {
      const response = await fetch("/api/ab-test/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_a_id: selectedModelA,
          model_b_id: selectedModelB,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        alert(data.message);
        fetchABConfig();
        fetchHistory();
      } else {
        const error = await response.json();
        alert(`설정 변경 실패: ${error.detail}`);
      }
    } catch (error) {
      console.error("설정 변경 실패:", error);
      alert("설정 변경에 실패했습니다.");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">로딩 중...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        {/* 헤더 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">A/B 테스트 설정</h1>
          <p className="text-gray-600 mt-2">
            비교할 두 모델을 선택하세요. 웹과 알림에서 이 두 모델이 비교됩니다.
          </p>
        </div>

        {/* 현재 설정 */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">현재 A/B 설정</h2>

          {currentConfig ? (
            <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg mb-6">
              <div className="flex-1">
                <p className="text-sm text-gray-600">Model A</p>
                <p className="text-lg font-semibold text-blue-900">
                  {currentConfig.model_a.name}
                </p>
                <p className="text-sm text-gray-500">
                  {currentConfig.model_a.model_identifier}
                </p>
              </div>
              <div className="px-4">
                <span className="text-2xl text-gray-400">vs</span>
              </div>
              <div className="flex-1">
                <p className="text-sm text-gray-600">Model B</p>
                <p className="text-lg font-semibold text-blue-900">
                  {currentConfig.model_b.name}
                </p>
                <p className="text-sm text-gray-500">
                  {currentConfig.model_b.model_identifier}
                </p>
              </div>
            </div>
          ) : (
            <div className="p-4 bg-yellow-50 rounded-lg mb-6">
              <p className="text-yellow-800">현재 활성화된 A/B 설정이 없습니다.</p>
            </div>
          )}

          {/* 새 설정 선택 */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Model A 선택
              </label>
              <select
                value={selectedModelA || ""}
                onChange={(e) => setSelectedModelA(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">-- Model A 선택 --</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} ({model.provider}/{model.model_identifier})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Model B 선택
              </label>
              <select
                value={selectedModelB || ""}
                onChange={(e) => setSelectedModelB(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">-- Model B 선택 --</option>
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} ({model.provider}/{model.model_identifier})
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleUpdateConfig}
              disabled={!selectedModelA || !selectedModelB}
              className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              A/B 설정 변경
            </button>
          </div>
        </div>

        {/* 설정 변경 이력 */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">설정 변경 이력</h2>

          {history.length > 0 ? (
            <div className="space-y-3">
              {history.map((config) => (
                <div
                  key={config.id}
                  className={`p-4 rounded-lg border ${
                    config.is_active
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 bg-gray-50"
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-sm text-gray-600">
                        {new Date(config.created_at).toLocaleString("ko-KR")}
                      </p>
                      <p className="font-medium mt-1">
                        {config.model_a.name} vs {config.model_b.name}
                      </p>
                    </div>
                    {config.is_active && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full">
                        활성
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">
              설정 변경 이력이 없습니다.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
