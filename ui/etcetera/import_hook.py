
class ImportProgressHook:
    """임포트 진행률 훅 클래스입니다.
    모듈 임포트 시 스플래시 화면에 진행률을 표시합니다.
    """
    def __init__(self, splash):
        self.splash = splash
        self.original_import = None
        self.modules = [
            'ui.ui_mainwindow',
            'ui.set_style',

            'utility.settings.setting_user',
            'utility.settings.setting_base',
            'utility.sub_process_and_thread.timesync',
            'utility.db_control.database_read_only',
            'utility.sub_process_and_thread.webcrawling',
            'utility.sub_process_and_thread.telegram_bot',
            'utility.sub_process_and_thread.chart_hoga_query_sound',
            'utility.static_method.static',

            'ui.create_widget.set_icon',
            'ui.create_widget.set_table',
            'ui.create_widget.set_log_tap',
            'ui.create_widget.set_home_tap',
            'ui.create_widget.set_widget',
            'ui.create_widget.set_setup_tap',
            'ui.create_widget.set_order_tap',
            'ui.create_widget.set_main_menu',
            'ui.create_widget.set_stg_tap',
            'ui.create_widget.set_dialog_etc',
            'ui.create_widget.set_dialog_back',
            'ui.create_widget.set_dialog_chart',
            'ui.create_widget.set_dialog_formula',
            'ui.create_widget.set_dialog_strategy',

            'ui.etcetera.etc',
            'ui.draw_chart.draw_treemap',
            'ui.draw_chart.draw_chart_db',
            'ui.etcetera.load_database',
            'ui.etcetera.monitor_windowQ',
            'ui.etcetera.process_starter',
            'ui.draw_chart.draw_home_chart',
            'ui.draw_chart.draw_chart_real',
            'ui.update_widget.update_textedit',
            'ui.create_widget.set_text_stg_button',
            'ui.update_widget.update_tablewidget',
            'ui.update_widget.update_telegram_msg',
            'ui.event_click.button_clicked_settings',
            'ui.update_widget.update_crawling_date',
            'ui.event_keypress.overwrite_keypress_event',
            'ui.event_keypress.overwrite_event_filter',
            'ui.etcetera.process_alive',
            'ui.update_widget.update_progressbar',
            'ui.event_click.button_clicked_backtest_engine',
        ]
        self.total_modules = len(self.modules)
        self.current_index = 0

    def custom_import(self, name, *args, **kwargs):
        """커스텀 임포트 함수입니다.
        모듈 임포트 시 진행률을 업데이트합니다.
        Args:
            name: 모듈 이름
            *args: 가변 인자
            **kwargs: 키워드 인자
        Returns:
            임포트된 모듈
        """
        if name in self.modules:
            self.current_index += 1
            progress = (self.current_index / self.total_modules) * 49
            self.splash.show_progress(f"{name}...", int(progress))
        return self.original_import(name, *args, **kwargs)

    def install(self):
        import builtins
        """훅을 설치합니다."""
        self.original_import = builtins.__import__
        builtins.__import__ = self.custom_import

    def uninstall(self):
        import builtins
        """훅을 제거합니다."""
        builtins.__import__ = self.original_import
