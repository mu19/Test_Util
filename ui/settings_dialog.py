"""
Settings Dialog for Log Collector

설정 다이얼로그 구현
"""

import wx
from core.models import LogSourceType
from config.settings import SettingsManager
from utils.validators import validate_ip_address, validate_port, validate_path
from utils.logger import get_logger

logger = get_logger("SettingsDialog")


class SettingsDialog(wx.Dialog):
    """설정 다이얼로그"""

    def __init__(self, parent):
        logger.info("SettingsDialog 초기화 시작")
        super().__init__(parent, title="설정", size=(600, 500))

        self.settings = SettingsManager()
        logger.info("SettingsManager 로드 완료")

        # 기본 폰트 설정
        self.default_font = wx.Font(9, wx.FONTFAMILY_DEFAULT,
                                     wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.init_ui()
        logger.info("UI 초기화 완료")

        self.load_settings()
        logger.info("설정 로드 완료")

        self.Centre()
        logger.info("SettingsDialog 초기화 완료")

    def init_ui(self):
        """UI 초기화"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 탭 컨트롤
        notebook = wx.Notebook(panel)

        # SSH 설정 탭
        self.ssh_panel = self.create_ssh_panel(notebook)
        notebook.AddPage(self.ssh_panel, "SSH 설정")

        # 로그 경로 설정 탭
        self.path_panel = self.create_path_panel(notebook)
        notebook.AddPage(self.path_panel, "로그 경로")

        # 일반 설정 탭
        self.general_panel = self.create_general_panel(notebook)
        notebook.AddPage(self.general_panel, "일반")

        main_sizer.Add(notebook, 1, wx.ALL | wx.EXPAND, 10)

        # 버튼
        btn_sizer = wx.StdDialogButtonSizer()

        ok_btn = wx.Button(panel, wx.ID_OK, "확인")
        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        btn_sizer.AddButton(ok_btn)

        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "취소")
        cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_sizer.AddButton(cancel_btn)

        btn_sizer.Realize()
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

        panel.SetSizer(main_sizer)

    def create_ssh_panel(self, parent):
        """SSH 설정 패널 생성"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # SSH 기본 설정
        ssh_box = wx.StaticBox(panel, label="SSH 기본 설정")
        ssh_sizer = wx.StaticBoxSizer(ssh_box, wx.VERTICAL)

        # Username
        username_sizer = wx.BoxSizer(wx.HORIZONTAL)
        username_sizer.Add(wx.StaticText(panel, label="사용자 이름:"), 0,
                          wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.username_ctrl = wx.TextCtrl(panel, size=(200, -1))
        username_sizer.Add(self.username_ctrl, 1, wx.EXPAND)
        ssh_sizer.Add(username_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Password
        password_sizer = wx.BoxSizer(wx.HORIZONTAL)
        password_sizer.Add(wx.StaticText(panel, label="비밀번호:"), 0,
                          wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.password_ctrl = wx.TextCtrl(panel, size=(200, -1),
                                        style=wx.TE_PASSWORD)
        password_sizer.Add(self.password_ctrl, 1, wx.EXPAND)
        ssh_sizer.Add(password_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Timeout
        timeout_sizer = wx.BoxSizer(wx.HORIZONTAL)
        timeout_sizer.Add(wx.StaticText(panel, label="타임아웃 (초):"), 0,
                         wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.timeout_ctrl = wx.SpinCtrl(panel, value="300",
                                       min=10, max=3600, initial=300)
        timeout_sizer.Add(self.timeout_ctrl, 0)
        ssh_sizer.Add(timeout_sizer, 0, wx.ALL, 5)

        # Keep-alive
        self.keepalive_check = wx.CheckBox(panel,
                                          label="Keep-alive 사용 (연결 유지)")
        self.keepalive_check.SetValue(True)
        ssh_sizer.Add(self.keepalive_check, 0, wx.ALL, 5)

        # Keep-alive interval
        interval_sizer = wx.BoxSizer(wx.HORIZONTAL)
        interval_sizer.Add(wx.StaticText(panel, label="Keep-alive 간격 (초):"), 0,
                          wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.keepalive_interval_ctrl = wx.SpinCtrl(panel, value="60",
                                                   min=10, max=300, initial=60)
        interval_sizer.Add(self.keepalive_interval_ctrl, 0)
        ssh_sizer.Add(interval_sizer, 0, wx.ALL, 5)

        sizer.Add(ssh_sizer, 0, wx.ALL | wx.EXPAND, 10)

        # 설명
        help_text = wx.StaticText(panel,
            label="SSH 연결시 사용할 기본 설정입니다.\n"
                  "실제 연결시에는 IP 주소와 포트를 입력해야 합니다.")
        help_text.SetFont(self.default_font)
        help_text.SetForegroundColour(wx.Colour(100, 100, 100))
        sizer.Add(help_text, 0, wx.ALL, 10)

        panel.SetSizer(sizer)
        return panel

    def create_path_panel(self, parent):
        """로그 경로 설정 패널 생성"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # 각 로그 소스별 경로 설정
        self.path_ctrls = {}

        # 커널 로그
        self.path_ctrls[LogSourceType.LINUX_KERNEL] = self.create_path_section(
            panel, sizer, "제어기 커널 로그 경로", LogSourceType.LINUX_KERNEL,
            "리눅스 커널 로그 파일 경로 (예: /var/log)"
        )

        # 서버 로그
        self.path_ctrls[LogSourceType.LINUX_SERVER] = self.create_path_section(
            panel, sizer, "제어기 로그 경로", LogSourceType.LINUX_SERVER,
            "서버 애플리케이션 로그 디렉토리 경로(예: /home/user/log)"
        )

        # 윈도우 클라이언트 로그
        self.path_ctrls[LogSourceType.WINDOWS_CLIENT] = self.create_path_section(
            panel, sizer, "사용자 SW 로그 경로", LogSourceType.WINDOWS_CLIENT,
            "윈도우 클라이언트 로그 디렉토리 경로 (예: C:\\Logs)"
        )

        panel.SetSizer(sizer)
        return panel

    def create_path_section(self, panel, parent_sizer, title, log_type, help_text):
        """경로 설정 섹션 생성"""
        box = wx.StaticBox(panel, label=title)
        box_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        # 경로 입력
        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_ctrl = wx.TextCtrl(panel)
        path_sizer.Add(path_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        # 찾아보기 버튼 (로컬 경로만 표시)
        if log_type == LogSourceType.WINDOWS_CLIENT:
            browse_btn = wx.Button(panel, label="찾아보기...")
            browse_btn.Bind(wx.EVT_BUTTON,
                           lambda e: self.on_browse_path(log_type))
            path_sizer.Add(browse_btn, 0)

        box_sizer.Add(path_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # 도움말 텍스트
        help_label = wx.StaticText(panel, label=help_text)
        help_label.SetFont(self.default_font)
        help_label.SetForegroundColour(wx.Colour(100, 100, 100))
        box_sizer.Add(help_label, 0, wx.ALL, 5)

        parent_sizer.Add(box_sizer, 0, wx.ALL | wx.EXPAND, 5)

        return path_ctrl

    def create_general_panel(self, parent):
        """일반 설정 패널 생성"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # 저장 경로
        save_box = wx.StaticBox(panel, label="기본 저장 경로")
        save_sizer = wx.StaticBoxSizer(save_box, wx.VERTICAL)

        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.save_path_ctrl = wx.TextCtrl(panel)
        path_sizer.Add(self.save_path_ctrl, 1,
                      wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        browse_btn = wx.Button(panel, label="찾아보기...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse_save_path)
        path_sizer.Add(browse_btn, 0)

        save_sizer.Add(path_sizer, 0, wx.ALL | wx.EXPAND, 5)

        help_text = wx.StaticText(panel,
            label="수집한 로그 파일을 저장할 기본 디렉토리입니다.")
        help_text.SetFont(self.default_font)
        help_text.SetForegroundColour(wx.Colour(100, 100, 100))
        save_sizer.Add(help_text, 0, wx.ALL, 5)

        sizer.Add(save_sizer, 0, wx.ALL | wx.EXPAND, 10)

        # 압축 설정
        compress_box = wx.StaticBox(panel, label="압축 설정")
        compress_sizer = wx.StaticBoxSizer(compress_box, wx.VERTICAL)

        self.compress_default_check = wx.CheckBox(panel,
                                                  label="기본적으로 압축 사용")
        self.compress_default_check.SetValue(False)
        compress_sizer.Add(self.compress_default_check, 0, wx.ALL, 5)

        compress_help = wx.StaticText(panel,
            label="파일 수집시 자동으로 압축할지 여부의 기본값입니다.")
        compress_help.SetFont(self.default_font)
        compress_help.SetForegroundColour(wx.Colour(100, 100, 100))
        compress_sizer.Add(compress_help, 0, wx.ALL, 5)

        sizer.Add(compress_sizer, 0, wx.ALL | wx.EXPAND, 10)

        # 삭제 설정
        delete_box = wx.StaticBox(panel, label="삭제 설정")
        delete_sizer = wx.StaticBoxSizer(delete_box, wx.VERTICAL)

        self.delete_default_check = wx.CheckBox(panel,
                                                label="기본적으로 원본 파일 삭제")
        self.delete_default_check.SetValue(False)
        delete_sizer.Add(self.delete_default_check, 0, wx.ALL, 5)

        delete_help = wx.StaticText(panel,
            label="파일 수집 후 원본 파일을 삭제할지 여부의 기본값입니다.\n"
                  "주의: 이 옵션을 사용하면 원본 파일이 삭제됩니다!")
        delete_help.SetFont(self.default_font)
        delete_help.SetForegroundColour(wx.Colour(200, 0, 0))
        delete_sizer.Add(delete_help, 0, wx.ALL, 5)

        sizer.Add(delete_sizer, 0, wx.ALL | wx.EXPAND, 10)

        panel.SetSizer(sizer)
        return panel

    def on_browse_path(self, log_type):
        """경로 찾아보기"""
        path_ctrl = self.path_ctrls[log_type]
        current_path = path_ctrl.GetValue()

        if log_type == LogSourceType.WINDOWS_CLIENT:
            # 윈도우 경로는 디렉토리 선택
            dlg = wx.DirDialog(self, "디렉토리 선택",
                              defaultPath=current_path if current_path else "")
        else:
            # 리눅스 경로는 텍스트 입력 (원격이므로)
            dlg = wx.TextEntryDialog(self, "원격 경로 입력:", "경로 설정",
                                    value=current_path if current_path else "")

        if dlg.ShowModal() == wx.ID_OK:
            if log_type == LogSourceType.WINDOWS_CLIENT:
                path_ctrl.SetValue(dlg.GetPath())
            else:
                path_ctrl.SetValue(dlg.GetValue())

        dlg.Destroy()

    def on_browse_save_path(self, event):
        """저장 경로 찾아보기"""
        current_path = self.save_path_ctrl.GetValue()

        dlg = wx.DirDialog(self, "저장 디렉토리 선택",
                          defaultPath=current_path if current_path else "")

        if dlg.ShowModal() == wx.ID_OK:
            self.save_path_ctrl.SetValue(dlg.GetPath())

        dlg.Destroy()

    def load_settings(self):
        """설정 로드"""
        # SSH 설정
        ssh_config = self.settings.get_ssh_config()
        self.username_ctrl.SetValue(ssh_config.username)
        self.password_ctrl.SetValue(ssh_config.password)
        self.timeout_ctrl.SetValue(ssh_config.timeout)
        self.keepalive_check.SetValue(ssh_config.keep_alive)
        self.keepalive_interval_ctrl.SetValue(ssh_config.keep_alive_interval)

        # 로그 경로
        for log_type, path_ctrl in self.path_ctrls.items():
            config = self.settings.get_log_source_config(log_type)
            path_ctrl.SetValue(config.path)

        # 일반 설정
        self.save_path_ctrl.SetValue(self.settings.get_save_path())

        # 압축/삭제 기본값은 설정에서 로드
        # (현재는 각 로그 소스별로 설정되어 있으므로 첫 번째 값 사용)
        kernel_config = self.settings.get_log_source_config(LogSourceType.LINUX_KERNEL)
        self.compress_default_check.SetValue(kernel_config.compress)
        self.delete_default_check.SetValue(kernel_config.delete_after)

    def validate_settings(self):
        """설정 유효성 검사"""
        try:
            # Username 검증
            username = self.username_ctrl.GetValue().strip()
            if not username:
                wx.MessageBox("사용자 이름을 입력하세요.", "입력 오류",
                             wx.OK | wx.ICON_ERROR)
                return False

            # Timeout 검증
            timeout = self.timeout_ctrl.GetValue()
            if timeout < 10:
                wx.MessageBox("타임아웃은 최소 10초 이상이어야 합니다.", "입력 오류",
                             wx.OK | wx.ICON_ERROR)
                return False

            # 경로 검증
            for log_type, path_ctrl in self.path_ctrls.items():
                path = path_ctrl.GetValue().strip()
                if not path:
                    type_name = {
                        LogSourceType.LINUX_KERNEL: "커널 로그",
                        LogSourceType.LINUX_SERVER: "서버 로그",
                        LogSourceType.WINDOWS_CLIENT: "클라이언트 로그"
                    }[log_type]
                    wx.MessageBox(f"{type_name} 경로를 입력하세요.", "입력 오류",
                                wx.OK | wx.ICON_ERROR)
                    return False

                # 윈도우 경로만 유효성 검사 (원격 경로는 실제 연결시 확인)
                if log_type == LogSourceType.WINDOWS_CLIENT:
                    is_valid, msg = validate_path(path)
                    if not is_valid:
                        wx.MessageBox(f"클라이언트 로그 경로 오류:\n{msg}",
                                    "입력 오류", wx.OK | wx.ICON_ERROR)
                        return False

            # 저장 경로 검증
            save_path = self.save_path_ctrl.GetValue().strip()
            if not save_path:
                wx.MessageBox("저장 경로를 입력하세요.", "입력 오류",
                             wx.OK | wx.ICON_ERROR)
                return False

            is_valid, msg = validate_path(save_path)
            if not is_valid:
                wx.MessageBox(f"저장 경로 오류:\n{msg}", "입력 오류",
                             wx.OK | wx.ICON_ERROR)
                return False

            logger.info("설정 유효성 검사 통과")
            return True

        except Exception as e:
            logger.exception(f"설정 유효성 검사 중 오류: {e}")
            wx.MessageBox(f"설정 검증 중 오류가 발생했습니다:\n{str(e)}",
                         "검증 오류", wx.OK | wx.ICON_ERROR)
            return False

    def save_settings(self):
        """설정 저장"""
        # SSH 설정 업데이트
        self.settings.update_config("ssh.username", self.username_ctrl.GetValue().strip())
        self.settings.update_config("ssh.password", self.password_ctrl.GetValue())
        self.settings.update_config("ssh.timeout", self.timeout_ctrl.GetValue())
        self.settings.update_config("ssh.keep_alive", self.keepalive_check.GetValue())
        self.settings.update_config("ssh.keep_alive_interval", self.keepalive_interval_ctrl.GetValue())

        # 로그 경로 업데이트
        for log_type, path_ctrl in self.path_ctrls.items():
            type_key = log_type.value
            self.settings.update_config(f"log_sources.{type_key}.path", path_ctrl.GetValue().strip())

        # 일반 설정 업데이트
        self.settings.set_save_path(self.save_path_ctrl.GetValue().strip())

        # 압축/삭제 기본값 업데이트 (모든 로그 소스에 적용)
        compress_default = self.compress_default_check.GetValue()
        delete_default = self.delete_default_check.GetValue()

        for log_type in LogSourceType:
            type_key = log_type.value
            self.settings.update_config(f"log_sources.{type_key}.compress", compress_default)
            self.settings.update_config(f"log_sources.{type_key}.delete_after", delete_default)

        # 파일에 저장
        self.settings.save()
        logger.info("설정 저장 완료")

    def on_ok(self, event):
        """확인 버튼"""
        # 설정 유효성 검사
        if not self.validate_settings():
            return

        # 저장 확인
        result = wx.MessageBox(
            "변경된 설정을 저장하시겠습니까?",
            "설정 저장 확인",
            wx.YES_NO | wx.ICON_QUESTION
        )

        if result == wx.YES:
            try:
                self.save_settings()
                wx.MessageBox("설정이 저장되었습니다.", "저장 완료",
                             wx.OK | wx.ICON_INFORMATION)
                self.EndModal(wx.ID_OK)
            except Exception as e:
                logger.exception(f"설정 저장 실패: {e}")
                wx.MessageBox(f"설정 저장 중 오류가 발생했습니다:\n{str(e)}",
                             "저장 오류", wx.OK | wx.ICON_ERROR)
        else:
            # 저장하지 않고 닫기
            result = wx.MessageBox(
                "저장하지 않고 닫으시겠습니까?\n변경사항이 손실됩니다.",
                "확인",
                wx.YES_NO | wx.ICON_WARNING
            )
            if result == wx.YES:
                self.EndModal(wx.ID_CANCEL)

    def on_cancel(self, event):
        """취소 버튼"""
        self.EndModal(wx.ID_CANCEL)
