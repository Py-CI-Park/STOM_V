from utility.telegram_bot import TelegramBot


def TelegramMsg(qlist):
    """
    Wrapper function for TelegramBot to be used as a multiprocessing.Process target.

    Args:
        qlist: List of queues for inter-process communication
               windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ, cstgQ, liveQ, kimpQ, wdzservQ, totalQ
               0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
    """
    TelegramBot(qlist)
