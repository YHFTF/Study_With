"""세션 기록 관리 및 통계 계산 모듈"""
from __future__ import annotations

import json
import os
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


def _get_data_dir() -> Path:
    """세션 데이터 저장 디렉토리 반환"""
    system = platform.system()
    if system == "Windows":
        base = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        data_dir = base / "StudyWith" / "data"
    elif system == "Darwin":
        data_dir = Path.home() / "Library" / "Application Support" / "StudyWith" / "data"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
        data_dir = base / "study-with" / "data"
    
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _get_sessions_file() -> Path:
    """세션 기록 파일 경로 반환"""
    return _get_data_dir() / "sessions.json"


class SessionManager:
    """세션 기록 관리 클래스"""
    
    def __init__(self):
        self.sessions_file = _get_sessions_file()
        self.sessions: List[Dict] = []
        self.load_sessions()
    
    def load_sessions(self) -> None:
        """세션 기록 파일에서 로드"""
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    self.sessions = json.load(f)
            except Exception:
                self.sessions = []
        else:
            self.sessions = []
    
    def save_sessions(self) -> None:
        """세션 기록을 파일에 저장"""
        try:
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"세션 저장 실패: {e}")
    
    def add_session(self, 
                   start_time: datetime,
                   end_time: datetime,
                   total_focus_minutes: int,
                   total_cycles: int,
                   completed_cycles: int,
                   focus_duration: int,
                   break_duration: int) -> None:
        """새 세션 기록 추가"""
        session = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_focus_minutes": total_focus_minutes,
            "total_cycles": total_cycles,
            "completed_cycles": completed_cycles,
            "focus_duration": focus_duration,  # 분 단위
            "break_duration": break_duration,  # 분 단위
            "date": start_time.date().isoformat()
        }
        self.sessions.append(session)
        self.save_sessions()
    
    def get_all_sessions(self) -> List[Dict]:
        """모든 세션 기록 반환"""
        return self.sessions
    
    def get_statistics(self) -> Dict:
        """통계 정보 계산"""
        if not self.sessions:
            return {
                "total_sessions": 0,
                "total_focus_minutes": 0,
                "total_focus_hours": 0,
                "total_cycles": 0,
                "completed_sessions": 0,
                "current_streak": 0,
                "longest_streak": 0,
                "total_score": 0,
                "rank": "브론즈",
                "rank_display": "브론즈"
            }
        
        # 기본 통계
        total_sessions = len(self.sessions)
        total_focus_minutes = sum(s.get("total_focus_minutes", 0) for s in self.sessions)
        total_focus_hours = total_focus_minutes / 60
        total_cycles = sum(s.get("completed_cycles", 0) for s in self.sessions)
        completed_sessions = sum(1 for s in self.sessions if s.get("completed_cycles", 0) == s.get("total_cycles", 0))
        
        # 연속 일수 계산
        dates = sorted(set(s.get("date", "") for s in self.sessions if s.get("date")))
        if not dates:
            current_streak = 0
            longest_streak = 0
        else:
            # 날짜를 datetime으로 변환하여 계산
            date_objs = [datetime.fromisoformat(d).date() for d in dates]
            date_objs.sort()
            
            # 현재 연속 일수
            today = datetime.now().date()
            current_streak = 0
            check_date = today
            # 오늘 또는 어제부터 역순으로 연속된 날짜 확인
            while True:
                if check_date in date_objs:
                    current_streak += 1
                    check_date -= timedelta(days=1)
                elif check_date == today:
                    # 오늘은 기록이 없지만, 어제부터 연속이면 계속 확인
                    check_date -= timedelta(days=1)
                else:
                    # 연속이 끊김
                    break
            
            # 최장 연속 일수
            longest_streak = 1
            temp_streak = 1
            for i in range(1, len(date_objs)):
                if (date_objs[i] - date_objs[i-1]).days == 1:
                    temp_streak += 1
                    longest_streak = max(longest_streak, temp_streak)
                else:
                    temp_streak = 1
        
        # 점수 계산
        # 집중 시간 1분 = 1점
        time_score = total_focus_minutes
        # 완료한 세션 1회 = 10점
        session_score = completed_sessions * 10
        # 연속 일수 보너스 (연속 일수 * 5점)
        streak_bonus = current_streak * 5
        total_score = time_score + session_score + streak_bonus
        
        # 등급 결정
        rank_info = self._calculate_rank(total_score)
        
        return {
            "total_sessions": total_sessions,
            "total_focus_minutes": total_focus_minutes,
            "total_focus_hours": round(total_focus_hours, 1),
            "total_cycles": total_cycles,
            "completed_sessions": completed_sessions,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_score": total_score,
            "rank": rank_info["rank"],
            "rank_display": rank_info["display"]
        }
    
    def _calculate_rank(self, score: int) -> Dict[str, str]:
        """점수에 따른 등급 계산"""
        if score < 100:
            return {"rank": "BRONZE", "display": "브론즈"}
        elif score < 300:
            return {"rank": "SILVER", "display": "실버"}
        elif score < 600:
            return {"rank": "GOLD", "display": "골드"}
        elif score < 1000:
            return {"rank": "PLATINUM", "display": "플래티넘"}
        elif score < 2000:
            return {"rank": "DIAMOND", "display": "다이아몬드"}
        elif score < 4000:
            return {"rank": "MASTER", "display": "마스터"}
        elif score < 8000:
            return {"rank": "GRANDMASTER", "display": "그랜드마스터"}
        elif score < 15000:
            return {"rank": "CHALLENGER", "display": "챌린저"}
        else:
            return {"rank": "LEGEND", "display": f"{score:,}점"}
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """최근 세션 기록 반환"""
        sorted_sessions = sorted(self.sessions, key=lambda x: x.get("start_time", ""), reverse=True)
        return sorted_sessions[:limit]
