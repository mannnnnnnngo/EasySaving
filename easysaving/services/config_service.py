"""설정 저장/불러오기. 손상된 파일이 있어도 앱이 죽지 않게 항상 기본값으로 복구한다."""

import json
import os
import tempfile

from ..core.models import Settings
from ..platform_layer import paths


class ConfigService:
    def __init__(self, path=None):
        self.path = path or paths.config_path()
        self.settings = Settings()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            self.settings = Settings.from_dict(data)
        except FileNotFoundError:
            self.settings = Settings()
        except Exception:
            # 손상된 설정은 백업해 두고 기본값으로 시작
            try:
                os.replace(self.path, self.path + ".broken")
            except Exception:
                pass
            self.settings = Settings()
        return self.settings

    def save(self):
        """원자적 저장 — 쓰다가 앱이 꺼져도 기존 설정이 깨지지 않는다."""
        data = self.settings.clamped().to_dict()
        directory = os.path.dirname(self.path)
        try:
            os.makedirs(directory, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=directory, prefix=".cfg", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
            return True
        except Exception:
            return False

    def reset(self):
        self.settings = Settings()
        self.save()
        return self.settings
