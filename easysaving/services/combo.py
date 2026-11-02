"""버튼 이동 조합키(modifier + 마우스 버튼) 판정.

Tk 의 event.state 비트는 OS 마다 다르다. 그래서 OS 별 표를 두고,
설정의 '조합키 녹화' 는 사용자가 실제로 누른 것을 그대로 저장한다.
"""

import sys

from ..core.models import MODIFIER_LABELS, BUTTON_LABELS, MoveCombo

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")

# modifier 이름 -> event.state 에서 확인할 비트들 (여러 개면 OR 로 판정)
if IS_MAC:
    _MASKS = {
        "shift": (0x0001,),
        "ctrl": (0x0004,),
        "cmd": (0x0008,),   # ⌘ Command = Mod1
        "alt": (0x0010,),   # ⌥ Option  = Mod2
    }
elif IS_WIN:
    _MASKS = {
        "shift": (0x0001,),
        "ctrl": (0x0004,),
        "alt": (0x20000,),
        "cmd": (0x0008,),   # Windows 키 (Tk 가 항상 주지는 않는다)
    }
else:
    _MASKS = {
        "shift": (0x0001,),
        "ctrl": (0x0004,),
        "alt": (0x0008,),
        "cmd": (0x0040,),
    }

# macOS 는 Tk 버전에 따라 오른쪽 버튼을 2 또는 3 으로 보고한다.
_EQUIVALENT_BUTTONS = {2: {2, 3}, 3: {2, 3}} if IS_MAC else {}


def modifiers_from_state(state):
    """event.state 정수 -> ['alt', 'shift'] 같은 목록."""
    try:
        state = int(state)
    except (TypeError, ValueError):
        return []
    return [name for name, masks in _MASKS.items() if any(state & mask for mask in masks)]


def matches(combo: MoveCombo, state, button):
    """이 이벤트가 조합키와 정확히 일치하는가 (남는 modifier 가 있으면 불일치)."""
    wanted = set(combo.modifiers or [])
    pressed = set(modifiers_from_state(state))
    if wanted != pressed:
        return False
    allowed = _EQUIVALENT_BUTTONS.get(combo.button, {combo.button})
    return button in allowed


def describe(combo: MoveCombo):
    """'⌥ Option(Alt) + 마우스 오른쪽 클릭' 처럼 사람이 읽는 문자열."""
    order = ["ctrl", "alt", "shift", "cmd"]
    mods = [MODIFIER_LABELS[m] for m in order if m in (combo.modifiers or [])]
    button = BUTTON_LABELS.get(combo.button, f"마우스 버튼 {combo.button}")
    return " + ".join(mods + [button]) if mods else button


def describe_short(combo: MoveCombo):
    short = {"shift": "Shift", "ctrl": "Ctrl", "alt": "Option" if IS_MAC else "Alt",
             "cmd": "Cmd" if IS_MAC else "Win"}
    order = ["ctrl", "alt", "shift", "cmd"]
    mods = [short[m] for m in order if m in (combo.modifiers or [])]
    button = {1: "좌클릭", 2: "우클릭" if IS_MAC else "휠클릭", 3: "우클릭"}.get(combo.button, "클릭")
    return " + ".join(mods + [button])


def is_valid(combo: MoveCombo):
    """실수로 '아무 수식키 없이 좌클릭' 같은 위험한 조합을 저장하지 못하게 한다."""
    if combo.button == 1 and not combo.modifiers:
        return False, "왼쪽 클릭만으로는 지정할 수 없어요. Alt 같은 키를 함께 눌러 주세요."
    if combo.button not in (1, 2, 3):
        return False, "마우스 왼쪽 / 가운데 / 오른쪽 버튼 중 하나를 눌러 주세요."
    return True, ""
