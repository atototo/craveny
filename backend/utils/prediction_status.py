"""
예측 생성 진행 상태 추적

메모리 기반 진행 상태 추적 (간단한 구현)
프로덕션에서는 Redis 같은 영구 저장소 사용 권장
"""
from typing import Dict, Optional
from datetime import datetime
import threading


class PredictionStatusTracker:
    """예측 생성 진행 상태 추적기 (싱글톤)"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """초기화"""
        self._status: Dict[str, Dict] = {}
        self._status_lock = threading.Lock()

    def start_task(self, task_id: str, total_count: int, description: str = "") -> None:
        """
        작업 시작

        Args:
            task_id: 작업 ID (예: "ab_config_4", "model_add_5")
            total_count: 총 예측 생성할 개수
            description: 작업 설명
        """
        with self._status_lock:
            self._status[task_id] = {
                "status": "in_progress",
                "total": total_count,
                "completed": 0,
                "failed": 0,
                "description": description,
                "started_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

    def update_progress(self, task_id: str, completed: int = 0, failed: int = 0) -> None:
        """
        진행 상황 업데이트

        Args:
            task_id: 작업 ID
            completed: 성공한 예측 개수 (누적)
            failed: 실패한 예측 개수 (누적)
        """
        with self._status_lock:
            if task_id in self._status:
                self._status[task_id]["completed"] = completed
                self._status[task_id]["failed"] = failed
                self._status[task_id]["updated_at"] = datetime.utcnow().isoformat()

                # 완료 여부 체크
                total = self._status[task_id]["total"]
                if completed + failed >= total:
                    self._status[task_id]["status"] = "completed"
                    self._status[task_id]["completed_at"] = datetime.utcnow().isoformat()

    def increment_progress(self, task_id: str, success: bool = True) -> None:
        """
        진행 상황 1개 증가

        Args:
            task_id: 작업 ID
            success: 성공 여부
        """
        with self._status_lock:
            if task_id in self._status:
                if success:
                    self._status[task_id]["completed"] += 1
                else:
                    self._status[task_id]["failed"] += 1
                self._status[task_id]["updated_at"] = datetime.utcnow().isoformat()

                # 완료 여부 체크
                total = self._status[task_id]["total"]
                completed = self._status[task_id]["completed"]
                failed = self._status[task_id]["failed"]

                if completed + failed >= total:
                    self._status[task_id]["status"] = "completed"
                    self._status[task_id]["completed_at"] = datetime.utcnow().isoformat()

    def get_status(self, task_id: str) -> Optional[Dict]:
        """
        작업 상태 조회

        Args:
            task_id: 작업 ID

        Returns:
            작업 상태 정보 또는 None
        """
        with self._status_lock:
            return self._status.get(task_id)

    def get_all_active_tasks(self) -> Dict[str, Dict]:
        """
        진행 중인 모든 작업 조회

        Returns:
            진행 중인 작업 목록
        """
        with self._status_lock:
            return {
                task_id: status
                for task_id, status in self._status.items()
                if status["status"] == "in_progress"
            }

    def complete_task(self, task_id: str) -> None:
        """
        작업 완료 처리

        Args:
            task_id: 작업 ID
        """
        with self._status_lock:
            if task_id in self._status:
                self._status[task_id]["status"] = "completed"
                self._status[task_id]["completed_at"] = datetime.utcnow().isoformat()

    def fail_task(self, task_id: str, error: str = "") -> None:
        """
        작업 실패 처리

        Args:
            task_id: 작업 ID
            error: 에러 메시지
        """
        with self._status_lock:
            if task_id in self._status:
                self._status[task_id]["status"] = "failed"
                self._status[task_id]["error"] = error
                self._status[task_id]["failed_at"] = datetime.utcnow().isoformat()

    def clear_completed(self, older_than_minutes: int = 60) -> None:
        """
        완료된 작업 정리 (메모리 관리)

        Args:
            older_than_minutes: 이 시간보다 오래된 완료 작업 삭제
        """
        with self._status_lock:
            current_time = datetime.utcnow()
            to_delete = []

            for task_id, status in self._status.items():
                if status["status"] in ["completed", "failed"]:
                    completed_at = datetime.fromisoformat(
                        status.get("completed_at") or status.get("failed_at", status["updated_at"])
                    )
                    age_minutes = (current_time - completed_at).total_seconds() / 60

                    if age_minutes > older_than_minutes:
                        to_delete.append(task_id)

            for task_id in to_delete:
                del self._status[task_id]


# 싱글톤 인스턴스
_tracker = PredictionStatusTracker()


def get_tracker() -> PredictionStatusTracker:
    """전역 트래커 인스턴스 반환"""
    return _tracker
