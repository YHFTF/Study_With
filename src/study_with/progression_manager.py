from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .session_manager import _get_data_dir


@dataclass
class Equipment:
    slot: str
    name: str
    base_power: int
    enhancement: int = 0

    @property
    def power(self) -> float:
        """현재 강화 단계를 고려한 전투력."""
        return round(self.base_power * (1 + self.enhancement * 0.2), 2)

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> "Equipment":
        return Equipment(
            slot=data.get("slot", ""),
            name=data.get("name", ""),
            base_power=int(data.get("base_power", 0)),
            enhancement=int(data.get("enhancement", 0)),
        )


@dataclass
class ProgressionState:
    points: int
    stage: int
    scrolls: int
    inventory: Dict[str, Equipment]

    def to_dict(self) -> Dict:
        return {
            "points": self.points,
            "stage": self.stage,
            "scrolls": self.scrolls,
            "inventory": {k: v.to_dict() for k, v in self.inventory.items()},
        }


@dataclass
class EnhancementResult:
    slot: str
    success: bool
    before_level: int
    after_level: int
    success_rate: float
    downgraded: bool = False


class ProgressionManager:
    """포인트, 장비, 스테이지 진행을 관리하는 경량 매니저."""

    def __init__(self):
        self.progress_file = _get_data_dir() / "progression.json"
        self.state: ProgressionState = self._load_state()
        self.battle_state: Optional[Dict[str, Any]] = None

    def _default_inventory(self) -> Dict[str, Equipment]:
        return {
            "book": Equipment(slot="book", name="책", base_power=10, enhancement=0),
            "pencil": Equipment(slot="pencil", name="연필", base_power=7, enhancement=0),
            "laptop": Equipment(slot="laptop", name="노트북", base_power=15, enhancement=0),
        }

    def _load_state(self) -> ProgressionState:
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                inventory_raw = raw.get("inventory", {})
                inventory: Dict[str, Equipment] = {}
                defaults = self._default_inventory()
                for slot, default_item in defaults.items():
                    merged = {**default_item.to_dict(), **inventory_raw.get(slot, {})}
                    inventory[slot] = Equipment.from_dict(merged)
                return ProgressionState(
                    points=int(raw.get("points", 0)),
                    stage=int(raw.get("stage", 1)),
                    scrolls=int(raw.get("scrolls", 0)),
                    inventory=inventory,
                )
            except Exception:
                pass

        return ProgressionState(
            points=0,
            stage=1,
            scrolls=0,
            inventory=self._default_inventory(),
        )

    def _save_state(self) -> None:
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"진행도 저장 실패: {e}")

    def add_points(self, amount: int) -> bool:
        """테스트 모드용: 포인트 임의 지급"""
        if amount <= 0:
            return False
        self.state.points += amount
        self._save_state()
        return True

    # --- 포인트 획득/소비 ---
    def grant_points_from_session(
        self,
        total_focus_minutes: int,
        completed_cycles: int,
        focus_duration: int = 0,
    ) -> int:
        """
        세션 기록을 기반으로 포인트를 지급한다.
        - 집중 시간 5분당 1포인트
        - 완료한 사이클 1회당 3포인트
        - 각 사이클의 집중 분량(focus_duration)이 길수록 1포인트 추가 보너스
        """
        if total_focus_minutes <= 0 and completed_cycles <= 0:
            return 0

        focus_points = max(total_focus_minutes // 5, 0)
        cycle_points = max(completed_cycles, 0) * 3
        duration_bonus = max(completed_cycles, 0) * max(focus_duration // 25, 0)
        earned = focus_points + cycle_points + duration_bonus

        self.state.points += earned
        self._save_state()
        return earned

    def buy_scroll(self, quantity: int = 1, cost_per_scroll: int = 40) -> bool:
        """포인트로 강화 스크롤을 구매한다."""
        if quantity <= 0:
            return False
        total_cost = quantity * cost_per_scroll
        if self.state.points < total_cost:
            return False

        self.state.points -= total_cost
        self.state.scrolls += quantity
        self._save_state()
        return True

    # --- 강화 ---
    def _success_rate(self, enhancement_level: int) -> float:
        """
        현재 강화 단계에 따른 성공 확률을 반환.
        0강: 90%에서 시작, 단계당 8%씩 감소, 최소 15%.
        """
        return max(0.9 - (enhancement_level * 0.08), 0.15)

    def _downgrade_rate(self, enhancement_level: int) -> float:
        """
        실패 시 하락 확률.
        0~1강: 0%
        2강부터 단계당 3%p씩 증가, 최대 20%
        """
        if enhancement_level <= 1:
            return 0.0
        return min(0.03 * (enhancement_level - 1), 0.20)

    def get_enhance_rates(self, slot: str) -> Dict[str, float]:
        item = self.state.inventory.get(slot)
        if item is None:
            return {"success": 0.0, "downgrade": 0.0}
        level = item.enhancement
        return {
            "success": round(self._success_rate(level) * 100, 1),
            "downgrade": round(self._downgrade_rate(level) * 100, 1),
        }

    def enhance(self, slot: str) -> Optional[EnhancementResult]:
        """특정 장비를 강화한다. 스크롤 1장을 소모."""
        item = self.state.inventory.get(slot)
        if item is None or self.state.scrolls <= 0:
            return None

        before = item.enhancement
        rate = self._success_rate(before)
        downgrade_rate = self._downgrade_rate(before)
        self.state.scrolls -= 1
        success = random.random() <= rate
        downgraded = False

        if success:
            item.enhancement += 1
            after = item.enhancement
        else:
            # 실패 시 하락 판정
            if item.enhancement > 0 and random.random() <= downgrade_rate:
                item.enhancement -= 1
                downgraded = True
            after = item.enhancement

        self._save_state()
        return EnhancementResult(
            slot=slot,
            success=success,
            before_level=before,
            after_level=after,
            success_rate=round(rate * 100, 1),
            downgraded=downgraded,
        )

    # --- 스테이지 ---
    def _power_requirement(self, next_stage: int) -> int:
        """
        다음 스테이지 요구 전투력.
        2스테이지부터 30, 이후 스테이지마다 10씩 증가.
        """
        base_requirement = 30
        if next_stage <= 2:
            return base_requirement
        return base_requirement + (next_stage - 2) * 10

    def _stage_hp(self, next_stage: int) -> int:
        """
        스테이지 HP 산정.
        요구 전투력 * 10을 기준 HP로 사용해 기본 전투력과 비슷한 난이도로 설정.
        """
        return self._power_requirement(next_stage) * 10

    def total_power(self) -> float:
        return round(sum(item.power for item in self.state.inventory.values()), 2)

    def try_auto_advance(self) -> Optional[int]:
        """
        현재 전투력으로 도달 가능한 만큼 스테이지를 올린다.
        반환값: 상승 후 최종 스테이지 번호, 상승이 없으면 None.
        """
        advanced = False
        while True:
            target_stage = self.state.stage + 1
            if self.total_power() >= self._power_requirement(target_stage):
                self.state.stage = target_stage
                advanced = True
            else:
                break

        if advanced:
            self._save_state()
            return self.state.stage
        return None

    # --- 전투 (단일 타격) ---
    def _reset_battle(self):
        self.battle_state = None

    def start_stage_battle(self) -> Dict[str, Any]:
        target_stage = self.state.stage + 1
        hp = self._stage_hp(target_stage)
        self.battle_state = {
            "target_stage": target_stage,
            "hp": hp,
            "remaining_hp": float(hp),
            "hits_used": 0,
            "limit": 10,
            "log": [],
        }
        return self.battle_state.copy()

    def hit_stage_battle(self, variance: float = 0.3) -> Dict[str, Any]:
        """
        단일 타격을 수행한다. 필요 시 자동으로 전투를 시작한다.
        반환값: 현재 타격 결과 및 전투 종료 여부.
        """
        if self.battle_state is None or self.battle_state.get("hits_used", 0) >= self.battle_state.get("limit", 10) or self.battle_state.get("remaining_hp", 0) <= 0:
            self.start_stage_battle()

        total_power = self.total_power()
        factor = random.uniform(1 - variance, 1 + variance)
        dmg = round(total_power * factor, 1)

        self.battle_state["hits_used"] += 1
        self.battle_state["remaining_hp"] -= dmg
        self.battle_state["log"].append(
            {
                "hit": self.battle_state["hits_used"],
                "damage": dmg,
                "factor": round(factor, 3),
            }
        )

        success = self.battle_state["remaining_hp"] <= 0
        finished = success or self.battle_state["hits_used"] >= self.battle_state["limit"]

        result = {
            "success": success,
            "finished": finished,
            "target_stage": self.battle_state["target_stage"],
            "hp": self.battle_state["hp"],
            "remaining_hp": round(self.battle_state["remaining_hp"], 1),
            "hit_index": self.battle_state["hits_used"],
            "hit_damage": dmg,
            "factor": round(factor, 3),
            "total_power": total_power,
            "hits_used": self.battle_state["hits_used"],
            "limit": self.battle_state["limit"],
        }

        if finished:
            if success:
                self.state.stage = self.battle_state["target_stage"]
                self._save_state()
            self._reset_battle()

        return result

    def get_battle_status(self) -> Dict[str, Any]:
        if self.battle_state is None:
            return {
                "in_progress": False,
                "target_stage": self.state.stage + 1,
                "hp": self._stage_hp(self.state.stage + 1),
                "remaining_hp": None,
                "hits_used": 0,
                "limit": 10,
            }
        return {
            "in_progress": True,
            "target_stage": self.battle_state["target_stage"],
            "hp": self.battle_state["hp"],
            "remaining_hp": round(self.battle_state["remaining_hp"], 1),
            "hits_used": self.battle_state["hits_used"],
            "limit": self.battle_state["limit"],
        }

    # --- 조회 ---
    def snapshot(self) -> Dict:
        """UI/로그용 요약 데이터를 반환."""
        return {
            "points": self.state.points,
            "stage": self.state.stage,
            "scrolls": self.state.scrolls,
            "inventory": {
                k: {
                    "level": v.enhancement,
                    "power": v.power,
                    "base_power": v.base_power,
                }
                for k, v in self.state.inventory.items()
            },
            "total_power": self.total_power(),
            "next_stage_requirement": self._power_requirement(self.state.stage + 1),
        }

