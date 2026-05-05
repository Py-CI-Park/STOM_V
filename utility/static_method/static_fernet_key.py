
def write_key():
    """암호화 키를 레지스트리에 저장합니다."""
    import winreg as reg
    from cryptography.fernet import Fernet
    key = str(Fernet.generate_key(), 'utf-8')
    reg.CreateKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM')
    reg.CreateKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM\EN_KEY')
    openkey = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM\EN_KEY', 0, reg.KEY_ALL_ACCESS)
    reg.SetValueEx(openkey, 'EN_KEY', 0, reg.REG_SZ, key)
    reg.CloseKey(openkey)


def read_key():
    """레지스트리에서 암호화 키를 읽습니다.
    Returns:
        암호화 키
    """
    import winreg as reg
    openkey = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\STOM\EN_KEY', 0, reg.KEY_ALL_ACCESS)
    key, _ = reg.QueryValueEx(openkey, 'EN_KEY')
    reg.CloseKey(openkey)
    return key


def en_text(key, text):
    """텍스트를 암호화합니다.
    Args:
        key: 암호화 키
        text: 암호화할 텍스트
    Returns:
        암호화된 텍스트
    """
    from cryptography.fernet import Fernet
    fernet = Fernet(bytes(key, 'utf-8'))
    return str(fernet.encrypt(bytes(text, 'utf-8')), 'utf-8')


def de_text(key, text):
    """텍스트를 복호화합니다.
    Args:
        key: 암호화 키
        text: 복호화할 텍스트
    Returns:
        복호화된 텍스트
    """
    from cryptography.fernet import Fernet
    fernet = Fernet(bytes(key, 'utf-8'))
    return str(fernet.decrypt(bytes(text, 'utf-8')), 'utf-8')
