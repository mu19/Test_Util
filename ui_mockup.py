import wx
import wx.lib.mixins.listctrl as listmix

class FileListDialog(wx.Dialog):
    """파일 목록 다이얼로그"""
    def __init__(self, parent, log_type, log_path):
        super().__init__(parent, title=f"{log_type} 파일 목록", 
                        size=(800, 500))
        
        self.log_type = log_type
        self.log_path = log_path
        self.selected_files = []
        
        self.init_ui()
        self.Centre()
        
    def init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 경로 정보
        path_box = wx.StaticBox(panel, label="경로")
        path_sizer = wx.StaticBoxSizer(path_box, wx.VERTICAL)
        path_text = wx.StaticText(panel, label=self.log_path)
        path_text.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, 
                                   wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        path_sizer.Add(path_text, 0, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(path_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # 파일 목록
        self.file_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.file_list.InsertColumn(0, "선택", width=50)
        self.file_list.InsertColumn(1, "파일명", width=400)
        self.file_list.InsertColumn(2, "크기", width=120)
        self.file_list.InsertColumn(3, "수정 날짜", width=180)
        
        # 샘플 데이터 추가
        sample_files = [
            ("syslog", "2.5 MB", "2025-10-20 14:30:22"),
            ("kern.log", "1.8 MB", "2025-10-20 14:25:10"),
            ("auth.log", "524 KB", "2025-10-20 13:45:55"),
            ("boot.log", "128 KB", "2025-10-19 09:15:03"),
            ("dmesg", "89 KB", "2025-10-19 09:14:58"),
        ]
        
        for i, (name, size, date) in enumerate(sample_files):
            index = self.file_list.InsertItem(i, "")
            self.file_list.SetItem(index, 1, name)
            self.file_list.SetItem(index, 2, size)
            self.file_list.SetItem(index, 3, date)
        
        self.file_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.file_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_item_deselected)
        
        main_sizer.Add(self.file_list, 1, wx.ALL | wx.EXPAND, 5)
        
        # 선택 정보
        info_box = wx.StaticBox(panel, label="선택 정보")
        info_sizer = wx.StaticBoxSizer(info_box, wx.VERTICAL)
        self.info_text = wx.StaticText(panel, label="선택된 파일: 0개 | 총 크기: 0 MB")
        info_sizer.Add(self.info_text, 0, wx.ALL | wx.EXPAND, 5)
        main_sizer.Add(info_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # 버튼
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        download_selected_btn = wx.Button(panel, label="선택한 파일 다운로드")
        download_selected_btn.Bind(wx.EVT_BUTTON, self.on_download_selected)
        button_sizer.Add(download_selected_btn, 1, wx.ALL, 5)
        
        download_all_btn = wx.Button(panel, label="전체 다운로드")
        download_all_btn.Bind(wx.EVT_BUTTON, self.on_download_all)
        button_sizer.Add(download_all_btn, 1, wx.ALL, 5)
        
        close_btn = wx.Button(panel, wx.ID_CLOSE, "닫기")
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        button_sizer.Add(close_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        panel.SetSizer(main_sizer)
    
    def on_item_selected(self, event):
        index = event.GetIndex()
        if index not in self.selected_files:
            self.selected_files.append(index)
            self.file_list.SetItem(index, 0, "✓")
        self.update_info()
    
    def on_item_deselected(self, event):
        index = event.GetIndex()
        if index in self.selected_files:
            self.selected_files.remove(index)
            self.file_list.SetItem(index, 0, "")
        self.update_info()
    
    def update_info(self):
        count = len(self.selected_files)
        self.info_text.SetLabel(f"선택된 파일: {count}개 | 총 크기: 0 MB")
    
    def on_download_selected(self, event):
        if not self.selected_files:
            wx.MessageBox("다운로드할 파일을 선택해주세요.", "알림", 
                         wx.OK | wx.ICON_INFORMATION)
            return
        wx.MessageBox(f"{len(self.selected_files)}개 파일 다운로드 시작", "알림", 
                     wx.OK | wx.ICON_INFORMATION)
    
    def on_download_all(self, event):
        wx.MessageBox("전체 파일 다운로드 시작", "알림", 
                     wx.OK | wx.ICON_INFORMATION)


class SettingsDialog(wx.Dialog):
    """설정 다이얼로그"""
    def __init__(self, parent):
        super().__init__(parent, title="설정", size=(800, 600))
        
        self.init_ui()
        self.Centre()
    
    def init_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 스크롤 가능한 패널
        scroll = wx.ScrolledWindow(panel)
        scroll.SetScrollRate(5, 5)
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # SSH 연결 설정
        ssh_box = wx.StaticBox(scroll, label="SSH 연결 설정")
        ssh_sizer = wx.StaticBoxSizer(ssh_box, wx.VERTICAL)
        
        grid_sizer = wx.FlexGridSizer(4, 2, 5, 5)
        grid_sizer.AddGrowableCol(1)
        
        grid_sizer.Add(wx.StaticText(scroll, label="사용자명:"), 0, 
                      wx.ALIGN_CENTER_VERTICAL)
        self.username_ctrl = wx.TextCtrl(scroll, value="root")
        grid_sizer.Add(self.username_ctrl, 1, wx.EXPAND)
        
        grid_sizer.Add(wx.StaticText(scroll, label="비밀번호:"), 0, 
                      wx.ALIGN_CENTER_VERTICAL)
        self.password_ctrl = wx.TextCtrl(scroll, style=wx.TE_PASSWORD)
        grid_sizer.Add(self.password_ctrl, 1, wx.EXPAND)
        
        grid_sizer.Add(wx.StaticText(scroll, label="타임아웃(초):"), 0, 
                      wx.ALIGN_CENTER_VERTICAL)
        self.timeout_ctrl = wx.TextCtrl(scroll, value="300")
        grid_sizer.Add(self.timeout_ctrl, 1, wx.EXPAND)
        
        ssh_sizer.Add(grid_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        self.keep_alive_check = wx.CheckBox(scroll, 
                                            label="SSH 연결 유지 (자동 재연결)")
        self.keep_alive_check.SetValue(True)
        ssh_sizer.Add(self.keep_alive_check, 0, wx.ALL, 5)
        
        scroll_sizer.Add(ssh_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # Linux 커널 로그 설정
        kernel_box = wx.StaticBox(scroll, label="Linux 커널 로그 설정")
        kernel_sizer = wx.StaticBoxSizer(kernel_box, wx.VERTICAL)
        
        path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer.Add(wx.StaticText(scroll, label="로그 경로:"), 0, 
                      wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.kernel_path_ctrl = wx.TextCtrl(scroll, value="/var/log/")
        path_sizer.Add(self.kernel_path_ctrl, 1, wx.EXPAND)
        default_btn = wx.Button(scroll, label="기본값")
        path_sizer.Add(default_btn, 0, wx.LEFT, 5)
        kernel_sizer.Add(path_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        self.kernel_delete_check = wx.CheckBox(scroll, label="원격 파일 삭제")
        kernel_sizer.Add(self.kernel_delete_check, 0, wx.ALL, 5)
        
        scroll_sizer.Add(kernel_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # Linux 서버 앱 로그 설정
        server_box = wx.StaticBox(scroll, label="Linux 서버 앱 로그 설정")
        server_sizer = wx.StaticBoxSizer(server_box, wx.VERTICAL)
        
        path_sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer2.Add(wx.StaticText(scroll, label="로그 경로:"), 0, 
                       wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.server_path_ctrl = wx.TextCtrl(scroll, value="/opt/myapp/logs/")
        path_sizer2.Add(self.server_path_ctrl, 1, wx.EXPAND)
        browse_btn = wx.Button(scroll, label="찾아보기")
        path_sizer2.Add(browse_btn, 0, wx.LEFT, 5)
        server_sizer.Add(path_sizer2, 0, wx.ALL | wx.EXPAND, 5)
        
        self.server_delete_check = wx.CheckBox(scroll, label="원격 파일 삭제")
        server_sizer.Add(self.server_delete_check, 0, wx.ALL, 5)
        
        scroll_sizer.Add(server_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # Windows 클라이언트 로그 설정
        client_box = wx.StaticBox(scroll, label="Windows 클라이언트 로그 설정")
        client_sizer = wx.StaticBoxSizer(client_box, wx.VERTICAL)
        
        path_sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        path_sizer3.Add(wx.StaticText(scroll, label="로그 경로:"), 0, 
                       wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.client_path_ctrl = wx.TextCtrl(scroll, 
                                            value="C:\\Program Files\\MyApp\\Logs\\")
        path_sizer3.Add(self.client_path_ctrl, 1, wx.EXPAND)
        browse_btn2 = wx.Button(scroll, label="찾아보기")
        path_sizer3.Add(browse_btn2, 0, wx.LEFT, 5)
        client_sizer.Add(path_sizer3, 0, wx.ALL | wx.EXPAND, 5)
        
        self.client_delete_check = wx.CheckBox(scroll, label="로컬 원본 파일 삭제")
        client_sizer.Add(self.client_delete_check, 0, wx.ALL, 5)
        
        scroll_sizer.Add(client_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # 공통 설정
        common_box = wx.StaticBox(scroll, label="공통 설정")
        common_sizer = wx.StaticBoxSizer(common_box, wx.VERTICAL)
        
        save_path_sizer = wx.BoxSizer(wx.HORIZONTAL)
        save_path_sizer.Add(wx.StaticText(scroll, label="기본 저장 경로:"), 0, 
                           wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.save_path_ctrl = wx.TextCtrl(scroll, value="C:\\Logs\\collected\\")
        save_path_sizer.Add(self.save_path_ctrl, 1, wx.EXPAND)
        browse_btn3 = wx.Button(scroll, label="찾아보기")
        save_path_sizer.Add(browse_btn3, 0, wx.LEFT, 5)
        common_sizer.Add(save_path_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        scroll_sizer.Add(common_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        scroll.SetSizer(scroll_sizer)
        main_sizer.Add(scroll, 1, wx.EXPAND)
        
        # 버튼
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer()
        
        save_btn = wx.Button(panel, wx.ID_SAVE, "저장")
        save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        button_sizer.Add(save_btn, 0, wx.ALL, 5)
        
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "취소")
        cancel_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        button_sizer.Add(cancel_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        panel.SetSizer(main_sizer)
    
    def on_save(self, event):
        wx.MessageBox("설정이 저장되었습니다.", "알림", 
                     wx.OK | wx.ICON_INFORMATION)
        self.Close()


class MainFrame(wx.Frame):
    """메인 프레임"""
    def __init__(self):
        super().__init__(None, title="로그 수집 유틸리티", size=(1100, 800))
        
        self.ssh_connected = False
        self.init_ui()
        self.Centre()
        self.CreateStatusBar()
        self.update_status_bar()
    
    def init_ui(self):
        # 메뉴바
        menubar = wx.MenuBar()
        
        file_menu = wx.Menu()
        exit_item = file_menu.Append(wx.ID_EXIT, "종료\tCtrl+Q")
        self.Bind(wx.EVT_MENU, self.on_quit, exit_item)
        menubar.Append(file_menu, "파일(&F)")
        
        settings_menu = wx.Menu()
        settings_item = settings_menu.Append(wx.ID_ANY, "설정\tCtrl+S")
        self.Bind(wx.EVT_MENU, self.on_settings, settings_item)
        menubar.Append(settings_menu, "설정(&S)")
        
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "정보")
        self.Bind(wx.EVT_MENU, self.on_about, about_item)
        menubar.Append(help_menu, "도움말(&H)")
        
        self.SetMenuBar(menubar)
        
        # 메인 패널
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # SSH 연결 그룹
        ssh_box = wx.StaticBox(panel, label="SSH 연결")
        ssh_sizer = wx.StaticBoxSizer(ssh_box, wx.HORIZONTAL)
        
        ssh_sizer.Add(wx.StaticText(panel, label="IP 주소:"), 0, 
                     wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.ip_ctrl = wx.TextCtrl(panel, size=(150, -1), value="192.168.1.100")
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
        
        main_sizer.Add(ssh_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # 로그 수집 설정 그룹
        log_box = wx.StaticBox(panel, label="로그 수집 설정")
        log_sizer = wx.StaticBoxSizer(log_box, wx.VERTICAL)
        
        # Linux 커널 로그
        self.create_log_section(panel, log_sizer, "Linux 커널 로그", 
                               "/var/log/", "kernel", wx.Colour(173, 216, 230))
        
        # Linux 서버 앱 로그
        self.create_log_section(panel, log_sizer, "Linux 서버 앱 로그", 
                               "설정 필요", "server", wx.Colour(144, 238, 144))
        
        # Windows 클라이언트 로그
        self.create_log_section(panel, log_sizer, "Windows 클라이언트 로그", 
                               "설정 필요", "client", wx.Colour(221, 160, 221))
        
        main_sizer.Add(log_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # 진행 상황 그룹
        progress_box = wx.StaticBox(panel, label="진행 상황")
        progress_sizer = wx.StaticBoxSizer(progress_box, wx.VERTICAL)
        
        self.progress_text = wx.StaticText(panel, 
                                          label="다운로드 중: kernel.log (2/5) - 40%")
        progress_sizer.Add(self.progress_text, 0, wx.ALL, 5)
        
        self.progress_bar = wx.Gauge(panel, range=100)
        self.progress_bar.SetValue(40)
        progress_sizer.Add(self.progress_bar, 0, wx.ALL | wx.EXPAND, 5)
        
        self.stop_btn = wx.Button(panel, label="다운로드 중지")
        self.stop_btn.Bind(wx.EVT_BUTTON, self.on_stop_download)
        progress_sizer.Add(self.stop_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(progress_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # 저장 경로 그룹
        save_box = wx.StaticBox(panel, label="저장 경로")
        save_sizer = wx.StaticBoxSizer(save_box, wx.HORIZONTAL)
        
        self.save_path_ctrl = wx.TextCtrl(panel, value="C:\\Logs\\collected")
        save_sizer.Add(self.save_path_ctrl, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        
        browse_btn = wx.Button(panel, label="찾아보기...")
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse_save_path)
        save_sizer.Add(browse_btn, 0)
        
        main_sizer.Add(save_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        panel.SetSizer(main_sizer)
    
    def create_log_section(self, panel, parent_sizer, title, path, log_type, color):
        """로그 섹션 생성"""
        section_box = wx.StaticBox(panel, label=title)
        section_box.SetBackgroundColour(color)
        section_sizer = wx.StaticBoxSizer(section_box, wx.VERTICAL)
        
        # 내용을 담을 패널
        content_panel = wx.Panel(panel)
        content_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 수집 옵션 (1열)
        option_sizer = wx.BoxSizer(wx.VERTICAL)
        option_sizer.Add(wx.StaticText(content_panel, label="수집 옵션"), 0, wx.BOTTOM, 5)
        
        rb_all = wx.RadioButton(content_panel, label="전체", style=wx.RB_GROUP)
        rb_all.SetValue(True)
        option_sizer.Add(rb_all, 0, wx.BOTTOM, 2)
        
        rb_regex = wx.RadioButton(content_panel, label="정규식")
        option_sizer.Add(rb_regex, 0, wx.BOTTOM, 2)
        
        rb_date = wx.RadioButton(content_panel, label="날짜")
        option_sizer.Add(rb_date, 0)
        
        content_sizer.Add(option_sizer, 1, wx.ALL | wx.EXPAND, 5)
        
        # 구분선
        content_sizer.Add(wx.StaticLine(content_panel, style=wx.LI_VERTICAL), 
                         0, wx.EXPAND | wx.ALL, 5)
        
        # 필터/옵션 (2열)
        filter_sizer = wx.BoxSizer(wx.VERTICAL)
        filter_sizer.Add(wx.StaticText(content_panel, label="필터/옵션"), 0, wx.BOTTOM, 5)
        
        filter_ctrl = wx.TextCtrl(content_panel, size=(200, -1))
        filter_ctrl.SetHint("필터 조건")
        filter_sizer.Add(filter_ctrl, 0, wx.EXPAND | wx.BOTTOM, 5)
        
        compress_check = wx.CheckBox(content_panel, label="압축")
        filter_sizer.Add(compress_check, 0)
        
        content_sizer.Add(filter_sizer, 1, wx.ALL | wx.EXPAND, 5)
        
        # 구분선
        content_sizer.Add(wx.StaticLine(content_panel, style=wx.LI_VERTICAL), 
                         0, wx.EXPAND | wx.ALL, 5)
        
        # 실행 버튼 (3열)
        action_sizer = wx.BoxSizer(wx.VERTICAL)
        action_sizer.Add(wx.StaticText(content_panel, label="실행"), 0, wx.BOTTOM, 5)
        
        list_btn = wx.Button(content_panel, label="목록")
        list_btn.Bind(wx.EVT_BUTTON, 
                     lambda e: self.on_show_file_list(log_type, title, path))
        action_sizer.Add(list_btn, 0, wx.EXPAND | wx.BOTTOM, 2)
        
        collect_btn = wx.Button(content_panel, label="수집")
        collect_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_collect(log_type))
        action_sizer.Add(collect_btn, 0, wx.EXPAND | wx.BOTTOM, 2)
        
        delete_btn = wx.Button(content_panel, label="삭제")
        delete_btn.Bind(wx.EVT_BUTTON, lambda e: self.on_delete(log_type))
        action_sizer.Add(delete_btn, 0, wx.EXPAND)
        
        content_sizer.Add(action_sizer, 1, wx.ALL | wx.EXPAND, 5)
        
        content_panel.SetSizer(content_sizer)
        section_sizer.Add(content_panel, 1, wx.EXPAND)
        
        # 경로 표시
        path_text = wx.StaticText(panel, label=path)
        path_text.SetFont(wx.Font(8, wx.FONTFAMILY_TELETYPE, 
                                  wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        section_sizer.Add(path_text, 0, wx.ALL | wx.EXPAND, 5)
        
        parent_sizer.Add(section_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
        # SSH 연결 상태에 따라 버튼 비활성화 (Windows는 항상 활성화)
        if log_type != "client":
            list_btn.Enable(self.ssh_connected)
            collect_btn.Enable(self.ssh_connected)
            delete_btn.Enable(self.ssh_connected)
    
    def on_toggle_connection(self, event):
        """SSH 연결/종료 토글"""
        self.ssh_connected = not self.ssh_connected
        
        if self.ssh_connected:
            self.connect_btn.SetLabel("연결 종료")
            self.connection_status.SetLabel("● 연결됨")
            self.connection_status.SetForegroundColour(wx.Colour(0, 128, 0))
            self.ip_ctrl.Enable(False)
            self.port_ctrl.Enable(False)
        else:
            self.connect_btn.SetLabel("연결")
            self.connection_status.SetLabel("○ 미연결")
            self.connection_status.SetForegroundColour(wx.Colour(128, 128, 128))
            self.ip_ctrl.Enable(True)
            self.port_ctrl.Enable(True)
        
        self.update_status_bar()
        # TODO: 실제 SSH 연결 상태에 따라 버튼 활성화/비활성화
    
    def on_show_file_list(self, log_type, title, path):
        """파일 목록 다이얼로그 표시"""
        if log_type != "client" and not self.ssh_connected:
            wx.MessageBox("먼저 SSH에 연결해주세요.", "알림", 
                         wx.OK | wx.ICON_WARNING)
            return
        
        dlg = FileListDialog(self, title, path)
        dlg.ShowModal()
        dlg.Destroy()
    
    def on_collect(self, log_type):
        """로그 수집"""
        if log_type != "client" and not self.ssh_connected:
            wx.MessageBox("먼저 SSH에 연결해주세요.", "알림", 
                         wx.OK | wx.ICON_WARNING)
            return
        
        wx.MessageBox(f"{log_type} 로그 수집을 시작합니다.", "알림", 
                     wx.OK | wx.ICON_INFORMATION)
    
    def on_delete(self, log_type):
        """로그 삭제"""
        if log_type != "client" and not self.ssh_connected:
            wx.MessageBox("먼저 SSH에 연결해주세요.", "알림", 
                         wx.OK | wx.ICON_WARNING)
            return
        
        dlg = wx.MessageDialog(self, 
                              f"{log_type} 로그 파일을 삭제하시겠습니까?", 
                              "삭제 확인", 
                              wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        
        if dlg.ShowModal() == wx.ID_YES:
            wx.MessageBox("파일이 삭제되었습니다.", "알림", 
                         wx.OK | wx.ICON_INFORMATION)
        
        dlg.Destroy()
    
    def on_stop_download(self, event):
        """다운로드 중지"""
        wx.MessageBox("다운로드를 중지했습니다.", "알림", 
                     wx.OK | wx.ICON_INFORMATION)
    
    def on_browse_save_path(self, event):
        """저장 경로 찾아보기"""
        dlg = wx.DirDialog(self, "저장 경로 선택", 
                          defaultPath=self.save_path_ctrl.GetValue(),
                          style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        
        if dlg.ShowModal() == wx.ID_OK:
            self.save_path_ctrl.SetValue(dlg.GetPath())
        
        dlg.Destroy()
    
    def on_settings(self, event):
        """설정 다이얼로그 표시"""
        dlg = SettingsDialog(self)
        dlg.ShowModal()
        dlg.Destroy()
    
    def on_about(self, event):
        """정보 다이얼로그"""
        info = wx.adv.AboutDialogInfo()
        info.SetName("로그 수집 유틸리티")
        info.SetVersion("1.0.0")
        info.SetDescription("리눅스 및 윈도우 로그 파일 수집 도구")
        info.SetWebSite("https://example.com")
        wx.adv.AboutBox(info)
    
    def on_quit(self, event):
        """프로그램 종료"""
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


class LogCollectorApp(wx.App):
    """애플리케이션 클래스"""
    def OnInit(self):
        self.frame = MainFrame()
        self.frame.Show()
        return True


if __name__ == '__main__':
    app = LogCollectorApp()
    app.MainLoop()