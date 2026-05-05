
class UpdateCrawlingData:
    """웹크롤링 스레드가 보내온 데이터를 처리합니다."""
    def __init__(self, ui):
        self.ui = ui

    def update_crawling_data(self, data):
        from ui.etcetera.etc import update_image
        from utility.settings.setting_base import UI_NUM

        if data[0] == UI_NUM['홈차트']:
            self.ui.draw_homechart.draw_home_chart(data)

        elif data[0] == UI_NUM['풍경사진']:
            update_image(self.ui, data)

        elif data[0] == UI_NUM['기업개요']:
            self.ui.update_textedit.update_texedit(data)

        elif data[0] in (UI_NUM['기업공시'], UI_NUM['기업뉴스'], UI_NUM['재무년도'], UI_NUM['재무분기']):
            self.ui.update_tablewidget.update_tablewidget(data)

        elif data[0] in (UI_NUM['트리맵'], UI_NUM['트리맵1'], UI_NUM['트리맵2']):
            self.ui.draw_treemap.draw_treemap(data)

        elif data[0] == UI_NUM['시스템로그']:
            self.ui.update_textedit.update_texedit(data)
