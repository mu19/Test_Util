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

    def __init__(self, parent, files: List[FileInfo], log_type: LogSourceType, file_collector=None, log_source_config=None):
        """
        초기화

        Args:
            parent: 부모 윈도우
            files: 파일 정보 리스트
            log_type: 로그 소스 타입
            file_collector: 파일 수집기 (삭제 기능에 필요)
            log_source_config: 로그 소스 설정 (파일 목록 재조회에 필요)
        """
        title = self.get_title(log_type)
        super().__init__(parent, title=title, size=(800, 600))

        self.files = files
        self.log_type = log_type
        self.selected_files = []
        self.file_collector = file_collector
        self.log_source_config = log_source_config

        # 정렬 상태 관리
        self.sort_column = None  # 현재 정렬 중인 컬럼 (None, 1, 2, 3, 4)
        self.sort_ascending = True  # True: 오름차순, False: 내림차순

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
        self.info_text = wx.StaticText(panel,
            label=f"총 {len(self.files)}개의 파일이 있습니다. "
                  "다운로드할 파일을 선택하세요.")
        self.info_text.SetFont(self.default_font)
        main_sizer.Add(self.info_text, 0, wx.ALL, 10)

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
        dialog_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 왼쪽: 삭제 버튼들
        delete_selected_btn = wx.Button(panel, label="선택 삭제")
        delete_selected_btn.Bind(wx.EVT_BUTTON, self.on_delete_selected)
        dialog_btn_sizer.Add(delete_selected_btn, 0, wx.RIGHT, 5)

        delete_all_btn = wx.Button(panel, label="전체 삭제")
        delete_all_btn.Bind(wx.EVT_BUTTON, self.on_delete_all)
        dialog_btn_sizer.Add(delete_all_btn, 0, wx.RIGHT, 5)

        # 공간 추가 (왼쪽과 오른쪽 버튼 분리)
        dialog_btn_sizer.AddStretchSpacer()

        # 오른쪽: 수집/취소 버튼들
        ok_btn = wx.Button(panel, wx.ID_OK, "수집")
        ok_btn.Bind(wx.EVT_BUTTON, self.on_ok)
        dialog_btn_sizer.Add(ok_btn, 0, wx.RIGHT, 5)

        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "취소")
        cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        dialog_btn_sizer.Add(cancel_btn, 0)

        main_sizer.Add(dialog_btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        panel.SetSizer(main_sizer)

        # 리스트 이벤트 바인딩
        self.file_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.file_list.Bind(wx.EVT_LIST_COL_CLICK, self.on_column_click)

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

    def on_column_click(self, event):
        """컬럼 클릭 시 정렬"""
        column = event.GetColumn()

        # 선택 컬럼(0번)은 정렬하지 않음
        if column == 0:
            return

        # 같은 컬럼을 클릭하면 오름차순/내림차순 토글
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            # 다른 컬럼을 클릭하면 해당 컬럼으로 오름차순 정렬
            self.sort_column = column
            self.sort_ascending = True

        # 정렬 실행
        self.sort_files()

        # UI 갱신
        self.load_file_list()

        logger.info(f"컬럼 {column} 정렬: {'오름차순' if self.sort_ascending else '내림차순'}")

    def sort_files(self):
        """파일 목록 정렬"""
        if self.sort_column is None or not self.files:
            return

        # 컬럼별 정렬 키 함수
        if self.sort_column == 1:  # 파일명
            key_func = lambda f: f.name.lower()
        elif self.sort_column == 2:  # 크기
            key_func = lambda f: f.size
        elif self.sort_column == 3:  # 수정 시간
            key_func = lambda f: f.modified_time
        elif self.sort_column == 4:  # 경로
            key_func = lambda f: f.path.lower()
        else:
            return

        # 정렬
        self.files.sort(key=key_func, reverse=not self.sort_ascending)

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

    def on_delete_selected(self, event):
        """선택한 파일 삭제"""
        if not self.file_collector:
            wx.MessageBox("삭제 기능을 사용할 수 없습니다.", "오류",
                         wx.OK | wx.ICON_ERROR)
            return

        selected_files = self.get_selected_files()

        if not selected_files:
            wx.MessageBox("삭제할 파일을 선택하세요.", "선택 오류",
                         wx.OK | wx.ICON_WARNING)
            return

        # 확인 메시지
        count = len(selected_files)
        total_size = sum(f.size for f in selected_files)
        size_str = self.format_size(total_size)

        msg = (f"선택한 {count}개 파일 (총 {size_str})을 삭제하시겠습니까?\n\n"
               f"⚠️ 이 작업은 되돌릴 수 없습니다!")

        result = wx.MessageBox(msg, "삭제 확인",
                              wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)

        if result == wx.YES:
            self.delete_files(selected_files)

    def on_delete_all(self, event):
        """전체 파일 삭제"""
        if not self.file_collector:
            wx.MessageBox("삭제 기능을 사용할 수 없습니다.", "오류",
                         wx.OK | wx.ICON_ERROR)
            return

        if not self.files:
            wx.MessageBox("삭제할 파일이 없습니다.", "알림",
                         wx.OK | wx.ICON_INFORMATION)
            return

        # 확인 메시지
        count = len(self.files)
        total_size = sum(f.size for f in self.files)
        size_str = self.format_size(total_size)

        msg = (f"전체 {count}개 파일 (총 {size_str})을 삭제하시겠습니까?\n\n"
               f"⚠️ 이 작업은 되돌릴 수 없습니다!")

        result = wx.MessageBox(msg, "삭제 확인",
                              wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)

        if result == wx.YES:
            self.delete_files(self.files)

    def delete_files(self, files_to_delete: List[FileInfo]):
        """파일 삭제 실행"""
        # 진행 다이얼로그 표시
        progress_dlg = wx.ProgressDialog(
            "파일 삭제 중",
            f"총 {len(files_to_delete)}개 파일을 삭제하는 중...",
            maximum=100,
            parent=self,
            style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE
        )

        try:
            # 파일 삭제 실행
            success_count, fail_count = self.file_collector.delete_files(files_to_delete)

            # 결과 표시
            if fail_count == 0:
                message = f"총 {len(files_to_delete)}개 파일 삭제 완료!"
                wx.MessageBox(message, "삭제 완료", wx.OK | wx.ICON_INFORMATION)
            else:
                message = (f"삭제 결과:\n\n"
                          f"성공: {success_count}개\n"
                          f"실패: {fail_count}개\n"
                          f"전체: {len(files_to_delete)}개")
                wx.MessageBox(message, "삭제 완료", wx.OK | wx.ICON_WARNING)

            # 삭제된 파일을 목록에서 제거
            self.remove_deleted_files(files_to_delete, success_count)

        except Exception as e:
            logger.error(f"파일 삭제 중 오류: {e}")
            wx.MessageBox(f"파일 삭제 실패:\n{str(e)}",
                         "오류", wx.OK | wx.ICON_ERROR)
        finally:
            progress_dlg.Destroy()

    def remove_deleted_files(self, deleted_files: List[FileInfo], success_count: int):
        """삭제된 파일을 목록에서 제거하고 서버에서 최신 목록 조회"""
        if success_count == 0:
            return

        # 파일 목록을 서버에서 다시 조회
        if self.file_collector and self.log_source_config:
            try:
                # 진행 다이얼로그 표시
                progress_dlg = wx.ProgressDialog(
                    "파일 목록 갱신 중",
                    "서버에서 최신 파일 목록을 조회하는 중...",
                    maximum=100,
                    parent=self,
                    style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH
                )
                progress_dlg.Pulse()

                # 파일 목록 재조회
                updated_files = self.file_collector.get_file_list(self.log_source_config)

                # 파일 목록 업데이트
                self.files = updated_files

                # 진행 다이얼로그 닫기
                progress_dlg.Destroy()

                logger.info(f"파일 목록 갱신 완료: {len(self.files)}개 파일")

            except Exception as e:
                logger.error(f"파일 목록 갱신 실패: {e}")
                # 실패 시 로컬에서 제거된 파일만 필터링
                deleted_paths = {f.get_full_path() for f in deleted_files}
                self.files = [f for f in self.files if f.get_full_path() not in deleted_paths]
        else:
            # file_collector나 log_source_config가 없으면 로컬에서만 제거
            deleted_paths = {f.get_full_path() for f in deleted_files}
            self.files = [f for f in self.files if f.get_full_path() not in deleted_paths]

        # UI 갱신
        self.load_file_list()

        # 정보 텍스트 업데이트
        self.info_text.SetLabel(f"총 {len(self.files)}개의 파일이 있습니다. "
                               "다운로드할 파일을 선택하세요.")

    def format_size(self, size_bytes: int) -> str:
        """파일 크기를 사람이 읽기 쉬운 형태로 변환"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
