import os
import sys
# Interface
import curses
# FTP
import ftplib
# PostgresQL
import psycopg2
# md5
import hashlib
# Logging
import logging

# Включаем протоколирование ошибок и сообщений
logging.basicConfig(filename='log.txt', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def chdir(dir, ftp):
    """Change directories - create if it doesn't exist"""
    if directory_exists(dir, ftp) is False:
        ftp.mkd(dir)
    ftp.cwd(dir)

def directory_exists(dir, ftp):
    """Check if directory exists (in current location)"""
    filelist = []
    ftp.retrlines('LIST', filelist.append)
    for f in filelist:
        if f.split()[-1] == dir and f.upper().startswith('D'):
            return True
    return False


class Products():
    """Хранит данные об изделиях, блока и подблоках"""

    def __init__(self, params):
        self.dct = {}
        for tpl in params:
            self.dct.setdefault(tpl[3], {})
            self.dct[tpl[3]].setdefault(tpl[2], [])
            self.dct[tpl[3]][tpl[2]].append(tpl[1])

    def get_products(self):
        """Возвращает список изделий"""
        return list(self.dct.keys())

    def get_blocks(self, key):
        """Возвращает список блоков"""
        return list(self.dct[key].keys())

    def get_sblocks(self, pkey, bkey):
        """Возвращает список подблоков"""
        return self.dct[pkey][bkey][:]


class Printer():
    """Формирует список строк для отображения"""

    def __init__(self, prod, cur):
        self.data = prod
        self.pkey = ''
        self.bkey = ''
        self.sbkey =''
        self.md5 = ''
        self.position = 0
        self.current_str = 0
        self.max_strings = 0 # макс кол-во строк для отображения и выбора
        self.cur = cur

    def move_position(self, step, key=''):
        """Меняет текущую позицию"""
        #logging.info(key)
        self.position += step
        if self.position < 0:
            self.position = 0
        elif self.position > 5:
            self.position = 0

        if self.position == 1 and key:
            self.pkey = key
        elif self.position == 2 and key:
            self.bkey = key
        elif self.position == 3 and key:
            self.sbkey = key
        elif self.position == 5 and key:
            self.md5 = key.split(' | ')[3]

    def move_current_str(self, step):
        """Перемещает указатель на выбранную строку"""
        self.current_str += step

        if self.current_str <= 0:
            self.current_str = 0
        elif self.current_str >= self.max_strings:
            self.current_str = self.max_strings

    def get_data(self):
        """Возвращает строки для отображения на экране терминала"""
        if self.position == 0:
            ret_val = self.data.get_products()
            self.max_strings = len(ret_val) - 1
            return ret_val
        elif self.position == 1:
            ret_val = self.data.get_blocks(self.pkey)
            self.max_strings = len(ret_val) - 1
            return ret_val
        elif self.position == 2:
            self.current_str = 0
            ret_val = self.data.get_sblocks(self.pkey, self.bkey)
            self.max_strings = len(ret_val) - 1
            return ret_val
        elif self.position == 3:
            self.max_strings = 3
            return ['Текущая прошивка блока', 'Добавить СПО в базу',
                    'Журнал запросов СПО', 'Каталог СПО блока']
        elif self.position == 4 and self.current_str == 0:
            request = "SELECT log.date, to_char(log.time, 'HH24:MM:SS'), spo.ksum, spo.md5, spo.comment, spo.is_official FROM spoquerylog AS log JOIN spo ON log.spo_id=spo.id WHERE log.owner_id=(SELECT id FROM ownersSPO WHERE products_name='" + self.pkey + "' AND block_name='" + self.bkey + "' AND sub_block_name='" + self.sbkey + "') ORDER BY log.id DESC LIMIT 1;"
            self.cur.execute(request)
            self.current_str = 0
            ret_val = list(" | ".join(str(item) for item in line)
                           for line in self.cur.fetchall())
            self.max_strings = len(ret_val) - 1
            return ret_val
        elif self.position == 4 and self.current_str == 1:
            request = "SELECT MAX(id) FROM spo;"
            self.cur.execute(request)
            self.current_str = 0
            return int(self.cur.fetchall()[0][0])
        elif self.position == 4 and self.current_str == 2:
            request = "SELECT log.date, to_char(log.time, 'HH24:MM:SS'), spo.ksum, spo.md5, spo.comment, spo.is_official FROM spoquerylog AS log JOIN spo ON log.spo_id=spo.id WHERE log.owner_id=(SELECT id FROM ownersSPO WHERE products_name='" + self.pkey + "' AND block_name='" + self.bkey + "' AND sub_block_name='" + self.sbkey + "') ORDER BY log.id DESC;"
            self.cur.execute(request)
            self.current_str = 0
            ret_val = list(" | ".join(str(item) for item in line)
                           for line in self.cur.fetchall())
            self.max_strings = len(ret_val) - 1
            return ret_val
        elif self.position == 4 and self.current_str == 3:
            request = "SELECT spo.date, spo.is_official, spo.ksum, spo.md5, spo.comment FROM spo WHERE spo.owner_id=(SELECT id FROM ownersSPO WHERE products_name='" + self.pkey + "' AND block_name='" + self.bkey + "' AND sub_block_name='" + self.sbkey + "') ORDER BY spo.id DESC;"
            self.cur.execute(request)
            self.current_str = 0
            ret_val = list(" | ".join(str(item) for item in line)
                           for line in self.cur.fetchall())
            self.max_strings = len(ret_val) - 1
            return ret_val
        elif self.position == 5:
            request = "SELECT path FROM spo WHERE md5='" + self.md5 + "';"
            self.cur.execute(request)
            self.current_str = 0
            return str(self.cur.fetchall()[0][0])

        return []


def select(cur, from_, select='*', where=''):
    """
    Запрос данных из таблицы
    Образец запроса для получения списка таблиц:
    (SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public';)
    """

    if len(where) == 0:
        request = ("SELECT " + select + " FROM " + from_ +";")
    else:
        request = ("SELECT " + select + " FROM " + from_ + " WHERE "
                   + where +";")
    # Sending request
    cur.execute(request)
    # Return request result
    return cur.fetchall()

def draw_menu(stdscr, connection_status, user, conn):
    """Отрисовка"""

    # Для работы с PostgresQL
    cur = conn.cursor()

    # Нажатая клавиша
    k = 0

    # Текущая строка, на которой находится курсор
    current_str = ''

    # Начальное положение  курсора
    cursor_x = 6
    cursor_y = 5

    # Clear and refresh the screen for a blank canvas
    stdscr.clear()
    stdscr.refresh()

    # Start colors in curses
    curses.start_color()
    # curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    # curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

    # Инициализируем экземпляр класса Принтер и получаем первую таблицу
    printer = Printer(Products(select(cur, 'ownersSPO')), cur)
    data = printer.get_data()

    # Получаем размеры терминала
    height, width = stdscr.getmaxyx()

    # Начальные отступы выводимых строк от верхнего левого края терминала,
    # где начало координат: y=0,x=0
    start_x = 5
    start_y = 5
    # Максимально возможное кол-во строк для отображения
    max_lines = int((height - start_y - 1)/2)

    while (k != 27):    # 'Esc'

        # Очистка экрана терминала
        stdscr.clear()

        # Начальное смещение по Y для отрисовки строк
        offset_y = 0

        # Отрисовать рамку
        # stdscr.border(0)

        # Скрыть мигающий курсор ('_')
        curses.curs_set(0)

        # Обработка нажатия клавиш управления работой приложения
        if k == curses.KEY_DOWN:
            cursor_y = cursor_y + 2
            printer.move_current_str(1)
        elif k == curses.KEY_UP:
            cursor_y = cursor_y - 2
            printer.move_current_str(-1)
        elif k == curses.KEY_LEFT:
            cursor_y = 5
            printer.move_position(-1)
            # отрисовка текущей таблицы
            data = printer.get_data()
        elif k == curses.KEY_RIGHT:
            cursor_y = 5
            printer.move_position(1, current_str)
            # отрисовка текущей таблицы
            data = printer.get_data()

        # формируем статус-бар
        statusbarstr = (connection_status + ' as ' + user + ', position: '
                        + str(printer.position) + ' current str: '
                        + str(printer.current_str) + '.  Max lines: '
                        + str(max_lines) + '. Data: ' + str(len(data)))

        # Если отрисовываем таблицу
        stdscr.attron(curses.A_BOLD)
        if type(data) is list:
            if len(data):
                # Если все строки помещаются на экран за раз
                if len(data) <= max_lines:
                    for line in data:
                        stdscr.addstr(start_y + offset_y, start_x,
                                      '[ ]\t' + line)
                        offset_y += 2
                # Если все строки не помещаются на экран
                else:
                    # Вычисляем интервал среза для вывода в терминал
                    if (printer.current_str - max_lines + 1) <= 0:
                        interval = 0
                    else:
                        interval = printer.current_str - max_lines + 1

                    for line in data[interval:interval + max_lines]:
                        stdscr.addstr(start_y + offset_y, start_x,
                                      '[ ]\t' + line)
                        offset_y += 2
            else:
                    stdscr.addstr(start_y + offset_y, start_x,
                                  '[ ]\t' + 'Нет данных')
                    offset_y += 2
        # Если заливаем новую прошивку в базу
        elif type(data) is int:
            # Просим пользователя ввести путь до файла прошивки
            stdscr.addstr(start_y + offset_y, start_x,
                          'Укажите имя файла СПО: ')
            # Формируем путь до файла СПО на FTP-сервере
            st = (printer.pkey + '/' + printer.bkey + '/' + printer.sbkey +
                  '/' + str(data+1))
            # Переводим путь в int-представление
            st = ''.join(map(str,list(map(lambda x: '/' if x=='/' else ord(x),
                         st))))
            # Ожидаем ввода пути до файла с прошивкой
            curses.echo()
            path = stdscr.getstr().strip().decode("utf-8")
            curses.noecho()
            # Вынимаем имя файла из абсолютного пути до файла прошивки
            file_name = path.split('\\')[-1]
            # Пробуем открыть указанный файл для подсчета md5
            try:
                with open(path,'rb') as f:
                    # Подсчет md5
                    hash = hashlib.md5(f.read()).hexdigest()
                    stdscr.addstr(start_y + offset_y, start_x,
                                  '\t' + st + '/' + file_name + '\t' + hash)
                    # Проверяем налчие прошики с данной md5 в базе
                    request = "SELECT md5 FROM spo WHERE owner_id=(SELECT id FROM ownersSPO WHERE products_name='" + printer.pkey + "' AND block_name='" + printer.bkey + "' AND sub_block_name='" + printer.sbkey + "');"
                    cur.execute(request)
                    # Если прошивка с указанной md5 уже есть в базе - СТОП
                    if (hash,) in cur.fetchall():
                        stdscr.addstr(start_y + offset_y, start_x,
                                      '\nСПО С ДАННОЙ md5 УЖЕ ИМЕЕТСЯ В БАЗЕ!')
                    else:
                        try:
                            # Создаем директорию с именем st на FTP-сервере
                            ftp = ftplib.FTP('192.168.7.24')
                            ftp.login(user='ftp_user', passwd='ftp')
                            dir_list = st.split('/')
                            ftp.cwd('files')
                            for dir in dir_list:
                                chdir(dir, ftp)
                            # Пишем файл file_name в созданную директорию
                            ftp.storbinary('STOR ' + file_name, open(path,'rb'))
                            # Закрываем FTP-сессию
                            ftp.close()
                            # Заполняем оставшиеся атрибуты прошивки
                            stdscr.addstr(start_y + offset_y + 2, start_x,
                                          'Укажите контрольную сумму СПО: ')
                            curses.echo()
                            ksum = stdscr.getstr().strip().decode("utf-8")
                            curses.noecho()
                            stdscr.addstr(start_y + offset_y + 4, start_x,
                                          'Укажите комментарий: ')
                            curses.echo()
                            comment = stdscr.getstr().strip().decode("utf-8")
                            curses.noecho()
                            stdscr.addstr(start_y + offset_y + 6, start_x,
                                          'Статус СПО (True или False): ')
                            curses.echo()
                            stat = stdscr.getstr().strip().decode("utf-8")
                            curses.noecho()
                            # Формируем запрос для добавления записи о прошике в базу
                            request = "SELECT id FROM ownersSPO WHERE products_name='" + printer.pkey + "' AND block_name='" + printer.bkey + "' AND sub_block_name='" + printer.sbkey + "';"
                            cur.execute(request)
                            id = cur.fetchall()[0][0]
                            request = "INSERT INTO spo(owner_id, ksum, md5, path, comment, is_official) VALUES(" + str(id) + ", '" + str(ksum) + "', '" + str(hash) + "', '" + st + "/" + file_name + "', '" + str(comment) + "', " + str(stat) + ");"
                            cur.execute(request)
                            conn.commit()
                            stdscr.addstr(start_y + offset_y + 8, start_x,
                                          'Спо добавлено в базу'.upper())
                        except Exception as err:
                            stdscr.addstr(start_y + offset_y, start_x,
                                          '\nОШИБКА ЗАГРУЗКИ ФАЙЛА НА FTP!')
                            logging.error(str(err))

            # Если не смогли открыть файл с прошивкой
            except Exception as err:
                stdscr.addstr(start_y + offset_y, start_x, '\nФАЙЛ НЕ НАЙДЕН!')
                logging.error(str(err))
            offset_y += 2
        # Если выкачиваем прошивку из базы
        elif type(data) is str:
            stdscr.addstr(start_y + offset_y, start_x,
                          'УКАЖИТЕ, КУДА СОХРАНИТЬ ПРОШИВКУ '
                          + data.split('/')[-1] +' : ')
            curses.echo()
            spo_path = stdscr.getstr().strip().decode("utf-8")
            # Добавляем слеш в конец строки с путем сохранения прошивки
            if spo_path[-1] != '\\':
                spo_path += '\\'
            curses.noecho()
            # Подключаемся к FTP-серверу
            try:
                ftp = ftplib.FTP('192.168.7.24')
                ftp.login(user='ftp_user', passwd='ftp')
                ftp.retrbinary('RETR files/' + data,
                               open(spo_path + data.split('/')[-1], 'wb').write)
                ftp.close()
                request = "SELECT id, owner_id FROM spo WHERE md5='" + printer.md5 + "';"
                cur.execute(request)
                s, o = cur.fetchall()[0]
                request = "INSERT INTO spoquerylog(spo_id, owner_id) VALUES(" + str(s) + ", " + str(o) + ");"
                cur.execute(request)
                conn.commit()
            except Exception as err:
                stdscr.addstr(start_y + offset_y, start_x,
                              '\nОШИБКА СОХРАНЕНИЯ ФАЙЛА!')
                logging.error(str(err))

        stdscr.attroff(curses.A_BOLD)

        offset_y -= 2

        # Set cursor borders
        if cursor_y < 5:
            cursor_y = 5

        if cursor_y > start_y + offset_y or ((printer.current_str - max_lines + 1) >= 0):
            cursor_y = start_y + offset_y


        # Render status bar
        stdscr.attron(curses.color_pair(3))
        stdscr.addstr(height-1, 0, statusbarstr)
        stdscr.addstr(height-1, len(statusbarstr),
                      " " * (width - len(statusbarstr) - 1))
        stdscr.attroff(curses.color_pair(3))

        # Move cursor to position (cursor_y, cursor_x)

        stdscr.move(cursor_y, cursor_x)

        # Draw current cursor position
        stdscr.addstr(cursor_y, cursor_x, '*')

        current_str = stdscr.instr(cursor_y, cursor_x + 2).strip().decode("utf-8")

        # Refresh the screen
        stdscr.refresh()

        # Wait for next input
        k = stdscr.getch()

    # End SQL sesion
    cur.close()
    conn.close()

    logging.info('Завершение сеанса')

def main():

    if len(sys.argv) > 1:
        dbname = str(sys.argv[1])
        user =   str(sys.argv[2])
        try:
            passwd = str(sys.argv[3])
        except IndexError:
            logging.warning('Вход без пароля!')
            passwd = None
    else:
        dbname = input('Укажите БД: ')
        user = input('Логин: ')
        passwd = input('Пароль: ')

    # Try to connect to DataBase
    try:
        """Connect to PostgresQL server"""
        conn = psycopg2.connect(dbname=dbname, host='192.168.7.24', user=user,
                                passwd=passwd)
    except Exception as err:
        print('DataBase connection error!')
        logging.critical(str(err))
        exit()

    # Resize terminal in Windows
    if os.name == 'nt':
        os.system('mode con: cols=150 lines=50')

    logging.info('Подключен к БД ' + dbname + ' как ' + user)
    # Start curses
    curses.wrapper(draw_menu, 'Connected to database ' + dbname, user, conn)

    # Resize terminal in Windows
    if os.name == 'nt':
        os.system("mode con: cols=80 lines=24")

if __name__ == "__main__":

    main()
