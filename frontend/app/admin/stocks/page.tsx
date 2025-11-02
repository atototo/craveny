"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface Stock {
  id: number;
  code: string;
  name: string;
  priority: number;
  is_active: boolean;
}

interface StockListResponse {
  total: number;
  stocks: Stock[];
}

export default function AdminStocksPage() {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 추가 폼 상태
  const [showAddForm, setShowAddForm] = useState(false);
  const [newStock, setNewStock] = useState({
    code: "",
    name: "",
    priority: 5,
  });

  // 필터 상태
  const [filterPriority, setFilterPriority] = useState<number | null>(null);
  const [filterActive, setFilterActive] = useState<boolean | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  // 종목 목록 조회
  const fetchStocks = async () => {
    try {
      setLoading(true);

      // 쿼리 파라미터 구성
      const params = new URLSearchParams();
      if (filterPriority !== null) params.append("priority", filterPriority.toString());
      if (filterActive !== null) params.append("is_active", filterActive.toString());
      if (searchQuery) params.append("search", searchQuery);

      const url = `/api/admin/stocks${params.toString() ? `?${params.toString()}` : ""}`;
      const res = await fetch(url);

      if (!res.ok) {
        throw new Error("종목 목록을 가져올 수 없습니다");
      }

      const data: StockListResponse = await res.json();
      setStocks(data.stocks);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch stocks:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStocks();
  }, [filterPriority, filterActive, searchQuery]);

  // 종목 추가
  const handleAddStock = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const res = await fetch("/api/admin/stocks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newStock),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "종목 추가 실패");
      }

      // 성공 시 폼 초기화 및 목록 새로고침
      setNewStock({ code: "", name: "", priority: 5 });
      setShowAddForm(false);
      fetchStocks();
      alert("종목이 추가되었습니다");
    } catch (err: any) {
      alert(`추가 실패: ${err.message}`);
    }
  };

  // 종목 활성화/비활성화 토글
  const handleToggleActive = async (stock: Stock) => {
    try {
      const res = await fetch(`/api/admin/stocks/${stock.code}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !stock.is_active }),
      });

      if (!res.ok) {
        throw new Error("상태 변경 실패");
      }

      fetchStocks();
    } catch (err: any) {
      alert(`상태 변경 실패: ${err.message}`);
    }
  };

  // 우선순위 변경
  const handleChangePriority = async (stock: Stock, newPriority: number) => {
    try {
      const res = await fetch(`/api/admin/stocks/${stock.code}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ priority: newPriority }),
      });

      if (!res.ok) {
        throw new Error("우선순위 변경 실패");
      }

      fetchStocks();
    } catch (err: any) {
      alert(`우선순위 변경 실패: ${err.message}`);
    }
  };

  // 종목 삭제 (비활성화)
  const handleDeleteStock = async (stock: Stock) => {
    if (!confirm(`${stock.name} (${stock.code})를 비활성화하시겠습니까?`)) {
      return;
    }

    try {
      const res = await fetch(`/api/admin/stocks/${stock.code}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        throw new Error("삭제 실패");
      }

      fetchStocks();
      alert("종목이 비활성화되었습니다");
    } catch (err: any) {
      alert(`삭제 실패: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">종목 관리</h1>
            <p className="text-gray-600 mt-1">종목 추가, 수정, 삭제</p>
          </div>
          <div className="flex gap-3">
            <Link
              href="/"
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              ← 대시보드
            </Link>
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              {showAddForm ? "취소" : "+ 종목 추가"}
            </button>
          </div>
        </div>

        {/* 에러 표시 */}
        {error && (
          <div className="mb-4 p-4 bg-red-100 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {/* 종목 추가 폼 */}
        {showAddForm && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">새 종목 추가</h2>
            <form onSubmit={handleAddStock} className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  종목 코드 (6자리)
                </label>
                <input
                  type="text"
                  maxLength={6}
                  pattern="[0-9]{6}"
                  value={newStock.code}
                  onChange={(e) => setNewStock({ ...newStock, code: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  placeholder="예: 005930"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  종목명
                </label>
                <input
                  type="text"
                  value={newStock.name}
                  onChange={(e) => setNewStock({ ...newStock, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  placeholder="예: 삼성전자"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  우선순위 (1~5)
                </label>
                <select
                  value={newStock.priority}
                  onChange={(e) =>
                    setNewStock({ ...newStock, priority: parseInt(e.target.value) })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value={1}>1 (최우선)</option>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                  <option value={4}>4</option>
                  <option value={5}>5 (낮음)</option>
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  추가
                </button>
              </div>
            </form>
          </div>
        )}

        {/* 필터 */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                검색 (종목명 또는 코드)
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                placeholder="삼성전자 또는 005930"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                우선순위 필터
              </label>
              <select
                value={filterPriority ?? ""}
                onChange={(e) =>
                  setFilterPriority(e.target.value ? parseInt(e.target.value) : null)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">전체</option>
                <option value={1}>1 (최우선)</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={4}>4</option>
                <option value={5}>5 (낮음)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                활성화 상태
              </label>
              <select
                value={filterActive === null ? "" : filterActive.toString()}
                onChange={(e) =>
                  setFilterActive(
                    e.target.value === "" ? null : e.target.value === "true"
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">전체</option>
                <option value="true">활성화</option>
                <option value="false">비활성화</option>
              </select>
            </div>
          </div>
        </div>

        {/* 종목 목록 */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">
                종목 목록 ({stocks.length}개)
              </h2>
            </div>

            {stocks.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <p>등록된 종목이 없습니다</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        종목 코드
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        종목명
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        우선순위
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        상태
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                        관리
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {stocks.map((stock) => (
                      <tr key={stock.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-mono text-gray-900">
                          {stock.code}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {stock.name}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <select
                            value={stock.priority}
                            onChange={(e) =>
                              handleChangePriority(stock, parseInt(e.target.value))
                            }
                            className="px-2 py-1 border border-gray-300 rounded"
                          >
                            <option value={1}>1 (최우선)</option>
                            <option value={2}>2</option>
                            <option value={3}>3</option>
                            <option value={4}>4</option>
                            <option value={5}>5 (낮음)</option>
                          </select>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <button
                            onClick={() => handleToggleActive(stock)}
                            className={`px-3 py-1 rounded-full text-xs font-medium ${
                              stock.is_active
                                ? "bg-green-100 text-green-700"
                                : "bg-gray-100 text-gray-700"
                            }`}
                          >
                            {stock.is_active ? "활성화" : "비활성화"}
                          </button>
                        </td>
                        <td className="px-4 py-3 text-sm text-right">
                          <button
                            onClick={() => handleDeleteStock(stock)}
                            className="text-red-600 hover:text-red-800"
                          >
                            삭제
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
