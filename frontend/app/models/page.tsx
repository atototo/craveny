"use client";

import { useState, useEffect } from "react";

interface Model {
  id: number;
  name: string;
  provider: string;
  model_identifier: string;
  is_active: boolean;
  description: string | null;
  created_at: string;
}

export default function ModelsPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    provider: "openrouter",
    model_identifier: "",
    description: "",
  });

  // 모델 목록 조회
  const fetchModels = async () => {
    try {
      const response = await fetch("/api/models");
      const data = await response.json();
      setModels(data);
    } catch (error) {
      console.error("모델 조회 실패:", error);
      alert("모델 목록을 불러오는데 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  // 모델 추가
  const handleAddModel = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch("/api/models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        alert("모델이 추가되었습니다!");
        setShowAddForm(false);
        setFormData({
          name: "",
          provider: "openrouter",
          model_identifier: "",
          description: "",
        });
        fetchModels();
      } else {
        const error = await response.json();
        alert(`모델 추가 실패: ${error.detail}`);
      }
    } catch (error) {
      console.error("모델 추가 실패:", error);
      alert("모델 추가에 실패했습니다.");
    }
  };

  // 모델 활성화/비활성화 토글
  const handleToggleActive = async (modelId: number) => {
    try {
      const response = await fetch(
        `/api/models/${modelId}/toggle`,
        { method: "PATCH" }
      );

      if (response.ok) {
        fetchModels();
      } else {
        alert("상태 변경에 실패했습니다.");
      }
    } catch (error) {
      console.error("상태 변경 실패:", error);
      alert("상태 변경에 실패했습니다.");
    }
  };

  // 모델 삭제
  const handleDeleteModel = async (modelId: number, modelName: string) => {
    if (!confirm(`정말로 '${modelName}' 모델을 삭제하시겠습니까?`)) {
      return;
    }

    try {
      const response = await fetch(
        `/api/models/${modelId}`,
        { method: "DELETE" }
      );

      if (response.ok) {
        alert("모델이 삭제되었습니다.");
        fetchModels();
      } else {
        const error = await response.json();
        alert(`모델 삭제 실패: ${error.detail}`);
      }
    } catch (error) {
      console.error("모델 삭제 실패:", error);
      alert("모델 삭제에 실패했습니다.");
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
      <div className="max-w-6xl mx-auto">
        {/* 헤더 */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">모델 관리</h1>
            <p className="text-gray-600 mt-2">
              LLM 모델을 추가하고 관리합니다
            </p>
          </div>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
          >
            {showAddForm ? "취소" : "➕ 모델 추가"}
          </button>
        </div>

        {/* 모델 추가 폼 */}
        {showAddForm && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">새 모델 추가</h2>
            <form onSubmit={handleAddModel} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  모델 이름
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="예: GPT-4o, Claude 3.5"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  프로바이더
                </label>
                <select
                  value={formData.provider}
                  onChange={(e) =>
                    setFormData({ ...formData, provider: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="openai">OpenAI</option>
                  <option value="openrouter">OpenRouter</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  모델 식별자
                </label>
                <input
                  type="text"
                  value={formData.model_identifier}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      model_identifier: e.target.value,
                    })
                  }
                  placeholder="예: gpt-4o, deepseek/deepseek-v3.2-exp"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  설명 (선택사항)
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  placeholder="모델 설명"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <button
                type="submit"
                className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition"
              >
                추가하기
              </button>
            </form>
          </div>
        )}

        {/* 모델 목록 */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  모델 이름
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  프로바이더
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  모델 식별자
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  상태
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  작업
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {models.map((model) => (
                <tr key={model.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {model.name}
                        </div>
                        {model.description && (
                          <div className="text-sm text-gray-500">
                            {model.description}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        model.provider === "openai"
                          ? "bg-green-100 text-green-800"
                          : "bg-blue-100 text-blue-800"
                      }`}
                    >
                      {model.provider}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {model.model_identifier}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => handleToggleActive(model.id)}
                      className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        model.is_active
                          ? "bg-green-100 text-green-800 hover:bg-green-200"
                          : "bg-gray-100 text-gray-800 hover:bg-gray-200"
                      } transition`}
                    >
                      {model.is_active ? "✓ 활성" : "○ 비활성"}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => handleDeleteModel(model.id, model.name)}
                      className="text-red-600 hover:text-red-900 transition"
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {models.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              등록된 모델이 없습니다.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
