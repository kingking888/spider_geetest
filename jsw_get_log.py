import logging
import os


def jsw_get_log(dir_name):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    log_path = os.path.dirname(os.getcwd()) + "/" + dir_name + "/Logs/"
    log_name = log_path + "/log" + '.log'
    logfile = log_name
    file_handler = logging.FileHandler(logfile)   # 输入到文件
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s:"
                                  "%(message)s")

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
