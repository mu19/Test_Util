"""
Main Frame for Log Collector

메인 윈도우 구현
"""

import wx
import threading
from typing import Optional

from core.models import SSHConfig, LogSourceType, LogSourceConfig, CancelToken, ProgressInfo
from core.ssh_manager import SSHManager, SSHConnectionError
from core.file_collector import FileCollector
from config.settings import SettingsManager
from utils.logger import get_logger

logger = get_logger("MainFrame")


class MainFrame(wx.Frame):
    """메인 프레임"""

    def __init__(self):
        super().__init__(None, title="로그 수집 유틸리티",
                        size=(1000, 800),
                        style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))

        self.settings = SettingsManager()
        self.ssh_manager = SSHManager()
        self.file_collector = FileCollector(self.ssh_manager)
        self.cancel_token = CancelToken()

        self.ssh_connected = False
        self.downloading = False
        self.connecting = False  # 연결 시도 중 플래그

        # 기본 폰트 설정 (일관성 있는 폰트 사용)
        self.default_font = wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        # 로그 윈도우
        self.log_window = None
        self.log_buffer = []  # 로그 버퍼 (윈도우가 열리기 전 메시지 저장)

        self.init_ui()
        self.Centre()
        self.CreateStatusBar()
        self.update_status_bar()

        logger.info("MainFrame 초기화 완료")
        self.log_message("로그 수집 유틸리티 시작", "INFO")

    def init_ui(self):
        """UI 초기화"""
        # 메뉴바
        self.create_menubar()

        # 메인 패널
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # SSH 연결 그룹
        self.create_ssh_section(panel, main_sizer)

        # 로그 수집 설정 그룹
        self.create_log_sections(panel, main_sizer)

        # 진행 상황 그룹
        self.create_progress_section(panel, main_sizer)

        panel.SetSizer(main_sizer)

    def create_menubar(self):
        """메뉴바 생성"""
        menubar = wx.MenuBar()

        # 파일 메뉴
        file_menu = wx.Menu()
        exit_item = file_menu.Append(wx.ID_EXIT, "종료\tCtrl+Q")
        self.Bind(wx.EVT_MENU, self.on_quit, exit_item)
        menubar.Append(file_menu, "파일(&F)")

        # 보기 메뉴
        view_menu = wx.Menu()
        log_window_item = view_menu.Append(wx.ID_ANY, "로그 메시지\tCtrl+L")
        self.Bind(wx.EVT_MENU, self.on_show_log_window, log_window_item)
        menubar.Append(view_menu, "보기(&V)")

        # 설정 메뉴
        settings_menu = wx.Menu()
        settings_item = settings_menu.Append(wx.ID_ANY, "설정\tCtrl+S")
        self.Bind(wx.EVT_MENU, self.on_settings, settings_item)
        menubar.Append(settings_menu, "설정(&S)")

        self.SetMenuBar(menubar)

    def create_ssh_section(self, panel, parent_sizer):
        """SSH 연결 섹션 생성"""
        ssh_box = wx.StaticBox(panel, label="SSH 연결")
        ssh_sizer = wx.StaticBoxSizer(ssh_box, wx.HORIZONTAL)

        ssh_sizer.Add(wx.StaticText(panel, label="IP 주소:"), 0,
                     wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)

        # 마지막 연결 정보 로드
        last_conn = self.settings.get_config().get('last_connection', {})
        default_ip = last_conn.get('ip', '127.0.0.1')

        self.ip_ctrl = wx.TextCtrl(panel, size=(150, -1), value=default_ip)
        ssh_sizer.Add(self.ip_ctrl, 0, wx.RIGHT, 10)

        ssh_sizer.Add(wx.StaticText(panel, label="포트:"), 0,
                     wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.port_ctrl = wx.TextCtrl(panel, size=(80, -1), value="22")
        ssh_sizer.Add(self.port_ctrl, 0, wx.RIGHT, 10)

        self.connect_btn = wx.Button(panel, label="연결")
        self.connect_btn.Bind(wx.EVT_BUTTON, self.on_toggle_connection)
        ssh_sizer.Add(self.connect_btn, 0, wx.RIGHT, 10)

        self.connection_status = wx.StaticText(panel, label="○ 미연결")
        self.connection_status.SetForegroundColour(wx.Colour(128, 128, 128))
        ssh_sizer.Add(self.connection_status, 0, wx.ALIGN_CENTER_VERTICAL)

        parent_sizer.Add(ssh_sizer, 0, wx.ALL | wx.EXPAND, 5)

    def create_log_sections(self, panel, parent_sizer):
        """로그 수집 설정 섹션 생성"""
        log_box = wx.StaticBox(panel, label="로그 수집 설정")
        log_sizer = wx.StaticBoxSizer(log_box, wx.VERTICAL)

        # Linux 커널 로그
        self.kernel_controls = self.create_log_section(
            panel, log_sizer, "Linux 커널 로그",
            LogSourceType.LINUX_KERNEL,
            wx.Colour(173, 216, 230)
        )

        # Linux 서버 앱 로그
        self.server_controls = self.create_log_section(
            panel, log_sizer, "Linux 서버 앱 로그",
            LogSourceType.LINUX_SERVER,
            wx.Colour(144, 238, 144)
        )

        # Windows 클라이언트 로그
        self.client_controls = self.create_log_section(
            panel, log_sizer, "Windows 클라이언트 로그",
            LogSourceType.WINDOWS_CLIENT,
            wx.Colour(221, 160, 221)
        )

        # 전체 수집 버튼
        collect_all_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.collect_all_btn = wx.Button(panel, label="전체 수집", size=(-1, 40))
        self.collect_all_btn.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT,
                                              wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.collect_all_btn.Bind(wx.EVT_BUTTON, self.on_collect_all)
        self.collect_all_btn.Enable(False)  # 초기에는 비활성화
        collect_all_sizer.Add(self.collect_all_btn, 1, wx.ALL | wx.EXPAND, 5)

        log_sizer.Add(collect_all_sizer, 0, wx.EXPAND | wx.TOP, 5)

        parent_sizer.Add(log_sizer, 0, wx.ALL | wx.EXPAND, 5)

    def create_log_section(self, panel, parent_sizer, title, log_type, color):
        """로그 섹션 생성"""
        section_box = wx.StaticBox(panel, label=title)
        section_box.SetBackgroundColour(color)
        section_sizer = wx.StaticBoxSizer(section_box, wx.VERTICAL)

        # 내용 패널
        content_panel = wx.Panel(panel)
        content_sizer = wx.BoxSizer(wx.VERTICAL)

        # 1행: 수집 옵션
        option_sizer = wx.BoxSizer(wx.HORIZONTAL)
        option_sizer.Add(wx.StaticText(content_panel, label="수집 옵션:"),
                        0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        rb_all = wx.RadioButton(content_panel, label="전체", style=wx.RB_GROUP)
        rb_all.SetValue(True)
        option_sizer.Add(rb_all, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        rb_regex = wx.RadioButton(content_panel, label="정규식")
        option_sizer.Add(rb_regex, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        rb_date = wx.RadioButton(content_panel, label="날짜")
        option_sizer.Add(rb_date, 0, wx.ALIGN_CENTER_VERTICAL)

        content_sizer.Add(option_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # 구분선
        content_sizer.Add(wx.StaticLine(content_panel, style=wx.LI_HORIZONTAL),
                         0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # 2행: 필터 조건
        filter_sizer = wx.BoxSizer(wx.HORIZONTAL)
        filter_sizer.Add(wx.StaticText(content_panel, label="필터 조건:"),
                        0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        filter_ctrl = wx.TextCtrl(content_panel, size=(400, -1))
        filter_ctrl.SetHint("필터 조건")
        filter_sizer.Add(filter_ctrl, 1, wx.ALIGN_CENTER_VERTICAL)

        # 날짜 라디오 버튼 선택 시 힌트 업데이트
        def on_date_selected(event):
            if rb_date.GetValue():
                filter_ctrl.SetHint("YYYY-MM-DD 또는 YYYY-MM-DD HH:MM:SS 형식 (예: 2025-10-21 14:30:00)")
            else:
                filter_ctrl.SetHint("필터 조건")

        rb_date.Bind(wx.EVT_RADIOBUTTON, on_date_selected)
        rb_all.Bind(wx.EVT_RADIOBUTTON, on_date_selected)
        rb_regex.Bind(wx.EVT_RADIOBUTTON, on_date_selected)

        content_sizer.Add(filter_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # 구분선
        content_sizer.Add(wx.StaticLine(content_panel, style=wx.LI_HORIZONTAL),
                         0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # 3행: 실행 버튼
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        action_sizer.Add(wx.StaticText(content_panel, label="실행:"),
                        0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        list_btn = wx.Button(content_panel, label="목록")
        list_btn.Bind(wx.EVT_BUTTON,
                     lambda e: self.on_show_file_list(log_type))
        action_sizer.Add(list_btn, 0, wx.RIGHT, 5)

        collect_btn = wx.Button(content_panel, label="수집")
        collect_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_collect(log_type))
        action_sizer.Add(collect_btn, 0, wx.RIGHT, 5)

        delete_btn = wx.Button(content_panel, label="삭제")
        delete_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_delete(log_type))
        action_sizer.Add(delete_btn, 0)

        content_sizer.Add(action_sizer, 0, wx.ALL | wx.EXPAND, 5)

        content_panel.SetSizer(content_sizer)
        section_sizer.Add(content_panel, 1, wx.EXPAND)

        # 경로 표시
        config = self.settings.get_log_source_config(log_type)
        path_text = wx.StaticText(panel, label=config.path)
        path_text.SetFont(self.default_font)  # 기본 폰트 사용
        section_sizer.Add(path_text, 0, wx.ALL | wx.EXPAND, 5)

        parent_sizer.Add(section_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # 컨트롤 저장
        controls = {
            'rb_all': rb_all,
            'rb_regex': rb_regex,
            'rb_date': rb_date,
            'filter_ctrl': filter_ctrl,
            'list_btn': list_btn,
            'collect_btn': collect_btn,
            'delete_btn': delete_btn,
            'path_text': path_text
        }

        # SSH 연결 상태에 따라 버튼 활성화/비활성화
        if log_type != LogSourceType.WINDOWS_CLIENT:
            list_btn.Enable(False)
            collect_btn.Enable(False)
            delete_btn.Enable(False)

        return controls

    def create_progress_section(self, panel, parent_sizer):
        """진행 상황 섹션 생성"""
        progress_box = wx.StaticBox(panel, label="진행 상황")
        progress_sizer = wx.StaticBoxSizer(progress_box, wx.VERTICAL)

        self.progress_text = wx.StaticText(panel, label="대기 중...")
        progress_sizer.Add(self.progress_text, 0, wx.ALL, 5)

        self.progress_bar = wx.Gauge(panel, range=100)
        self.progress_bar.SetValue(0)
        progress_sizer.Add(self.progress_bar, 0, wx.ALL | wx.EXPAND, 5)

        self.stop_btn = wx.Button(panel, label="다운로드 중지")
        self.stop_btn.Bind(wx.EVT_BUTTON, self.on_stop_download)
        self.stop_btn.Enable(False)
        progress_sizer.Add(self.stop_btn, 0, wx.ALL, 5)

        parent_sizer.Add(progress_sizer, 0, wx.ALL | wx.EXPAND, 5)


    def on_toggle_connection(self, event):
        """SSH 연결/종료 토글"""
        if not self.ssh_connected:
            # 연결 시도
            self.connect_ssh()
        else:
            # 연결 종료
            self.disconnect_ssh()

    def connect_ssh(self):
        """SSH 연결 (백그라운드 스레드)"""
        if self.connecting:
            wx.MessageBox("이미 연결 시도 중입니다.", "알림", wx.OK | wx.ICON_WARNING)
            return

        ip = self.ip_ctrl.GetValue().strip()
        port = self.port_ctrl.GetValue().strip()

        # 입력 검증
        from utils.validators import validate_ip_address, validate_port

        is_valid, msg = validate_ip_address(ip)
        if not is_valid:
            wx.MessageBox(msg, "입력 오류", wx.OK | wx.ICON_ERROR)
            return

        is_valid, msg = validate_port(port)
        if not is_valid:
            wx.MessageBox(msg, "입력 오류", wx.OK | wx.ICON_ERROR)
            return

        # 연결 시작 - UI 업데이트
        self.connecting = True
        self.connect_btn.Enable(False)
        self.ip_ctrl.Enable(False)
        self.port_ctrl.Enable(False)
        self.connection_status.SetLabel("⏳ 연결 중...")
        self.connection_status.SetForegroundColour(wx.Colour(255, 165, 0))  # 오렌지색
        self.update_status_bar()

        # SSH 설정 생성
        ssh_config = self.settings.get_ssh_config(ip)
        ssh_config.port = int(port)

        def connection_worker():
            """백그라운드 연결 작업"""
            try:
                logger.info(f"SSH 연결 시도: {ip}:{port}")
                self.ssh_manager.connect(ssh_config)

                # 연결 성공 - UI 업데이트 (메인 스레드에서)
                wx.CallAfter(self.on_connection_success, ip, int(port))

            except SSHConnectionError as e:
                logger.error(f"SSH 연결 실패: {e}")
                wx.CallAfter(self.on_connection_failure, str(e))

            except Exception as e:
                logger.exception(f"예기치 않은 연결 오류: {e}")
                wx.CallAfter(self.on_connection_failure, f"예기치 않은 오류: {str(e)}")

        # 백그라운드 스레드 시작
        thread = threading.Thread(target=connection_worker, daemon=True)
        thread.start()

    def on_connection_success(self, ip, port):
        """SSH 연결 성공 핸들러 (메인 스레드)"""
        self.ssh_connected = True
        self.connecting = False

        self.connect_btn.SetLabel("연결 종료")
        self.connect_btn.Enable(True)
        self.connection_status.SetLabel("● 연결됨")
        self.connection_status.SetForegroundColour(wx.Colour(0, 128, 0))

        # 원격 로그 버튼 활성화
        self.enable_remote_controls(True)

        # 마지막 연결 정보 저장
        self.settings.update_last_connection(ip, port)
        self.settings.save()

        self.update_status_bar()

        self.log_message(f"SSH 연결 성공: {ip}:{port}", "SUCCESS")

        wx.MessageBox("SSH 연결에 성공했습니다.", "연결 성공",
                     wx.OK | wx.ICON_INFORMATION)

    def on_connection_failure(self, error_message):
        """SSH 연결 실패 핸들러 (메인 스레드)"""
        self.connecting = False

        self.connect_btn.SetLabel("연결")
        self.connect_btn.Enable(True)
        self.ip_ctrl.Enable(True)
        self.port_ctrl.Enable(True)
        self.connection_status.SetLabel("○ 미연결")
        self.connection_status.SetForegroundColour(wx.Colour(128, 128, 128))

        self.update_status_bar()

        self.log_message(f"SSH 연결 실패: {error_message}", "ERROR")

        wx.MessageBox(f"SSH 연결 실패:\n{error_message}", "연결 오류",
                     wx.OK | wx.ICON_ERROR)

    def disconnect_ssh(self):
        """SSH 연결 종료"""
        try:
            self.ssh_manager.disconnect()

            self.ssh_connected = False
            self.connect_btn.SetLabel("연결")
            self.connection_status.SetLabel("○ 미연결")
            self.connection_status.SetForegroundColour(wx.Colour(128, 128, 128))
            self.ip_ctrl.Enable(True)
            self.port_ctrl.Enable(True)

            # 원격 로그 버튼 비활성화
            self.enable_remote_controls(False)

            self.update_status_bar()

            logger.info("SSH 연결 종료")
            self.log_message("SSH 연결 종료", "INFO")

        except Exception as e:
            logger.error(f"SSH 연결 종료 중 오류: {e}")
            self.log_message(f"SSH 연결 종료 중 오류: {e}", "ERROR")

    def enable_remote_controls(self, enabled):
        """원격 로그 컨트롤 활성화/비활성화"""
        for controls in [self.kernel_controls, self.server_controls]:
            controls['list_btn'].Enable(enabled)
            controls['collect_btn'].Enable(enabled)
            controls['delete_btn'].Enable(enabled)

        # 전체 수집 버튼도 활성화/비활성화
        self.collect_all_btn.Enable(enabled)

    def on_show_file_list(self, log_type):
        """파일 목록 다이얼로그 표시"""
        # 연결 확인
        config = self.settings.get_log_source_config(log_type)
        if config.is_remote() and not self.ssh_connected:
            wx.MessageBox("먼저 SSH에 연결해주세요.", "알림",
                         wx.OK | wx.ICON_WARNING)
            return

        # 파일 목록 조회 (백그라운드)
        self.show_file_list_async(log_type)

    def show_file_list_async(self, log_type):
        """파일 목록 조회 및 표시 (백그라운드)"""
        # 진행 상태 표시
        self.progress_text.SetLabel("파일 목록 조회 중...")
        self.progress_bar.Pulse()

        def list_worker():
            try:
                # 파일 목록 조회
                files = self.file_collector.get_file_list(
                    self.settings.get_log_source_config(log_type)
                )

                # 다이얼로그 표시 (메인 스레드)
                wx.CallAfter(self.show_file_list_dialog, log_type, files)

            except Exception as e:
                logger.error(f"파일 목록 조회 실패: {e}")
                wx.CallAfter(wx.MessageBox,
                            f"파일 목록 조회 실패:\n{str(e)}",
                            "오류", wx.OK | wx.ICON_ERROR)

            finally:
                wx.CallAfter(self.progress_text.SetLabel, "대기 중...")
                wx.CallAfter(self.progress_bar.SetValue, 0)

        # 백그라운드 스레드 시작
        thread = threading.Thread(target=list_worker, daemon=True)
        thread.start()

    def show_file_list_dialog(self, log_type, files):
        """파일 목록 다이얼로그 표시 (메인 스레드)"""
        from ui.file_list_dialog import FileListDialog

        if not files:
            wx.MessageBox("파일이 없습니다.", "알림",
                         wx.OK | wx.ICON_INFORMATION)
            return

        # 파일 목록 다이얼로그
        dlg = FileListDialog(self, files, log_type)
        result = dlg.ShowModal()

        if result == wx.ID_OK:
            # 선택한 파일 수집
            selected_files = dlg.selected_files
            if selected_files:
                self.start_selected_collection(selected_files)

        dlg.Destroy()

    def on_collect(self, log_type):
        """로그 수집"""
        # 연결 확인
        config = self.settings.get_log_source_config(log_type)
        if config.is_remote() and not self.ssh_connected:
            wx.MessageBox("먼저 SSH에 연결해주세요.", "알림",
                         wx.OK | wx.ICON_WARNING)
            return

        # 백그라운드 스레드에서 수집
        self.start_collection(log_type)

    def on_collect_all(self, event):
        """전체 로그 수집"""
        # SSH 연결 확인
        if not self.ssh_connected:
            wx.MessageBox("먼저 SSH에 연결해주세요.", "알림",
                         wx.OK | wx.ICON_WARNING)
            return

        # 확인 메시지
        result = wx.MessageBox(
            "3가지 로그를 모두 수집하시겠습니까?\n\n"
            "- 제어기 커널 로그\n"
            "- 제어기 로그\n"
            "- 사용자 SW 로그",
            "전체 수집 확인",
            wx.YES_NO | wx.ICON_QUESTION
        )

        if result != wx.YES:
            return

        # 순차적으로 수집
        self.start_all_collection()

    def start_all_collection(self):
        """모든 로그 순차 수집"""
        if self.downloading:
            wx.MessageBox("이미 다운로드가 진행 중입니다.", "알림",
                         wx.OK | wx.ICON_WARNING)
            return

        def collection_worker():
            try:
                self.downloading = True
                wx.CallAfter(self.stop_btn.Enable, True)

                save_path = self.settings.get_save_path()
                all_results = []

                # 3가지 로그 타입 순차 수집
                log_types = [
                    LogSourceType.LINUX_KERNEL,
                    LogSourceType.LINUX_SERVER,
                    LogSourceType.WINDOWS_CLIENT
                ]

                for log_type in log_types:
                    # 취소 확인
                    if self.cancel_token.is_cancelled():
                        break

                    config = self.settings.get_log_source_config(log_type)

                    # 진행 상황 표시
                    wx.CallAfter(
                        self.progress_text.SetLabel,
                        f"{config.get_display_name()} 수집 중..."
                    )

                    # 파일 수집
                    result = self.file_collector.collect_logs(
                        config,
                        save_path,
                        progress_callback=lambda p: wx.CallAfter(self.update_progress, p),
                        cancel_token=self.cancel_token
                    )

                    all_results.append((config.get_display_name(), result))

                # 전체 결과 표시
                wx.CallAfter(self.show_all_collection_result, all_results)

            except Exception as e:
                logger.error(f"전체 로그 수집 중 오류: {e}")
                wx.CallAfter(wx.MessageBox, f"전체 로그 수집 실패:\n{str(e)}",
                           "오류", wx.OK | wx.ICON_ERROR)
            finally:
                self.downloading = False
                wx.CallAfter(self.stop_btn.Enable, False)
                self.cancel_token.reset()

        thread = threading.Thread(target=collection_worker, daemon=True)
        thread.start()

    def show_all_collection_result(self, all_results):
        """전체 수집 결과 표시"""
        message_parts = ["전체 로그 수집 완료!\n"]

        total_collected = 0
        total_failed = 0

        for log_name, result in all_results:
            if result.success:
                message_parts.append(
                    f"\n✓ {log_name}: {result.collected_files}개 파일 수집"
                )
                total_collected += result.collected_files
            else:
                message_parts.append(
                    f"\n✗ {log_name}: 수집 실패 ({result.error_message})"
                )
                total_failed += 1

        message_parts.append(f"\n\n총 {total_collected}개 파일 수집 완료")
        if total_failed > 0:
            message_parts.append(f"\n실패: {total_failed}개 로그 타입")

        wx.MessageBox("".join(message_parts), "전체 수집 완료",
                     wx.OK | wx.ICON_INFORMATION)

        # 진행률 초기화
        self.progress_text.SetLabel("대기 중...")
        self.progress_bar.SetValue(0)

    def start_collection(self, log_type):
        """로그 수집 시작 (백그라운드)"""
        if self.downloading:
            wx.MessageBox("이미 다운로드가 진행 중입니다.", "알림",
                         wx.OK | wx.ICON_WARNING)
            return

        def collection_worker():
            try:
                self.downloading = True
                wx.CallAfter(self.stop_btn.Enable, True)

                # 설정 로드
                config = self.settings.get_log_source_config(log_type)
                save_path = self.settings.get_save_path()

                wx.CallAfter(self.log_message, f"{config.get_display_name()} 수집 시작", "INFO")

                # 파일 수집
                result = self.file_collector.collect_logs(
                    config,
                    save_path,
                    progress_callback=lambda p: wx.CallAfter(self.update_progress, p),
                    cancel_token=self.cancel_token
                )

                # 결과 로그
                if result.success:
                    wx.CallAfter(self.log_message,
                               f"{config.get_display_name()} 수집 완료: {result.collected_files}개 파일",
                               "SUCCESS")
                else:
                    wx.CallAfter(self.log_message,
                               f"{config.get_display_name()} 수집 실패: {result.error_message}",
                               "ERROR")

                # 결과 표시
                wx.CallAfter(self.show_collection_result, result)

            except Exception as e:
                logger.error(f"로그 수집 중 오류: {e}")
                wx.CallAfter(wx.MessageBox, f"로그 수집 실패:\n{str(e)}",
                           "오류", wx.OK | wx.ICON_ERROR)
            finally:
                self.downloading = False
                wx.CallAfter(self.stop_btn.Enable, False)
                self.cancel_token.reset()

        thread = threading.Thread(target=collection_worker, daemon=True)
        thread.start()

    def start_selected_collection(self, files):
        """선택한 파일만 수집 (백그라운드)"""
        if self.downloading:
            wx.MessageBox("이미 다운로드가 진행 중입니다.", "알림",
                         wx.OK | wx.ICON_WARNING)
            return

        def collection_worker():
            try:
                self.downloading = True
                wx.CallAfter(self.stop_btn.Enable, True)

                # 저장 경로
                save_path = self.settings.get_save_path()

                # 선택한 파일 수집
                result = self.file_collector.collect_selected_files(
                    files,
                    save_path,
                    progress_callback=lambda p: wx.CallAfter(self.update_progress, p),
                    cancel_token=self.cancel_token
                )

                # 결과 표시
                wx.CallAfter(self.show_collection_result, result)

            except Exception as e:
                logger.error(f"파일 수집 중 오류: {e}")
                wx.CallAfter(wx.MessageBox, f"파일 수집 실패:\n{str(e)}",
                           "오류", wx.OK | wx.ICON_ERROR)
            finally:
                self.downloading = False
                wx.CallAfter(self.stop_btn.Enable, False)
                self.cancel_token.reset()

        thread = threading.Thread(target=collection_worker, daemon=True)
        thread.start()

    def update_progress(self, progress: ProgressInfo):
        """진행률 업데이트"""
        self.progress_text.SetLabel(progress.get_progress_text())
        self.progress_bar.SetValue(progress.total_progress)

    def show_collection_result(self, result):
        """수집 결과 표시"""
        if result.success:
            message = f"로그 수집 완료!\n\n{result.get_summary()}"
            wx.MessageBox(message, "수집 완료", wx.OK | wx.ICON_INFORMATION)
        else:
            message = f"로그 수집 실패\n\n{result.error_message}"
            wx.MessageBox(message, "수집 실패", wx.OK | wx.ICON_ERROR)

        # 진행률 초기화
        self.progress_text.SetLabel("대기 중...")
        self.progress_bar.SetValue(0)

    def on_delete(self, log_type):
        """로그 삭제"""
        # 연결 확인
        config = self.settings.get_log_source_config(log_type)
        if config.is_remote() and not self.ssh_connected:
            wx.MessageBox("먼저 SSH에 연결해주세요.", "알림",
                         wx.OK | wx.ICON_WARNING)
            return

        # 파일 목록 조회 먼저 수행
        self.show_delete_file_list(log_type)

    def show_delete_file_list(self, log_type):
        """삭제할 파일 목록 조회 및 표시"""
        # 진행 상태 표시
        self.progress_text.SetLabel("파일 목록 조회 중...")
        self.progress_bar.Pulse()

        def list_worker():
            try:
                # 파일 목록 조회
                files = self.file_collector.get_file_list(
                    self.settings.get_log_source_config(log_type)
                )

                # 다이얼로그 표시 (메인 스레드)
                wx.CallAfter(self.confirm_and_delete_files, log_type, files)

            except Exception as e:
                logger.error(f"파일 목록 조회 실패: {e}")
                wx.CallAfter(wx.MessageBox,
                            f"파일 목록 조회 실패:\n{str(e)}",
                            "오류", wx.OK | wx.ICON_ERROR)

            finally:
                wx.CallAfter(self.progress_text.SetLabel, "대기 중...")
                wx.CallAfter(self.progress_bar.SetValue, 0)

        # 백그라운드 스레드 시작
        thread = threading.Thread(target=list_worker, daemon=True)
        thread.start()

    def confirm_and_delete_files(self, log_type, files):
        """삭제 확인 및 실행"""
        if not files:
            wx.MessageBox("삭제할 파일이 없습니다.", "알림",
                         wx.OK | wx.ICON_INFORMATION)
            return

        config = self.settings.get_log_source_config(log_type)
        count = len(files)
        total_size = sum(f.size for f in files)

        # 크기 포맷팅
        size = total_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                size_str = f"{size:.2f} {unit}"
                break
            size /= 1024.0
        else:
            size_str = f"{size:.2f} TB"

        # 확인 대화상자
        msg = (f"{config.get_display_name()}\n\n"
               f"총 {count}개 파일 ({size_str})을 삭제하시겠습니까?\n\n"
               f"경로: {config.path}\n\n"
               f"⚠️ 이 작업은 되돌릴 수 없습니다!")

        result = wx.MessageBox(msg, "삭제 확인",
                              wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)

        if result == wx.YES:
            # 삭제 실행
            self.start_delete_files(files)

    def start_delete_files(self, files):
        """파일 삭제 시작 (백그라운드)"""
        def delete_worker():
            try:
                self.progress_text.SetLabel("파일 삭제 중...")
                self.progress_bar.SetValue(0)

                # 파일 삭제
                success_count, fail_count = self.file_collector.delete_files(files)

                # 결과 표시
                wx.CallAfter(self.show_delete_result, success_count, fail_count, len(files))

            except Exception as e:
                logger.error(f"파일 삭제 중 오류: {e}")
                wx.CallAfter(wx.MessageBox, f"파일 삭제 실패:\n{str(e)}",
                           "오류", wx.OK | wx.ICON_ERROR)
            finally:
                wx.CallAfter(self.progress_text.SetLabel, "대기 중...")
                wx.CallAfter(self.progress_bar.SetValue, 0)

        thread = threading.Thread(target=delete_worker, daemon=True)
        thread.start()

    def show_delete_result(self, success_count, fail_count, total_count):
        """삭제 결과 표시"""
        if fail_count == 0:
            message = f"총 {total_count}개 파일 삭제 완료!"
            wx.MessageBox(message, "삭제 완료", wx.OK | wx.ICON_INFORMATION)
        else:
            message = (f"삭제 결과:\n\n"
                      f"성공: {success_count}개\n"
                      f"실패: {fail_count}개\n"
                      f"전체: {total_count}개")
            wx.MessageBox(message, "삭제 완료", wx.OK | wx.ICON_WARNING)

    def on_stop_download(self, event):
        """다운로드 중지"""
        self.cancel_token.cancel()
        self.progress_text.SetLabel("취소 중...")


    def on_settings(self, event):
        """설정 다이얼로그 표시"""
        try:
            logger.info("설정 다이얼로그 열기 시작")
            from ui.settings_dialog import SettingsDialog

            dlg = SettingsDialog(self)
            logger.info("설정 다이얼로그 생성 완료")

            result = dlg.ShowModal()
            logger.info(f"설정 다이얼로그 결과: {result}")

            if result == wx.ID_OK:
                # 설정이 변경되었으므로 UI 업데이트
                self.refresh_ui_from_settings()

            dlg.Destroy()

        except Exception as e:
            logger.exception(f"설정 다이얼로그 오류: {e}")
            wx.MessageBox(f"설정 다이얼로그 오류:\n{str(e)}", "오류",
                         wx.OK | wx.ICON_ERROR)

    def on_quit(self, event):
        """프로그램 종료"""
        # SSH 연결 종료
        if self.ssh_connected:
            self.disconnect_ssh()

        self.Close()

    def update_status_bar(self):
        """상태 표시줄 업데이트"""
        if self.ssh_connected:
            ip = self.ip_ctrl.GetValue()
            port = self.port_ctrl.GetValue()
            status = f"SSH: 연결됨 ({ip}:{port}) | 준비"
        else:
            status = "SSH: 미연결 | 준비"

        self.SetStatusText(status)

    def refresh_ui_from_settings(self):
        """설정 변경 후 UI 업데이트"""
        # 각 로그 섹션의 경로 텍스트 업데이트
        for log_type in [LogSourceType.LINUX_KERNEL, LogSourceType.LINUX_SERVER, LogSourceType.WINDOWS_CLIENT]:
            config = self.settings.get_log_source_config(log_type)

            if log_type == LogSourceType.LINUX_KERNEL:
                controls = self.kernel_controls
            elif log_type == LogSourceType.LINUX_SERVER:
                controls = self.server_controls
            else:
                controls = self.client_controls

            # 경로 텍스트 업데이트
            controls['path_text'].SetLabel(config.path)

        logger.info("설정 변경 후 UI 업데이트 완료")

    def on_show_log_window(self, event):
        """로그 윈도우 표시"""
        if self.log_window is None or not self.log_window:
            from ui.log_window import LogWindow
            self.log_window = LogWindow(self)

            # 버퍼에 저장된 로그 메시지를 모두 출력
            for msg, lvl in self.log_buffer:
                self.log_window.append_log(msg, lvl)

        self.log_window.Show()
        self.log_window.Raise()

    def log_message(self, message, level="INFO"):
        """
        로그 메시지 출력 (항상 버퍼에 저장하고, 윈도우가 열려있으면 즉시 표시)

        Args:
            message: 로그 메시지
            level: 로그 레벨 (INFO, WARNING, ERROR, DEBUG, SUCCESS)
        """
        # 버퍼에 저장 (최대 1000개 메시지만 유지)
        self.log_buffer.append((message, level))
        if len(self.log_buffer) > 1000:
            self.log_buffer.pop(0)

        # 로그 윈도우가 열려있으면 메시지 추가
        if self.log_window and self.log_window.IsShown():
            wx.CallAfter(self.log_window.append_log, message, level)
