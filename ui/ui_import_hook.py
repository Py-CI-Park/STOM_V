
import builtins


class ImportProgressHook:
    def __init__(self, splash):
        self.splash          = splash
        self.progress        = 5
        self.original_import = None
        self.modules = [
            'ui.ui_mainwindow', 'ui.set_style', 'utility.chartquerysound', 'utility.timesync', 'utility.setting_base',
            'utility.webcrawling', 'utility.telegram_bot', 'utility.setting_user', 'utility.static',
            'utility.database_read_only', 'ui.set_icon', 'ui.set_table', 'ui.set_log_tap', 'ui.set_home_tap',
            'ui.set_widget', 'ui.set_setup_tap', 'ui.set_order_tap', 'ui.set_main_menu', 'ui.set_dialog_etc',
            'ui.set_dialog_back', 'ui.set_stg_coin_tap', 'ui.set_dialog_chart', 'ui.set_stg_stock_tap',
            'ui.set_dialog_formula', 'ui.set_dialog_strategy', 'ui.ui_draw_treemap', 'ui.ui_draw_chart_db',
            'ui.ui_load_database', 'ui.ui_extend_window', 'ui.ui_draw_home_chart', 'ui.ui_draw_chart_real',
            'ui.ui_update_textedit', 'ui.ui_process_starter', 'ui.ui_update_tablewidget',
            'ui.ui_chart_count_change', 'ui.ui_etc', 'ui.ui_show_dialog', 'ui.ui_vars_change', 'ui.ui_event_filter',
            'ui.ui_return_press', 'ui.ui_text_changed', 'ui.ui_cell_clicked', 'ui.ui_activated_etc',
            'ui.ui_process_alive', 'ui.ui_activated_back', 'ui.ui_key_press_event', 'ui.ui_backtest_engine',
            'ui.ui_checkbox_changed', 'ui.ui_update_progressbar', 'ui.ui_button_clicked_etc',
            'ui.ui_activated_coin_stg', 'ui.ui_button_clicked_zoom', 'ui.ui_activated_stock_stg',
            'ui.ui_button_clicked_order', 'ui.ui_button_clicked_chart', 'ui.ui_button_clicked_shortcut',
            'ui.ui_button_clicked_strategy', 'ui.ui_button_clicked_settings', 'ui.ui_button_clicked_editer_coin',
            'ui.ui_button_clicked_editer_stock', 'ui.ui_button_clicked_dialog_formula',
            'ui.ui_button_clicked_editer_ga_coin', 'ui.ui_button_clicked_editer_backlog',
            'ui.ui_button_clicked_dialog_database', 'ui.ui_button_clicked_editer_ga_stock',
            'ui.ui_button_clicked_editer_opti_coin', 'ui.ui_button_clicked_dialog_backengine',
            'ui.ui_button_clicked_editer_opti_stock', 'ui.ui_button_clicked_editer_stg_buy_coin',
            'ui.ui_button_clicked_editer_stg_sell_coin', 'ui.ui_button_clicked_editer_stg_buy_stock',
            'ui.ui_button_clicked_editer_stg_sell_stock', 'ui.ui_button_clicked_dialog_elapsed_tick_number'
        ]
        self.total_modules = len(self.modules)
        self.current_index = 0

    def custom_import(self, name, *args, **kwargs):
        if name in self.modules:
            self.current_index += 1
            progress = self.progress + (self.current_index / self.total_modules) * 73
            self.splash.show_progress(f"{name}...", int(progress))
        return self.original_import(name, *args, **kwargs)

    def install(self):
        self.original_import = builtins.__import__
        builtins.__import__ = self.custom_import

    def uninstall(self):
        builtins.__import__ = self.original_import
