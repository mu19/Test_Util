"""
Log Window for Log Collector

실시간 도구 로그 메시지 출력 윈도우
"""

import wx
from datetime import datetime


class LogWindow(wx.Frame):
    """실시간 로그 출력 윈도우"""

    def __init__(self, parent):
        """
        초기화

        Args:
            parent: 부모 윈도우
        """
        super().__init__(parent, title="로그 메시지", size=(800, 600))

        # 기본 폰트
        self.default_font = wx.Font(9, wx.FONTFAMILY_TELETYPE,
                                     wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.init_ui()
        self.Centre()

    def init_ui(self):
        """UI 초기화"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 로그 출력 영역 (읽기 전용이지만 복사 가능)
        self.log_text = wx.TextCtrl(panel,
                                     style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.log_text.SetFont(self.default_font)
        self.log_text.SetEditable(False)  # 수정 불가
        main_sizer.Add(self.log_text, 1, wx.ALL | wx.EXPAND, 5)

        # 버튼 영역
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        clear_btn = wx.Button(panel, label="지우기")
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        btn_sizer.Add(clear_btn, 0, wx.RIGHT, 5)

        save_btn = wx.Button(panel, label="저장")
        save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        btn_sizer.Add(save_btn, 0)

        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 5)

        panel.SetSizer(main_sizer)

    def append_log(self, message, level="INFO"):
        """
        로그 메시지 추가

        Args:
            message: 로그 메시지
            level: 로그 레벨 (INFO, WARNING, ERROR, DEBUG)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] [{level}] {message}\n"

        # 색상 설정
        color = self.get_level_color(level)

        # 메시지 추가
        self.log_text.SetDefaultStyle(wx.TextAttr(color))
        self.log_text.AppendText(log_line)

        # 자동 스크롤
        self.log_text.SetInsertionPointEnd()

    def get_level_color(self, level):
        """로그 레벨별 색상 반환"""
        colors = {
            "DEBUG": wx.Colour(128, 128, 128),  # 회색
            "INFO": wx.Colour(0, 0, 0),         # 검정
            "WARNING": wx.Colour(255, 140, 0),  # 주황
            "ERROR": wx.Colour(255, 0, 0),      # 빨강
            "SUCCESS": wx.Colour(0, 128, 0)     # 녹색
        }
        return colors.get(level, wx.Colour(0, 0, 0))

    def on_clear(self, event):
        """로그 지우기"""
        result = wx.MessageBox("로그를 모두 지우시겠습니까?", "확인",
                              wx.YES_NO | wx.ICON_QUESTION)
        if result == wx.YES:
            self.log_text.Clear()

    def on_save(self, event):
        """로그 파일로 저장"""
        wildcard = "텍스트 파일 (*.txt)|*.txt|모든 파일 (*.*)|*.*"
        dlg = wx.FileDialog(self, "로그 저장",
                           defaultFile=f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                           wildcard=wildcard,
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            try:
                path = dlg.GetPath()
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.GetValue())
                wx.MessageBox("로그가 저장되었습니다.", "저장 완료",
                            wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f"로그 저장 실패:\n{str(e)}", "오류",
                            wx.OK | wx.ICON_ERROR)
        dlg.Destroy()
