"""
File List Dialog for Log Collector

파일 목록 다이얼로그 구현
"""

import wx
from typing import List
from core.models import FileInfo, LogSourceType
from utils.logger import get_logger

logger = get_logger("FileListDialog")


class FileListDialog(wx.Dialog):
    """파일 목록 다이얼로그"""

    def __init__(self, parent, files: List[FileInfo], log_type: LogSourceType):
        """
        초기화

        Args:
            parent: 부모 윈도우
            files: 파일 정보 리스트
            log_type: 로그 소스 타입
        """
        title = self.get_title(log_type)
        super().__init__(parent, title=title, size=(800, 600))

        self.files = files
        self.log_type = log_type
        self.selected_files = []

        # 기본 폰트
        self.default_font = wx.Font(9, wx.FONTFAMILY_DEFAULT,
                                     wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        self.init_ui()
        self.load_file_list()
        self.Centre()

    def get_title(self, log_type: LogSourceType) -> str:
        """타입별 타이틀 생성"""
        titles = {
            LogSourceType.LINUX_KERNEL: "제어기 커널 로그 파일 목록",
            LogSourceType.LINUX_SERVER: "제어기 로그 파일 목록",
            LogSourceType.WINDOWS_CLIENT: "사용자 SW 로그 파일 목록"
        }
        return titles.get(log_type, "파일 목록")

    def init_ui(self):
        """UI 초기화"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 정보 표시
        info_text = wx.StaticText(panel,
            label=f"총 {len(self.files)}개의 파일이 있습니다. "
                  "다운로드할 파일을 선택하세요.")
        info_text.SetFont(self.default_font)
        main_sizer.Add(info_text, 0, wx.ALL, 10)

        # 파일 리스트
        self.file_list = wx.ListCtrl(panel,
                                     style=wx.LC_REPORT | wx.LC_SINGLE_SEL)

        # 컬럼 추가
        self.file_list.InsertColumn(0, "선택", width=50)
        self.file_list.InsertColumn(1, "파일명", width=300)
        self.file_list.InsertColumn(2, "크기", width=100)
        self.file_list.InsertColumn(3, "수정 시간", width=150)
        self.file_list.InsertColumn(4, "경로", width=180)

        main_sizer.Add(self.file_list, 1, wx.ALL | wx.EXPAND, 10)

        # 선택 버튼
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        select_all_btn = wx.Button(panel, label="전체 선택")
        select_all_btn.Bind(wx.EVT_BUTTON, self.on_select_all)
        btn_sizer.Add(select_all_btn, 0, wx.RIGHT, 5)

        deselect_all_btn = wx.Button(panel, label="선택 해제")
        deselect_all_btn.Bind(wx.EVT_BUTTON, self.on_deselect_all)
        btn_sizer.Add(deselect_all_btn, 0, wx.RIGHT, 5)

        toggle_btn = wx.Button(panel, label="선택 토글")
        toggle_btn.Bind(wx.EVT_BUTTON, self.on_toggle_selection)
        btn_sizer.Add(toggle_btn, 0)

        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        # 다이얼로그 버튼
        dialog_btn_sizer = wx.StdDialogButtonSizer()

        ok_btn = wx.Button(panel, wx.ID_OK, "수집")
        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        dialog_btn_sizer.AddButton(ok_btn)

        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "취소")
        cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        dialog_btn_sizer.AddButton(cancel_btn)

        dialog_btn_sizer.Realize()
        main_sizer.Add(dialog_btn_sizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

        panel.SetSizer(main_sizer)

        # 리스트 아이템 클릭 이벤트
        self.file_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)

    def load_file_list(self):
        """파일 목록 로드"""
        self.file_list.DeleteAllItems()

        for idx, file_info in enumerate(self.files):
            # 아이템 추가
            index = self.file_list.InsertItem(idx, "")
            self.file_list.SetItem(index, 1, file_info.name)
            self.file_list.SetItem(index, 2, file_info.get_size_str())
            self.file_list.SetItem(index, 3, file_info.get_modified_time_str())
            self.file_list.SetItem(index, 4, file_info.path)

            # 데이터 저장
            self.file_list.SetItemData(index, idx)

    def is_item_selected(self, index: int) -> bool:
        """아이템 선택 여부 확인"""
        return self.file_list.GetItemText(index, 0) == "✓"

    def set_item_selected(self, index: int, selected: bool):
        """아이템 선택 상태 설정"""
        if selected:
            self.file_list.SetItem(index, 0, "✓")
            self.file_list.SetItemBackgroundColour(index, wx.Colour(230, 255, 230))
        else:
            self.file_list.SetItem(index, 0, "")
            self.file_list.SetItemBackgroundColour(index, wx.WHITE)

    def on_item_activated(self, event):
        """아이템 더블클릭 또는 엔터키"""
        index = event.GetIndex()
        current = self.is_item_selected(index)
        self.set_item_selected(index, not current)

    def on_select_all(self, event):
        """전체 선택"""
        count = self.file_list.GetItemCount()
        for i in range(count):
            self.set_item_selected(i, True)

    def on_deselect_all(self, event):
        """선택 해제"""
        count = self.file_list.GetItemCount()
        for i in range(count):
            self.set_item_selected(i, False)

    def on_toggle_selection(self, event):
        """선택 토글"""
        count = self.file_list.GetItemCount()
        for i in range(count):
            current = self.is_item_selected(i)
            self.set_item_selected(i, not current)

    def get_selected_files(self) -> List[FileInfo]:
        """선택된 파일 목록 반환"""
        selected = []
        count = self.file_list.GetItemCount()

        for i in range(count):
            if self.is_item_selected(i):
                file_idx = self.file_list.GetItemData(i)
                selected.append(self.files[file_idx])

        return selected

    def on_ok(self, event):
        """확인 버튼"""
        self.selected_files = self.get_selected_files()

        if not self.selected_files:
            wx.MessageBox("파일을 선택하세요.", "선택 오류",
                         wx.OK | wx.ICON_WARNING)
            return

        # 확인 메시지
        count = len(self.selected_files)
        total_size = sum(f.size for f in self.selected_files)

        # 크기를 사람이 읽기 쉬운 형태로 변환
        size = total_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                size_str = f"{size:.2f} {unit}"
                break
            size /= 1024.0
        else:
            size_str = f"{size:.2f} TB"

        msg = f"선택한 {count}개 파일 (총 {size_str})을 수집하시겠습니까?"
        result = wx.MessageBox(msg, "수집 확인",
                              wx.YES_NO | wx.ICON_QUESTION)

        if result == wx.YES:
            self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        """취소 버튼"""
        self.selected_files = []
        self.EndModal(wx.ID_CANCEL)
