"""더블클릭용 시작 파일 — .pyw 는 pythonw 로 열려서 콘솔 창이 뜨지 않는다."""

import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.py"), run_name="__main__")
