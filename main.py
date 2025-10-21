"""
Log Collector Main Application

로그 수집 유틸리티 메인 진입점
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import wx
from ui.main_frame import MainFrame
from utils.logger import setup_logger, LOG_LEVEL_INFO
from config.settings import SettingsManager

# 로거 설정
logger = setup_logger(log_level=LOG_LEVEL_INFO)


class LogCollectorApp(wx.App):
    """로그 수집 애플리케이션"""

    def OnInit(self):
        """애플리케이션 초기화"""
        logger.info("="*60)
        logger.info("로그 수집 유틸리티 시작")
        logger.info("="*60)

        # 설정 초기화
        settings = SettingsManager()
        logger.info(f"설정 파일 로드 완료")

        # 메인 프레임 생성
        self.frame = MainFrame()
        self.frame.Show()

        logger.info("메인 윈도우 표시 완료")

        return True

    def OnExit(self):
        """애플리케이션 종료"""
        logger.info("="*60)
        logger.info("로그 수집 유틸리티 종료")
        logger.info("="*60)
        return 0


def main():
    """메인 함수"""
    try:
        app = LogCollectorApp()
        app.MainLoop()
        return 0

    except Exception as e:
        logger.exception(f"애플리케이션 오류: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
