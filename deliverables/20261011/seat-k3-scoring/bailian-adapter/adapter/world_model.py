"""world_model.py —— 世界模型接口位（支持实时交互的开放式世界模型）。

三类运行模式（与 world/index.html 观展台前端一致）：
    EXPLORE  世界探索  —— 自由轨道巡游，状态拉取
    DIRECT   实时导演  —— 机位/灯光 cue 事件下发
    ROLEPLAY 角色演绎  —— 人设驱动行为与台词事件

诚实边界：百炼侧暂无现成「实时交互世界模型」单品，本模块定义事件协议与
本地回退（LocalWorldBackend，对接观展台前端状态机）；远端后端待服务选定后
实装，接口不变。决不自称已接通外部世界模型服务。
"""
from __future__ import annotations
import enum, time
from .telemetry import Telemetry


class WorldMode(enum.Enum):
    EXPLORE = "世界探索"
    DIRECT = "实时导演"
    ROLEPLAY = "角色演绎"


class LocalWorldBackend:
    """本地回退后端：世界状态内存态（与观展台三模式一一对应）。"""

    def __init__(self):
        self.state = {"mode": WorldMode.EXPLORE.value,
                      "camera": {"shot": "wide"},
                      "lighting": {"cue": "star"},
                      "persona": {"line_idx": 0}}
        self.events: list[dict] = []

    def apply(self, event: dict) -> dict:
        et = event.get("type")
        if et == "set_mode":
            m = WorldMode(event["mode"])  # 非法值在此抛 ValueError
            self.state["mode"] = m.value
        elif et == "camera_shot":
            self.state["camera"]["shot"] = event["shot"]
        elif et == "lighting_cue":
            self.state["lighting"]["cue"] = event["cue"]
        elif et == "persona_line":
            self.state["persona"]["line_idx"] = int(event["line_idx"])
        else:
            raise ValueError(f"未知事件类型：{et!r}")
        self.events.append({"ts": time.time(), **event})
        return dict(self.state)


class WorldModelClient:
    """世界模型客户端：模式切换 / 导演 cue / 演绎事件 / 状态拉取。"""

    def __init__(self, backend=None, telemetry: Telemetry | None = None):
        self.backend = backend or LocalWorldBackend()
        self.tel = telemetry or Telemetry()

    def _apply(self, endpoint: str, event: dict) -> dict:
        t0 = time.perf_counter()
        try:
            state = self.backend.apply(event)
        except Exception:
            self.tel.record(f"world.{endpoint}", False,
                            (time.perf_counter() - t0) * 1000)
            raise
        self.tel.record(f"world.{endpoint}", True, (time.perf_counter() - t0) * 1000)
        return state

    def explore(self) -> dict:
        """世界探索：切模式并拉取当前世界状态。"""
        return self._apply("explore", {"type": "set_mode", "mode": "世界探索"})

    def direct(self, shot: str | None = None, cue: str | None = None) -> dict:
        """实时导演：机位与灯光 cue 即时下发。"""
        self._apply("direct.mode", {"type": "set_mode", "mode": "实时导演"})
        if shot:
            self._apply("direct.shot", {"type": "camera_shot", "shot": shot})
        if cue:
            self._apply("direct.cue", {"type": "lighting_cue", "cue": cue})
        return self.state()

    def roleplay(self, line_idx: int = 0) -> dict:
        """角色演绎：人设台词/行为事件。"""
        self._apply("role.mode", {"type": "set_mode", "mode": "角色演绎"})
        return self._apply("role.line", {"type": "persona_line", "line_idx": line_idx})

    def state(self) -> dict:
        return dict(self.backend.state) if hasattr(self.backend, "state") else {}
