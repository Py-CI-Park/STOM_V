
from PyQt5.QtGui import QIcon
from ui.set_widget import error_decorator
from utility.setting_base import ICON_PATH


class SetIcon:
    def __init__(self, ui_class):
        self.ui = ui_class
        self.set()

    @error_decorator
    def set(self):
        self.ui.icon_main    = QIcon(f'{ICON_PATH}/python.png')
        self.ui.icon_home    = QIcon(f'{ICON_PATH}/home.png')
        self.ui.icon_stock   = QIcon(f'{ICON_PATH}/stock.png')
        self.ui.icon_coin    = QIcon(f'{ICON_PATH}/coin.png')
        self.ui.icon_set     = QIcon(f'{ICON_PATH}/set.png')
        self.ui.icon_live    = QIcon(f'{ICON_PATH}/live.png')
        self.ui.icon_log     = QIcon(f'{ICON_PATH}/log.png')
        self.ui.icon_log2    = QIcon(f'{ICON_PATH}/log2.png')
        self.ui.icon_total   = QIcon(f'{ICON_PATH}/total.png')
        self.ui.icon_start   = QIcon(f'{ICON_PATH}/start.png')
        self.ui.icon_dbdel   = QIcon(f'{ICON_PATH}/dbdel.png')
        self.ui.icon_stocks  = QIcon(f'{ICON_PATH}/stocks.png')
        self.ui.icon_stocks2 = QIcon(f'{ICON_PATH}/stocks2.png')
        self.ui.icon_coins   = QIcon(f'{ICON_PATH}/coins.png')
        self.ui.icon_coins2  = QIcon(f'{ICON_PATH}/coins2.png')

        self.ui.icon_open    = QIcon(f'{ICON_PATH}/open.bmp')
        self.ui.icon_high    = QIcon(f'{ICON_PATH}/high.bmp')
        self.ui.icon_low     = QIcon(f'{ICON_PATH}/low.bmp')
        self.ui.icon_up      = QIcon(f'{ICON_PATH}/up.bmp')
        self.ui.icon_down    = QIcon(f'{ICON_PATH}/down.bmp')
        self.ui.icon_vi      = QIcon(f'{ICON_PATH}/vi.bmp')
        self.ui.icon_totals  = QIcon(f'{ICON_PATH}/totals.bmp')
        self.ui.icon_totalb  = QIcon(f'{ICON_PATH}/totalb.bmp')

        self.ui.icon_korea   = QIcon(f'{ICON_PATH}/korea.png')
        self.ui.icon_usdkrw  = QIcon(f'{ICON_PATH}/usdkrw.png')
        self.ui.icon_oilgsl  = QIcon(f'{ICON_PATH}/oilgsl.png')
        self.ui.icon_gold    = QIcon(f'{ICON_PATH}/gold.png')

        self.ui.icon_btc     = QIcon(f'{ICON_PATH}/BTC.png')
        self.ui.icon_eth     = QIcon(f'{ICON_PATH}/ETH.png')
        self.ui.icon_xrp     = QIcon(f'{ICON_PATH}/XRP.png')
        self.ui.icon_bnb     = QIcon(f'{ICON_PATH}/BNB.png')

        self.ui.icon_sol     = QIcon(f'{ICON_PATH}/SOL.png')
        self.ui.icon_doge    = QIcon(f'{ICON_PATH}/DOGE.png')
        self.ui.icon_ada     = QIcon(f'{ICON_PATH}/ADA.png')
        self.ui.icon_link    = QIcon(f'{ICON_PATH}/LINK.png')
