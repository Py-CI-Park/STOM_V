def apply_telegram_settings_save(ui, gubun, str_bot, int_id, encrypt_text):
    en_str_bot = encrypt_text(ui.dict_set['키'], str_bot)
    en_int_id = encrypt_text(ui.dict_set['키'], int_id)
    query = 'UPDATE telegram SET str_bot = ?, int_id = ? WHERE `index` = ?'
    values = (en_str_bot, en_int_id, gubun)
    ui.queryQ.put(('설정디비', query, values))

    ui.dict_set[f'텔레그램봇토큰{gubun}'] = str_bot
    ui.dict_set[f'텔레그램사용자아이디{gubun}'] = int(int_id)
    ui.UpdateDictSet()
