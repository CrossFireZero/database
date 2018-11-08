import os
# Interface
import curses
# FTP
import ftplib
# PostgresQL
import psycopg2
# md5
import hashlib


def chdir(dir, ftp):
    """Change directories - create if it doesn't exist"""
    if directory_exists(dir, ftp) is False: # (or negate, whatever you prefer for readability)
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
        self.position = 0
        self.current_str = 0
        self.cur = cur


    def move_position(self, step, key=''):
        """Меняет текущую позицию"""
        self.position += step
        if self.position < 0:
            self.position = 0
        elif self.position > 4:
            self.position = 0

        if self.position == 1 and key:
            self.pkey = key
        elif self.position == 2 and key:
            self.bkey = key
        elif self.position == 3 and key:
            self.sbkey = key


    def move_current_str(self, step):
        """Перемещает указатель на выбранную строку"""
        self.current_str += step


    def get_data(self):
        """Возвращает строки для отображения на экране терминала"""
        if self.position == 0:
            return self.data.get_products()
        elif self.position == 1:
            return self.data.get_blocks(self.pkey)
        elif self.position == 2:
            self.current_str = 0
            return self.data.get_sblocks(self.pkey, self.bkey)
        elif self.position == 3:
            return ['Текущая прошивка блока', 'Добавить СПО в базу',
                    'Журнал запросов СПО', 'Каталог СПО блока']
        elif self.position == 4 and self.current_str == 0:
            request = "SELECT log.date, to_char(log.time, 'HH24:MM:SS'), spo.ksum, spo.comment, spo.is_official FROM spoquerylog AS log JOIN spo ON log.spo_id=spo.id WHERE log.owner_id=(SELECT id FROM ownersSPO WHERE products_name='" + self.pkey + "' AND block_name='" + self.bkey + "' AND sub_block_name='" + self.sbkey + "') ORDER BY log.id DESC LIMIT 1;"
            self.cur.execute(request)
            self.current_str = 0
            return list(" | ".join(str(item) for item in line)
                        for line in self.cur.fetchall())
        elif self.position == 4 and self.current_str == 1:
            request = "SELECT MAX(id) FROM spo;"
            self.cur.execute(request)
            self.current_str = 0
            return int(self.cur.fetchall()[0][0])
        elif self.position == 4 and self.current_str == 2:
            request = "SELECT log.date, to_char(log.time, 'HH24:MM:SS'), spo.ksum, spo.comment, spo.is_official FROM spoquerylog AS log JOIN spo ON log.spo_id=spo.id WHERE log.owner_id=(SELECT id FROM ownersSPO WHERE products_name='" + self.pkey + "' AND block_name='" + self.bkey + "' AND sub_block_name='" + self.sbkey + "') ORDER BY log.id DESC;"
            self.cur.execute(request)
            self.current_str = 0
            return list(" | ".join(str(item) for item in line)
                        for line in self.cur.fetchall())
        elif self.position == 4 and self.current_str == 3:
            request = "SELECT spo.date, spo.ksum, spo.md5, spo.comment, spo.is_official FROM spo WHERE spo.owner_id=(SELECT id FROM ownersSPO WHERE products_name='" + self.pkey + "' AND block_name='" + self.bkey + "' AND sub_block_name='" + self.sbkey + "') ORDER BY spo.id DESC;"
            self.cur.execute(request)
            self.current_str = 0
            return list(" | ".join(str(item) for item in line)
                        for line in self.cur.fetchall())

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

    # Get data from Products table (where="param='x'" need '' for string params)
    # rows = [Product(value) for value in select(cur, 'products')]
    printer = Printer(Products(select(cur, 'ownersSPO')), cur)

    while (k != 27):    # 'Esc'

        # Initialization
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Hide cursor
        curses.curs_set(0)

        # Centering calculations
        start_x = 5
        start_y = 5
        offset_y = 0

        if k == curses.KEY_DOWN:
            cursor_y = cursor_y + 2
            printer.move_current_str(1)
        elif k == curses.KEY_UP:
            cursor_y = cursor_y - 2
            printer.move_current_str(-1)
        elif k == curses.KEY_LEFT:
            cursor_y = 5
            printer.move_position(-1)
        elif k == curses.KEY_RIGHT:
            cursor_y = 5
            printer.move_position(1, current_str)

        # Cursor border
        # cursor_x = max(0, cursor_x)
        # cursor_x = min(width-1, cursor_x)
        #
        # cursor_y = max(0, cursor_y)
        # cursor_y = min(height-1, cursor_y)

        # Declaration of strings
        # title = "ТУТ БУДЕТ ЗАГОЛОВОК"[:width-1]
        # subtitle = "Written by Clay McLeod"[:width-1]
        # keystr = "Last key pressed: {}".format(k)[:width-1]
        # statusbarstr = "Press 'Esc' to exit | STATUS BAR | Pos: {}, {}".format(cursor_x, cursor_y)
        statusbarstr = (connection_status + ' as ' + user)

        # if k == 0:
        #     keystr = "No key press detected..."[:width-1]

        # Centering calculations
        # start_x_title = int((width // 2) - (len(title) // 2) - len(title) % 2)
        # start_x_subtitle = int((width // 2) - (len(subtitle) // 2) - len(subtitle) % 2)
        # start_x_keystr = int((width // 2) - (len(keystr) // 2) - len(keystr) % 2)
        # start_y = int((height // 2) - 2)

        # Rendering some text
        # whstr = "Width: {}, Height: {}".format(width, height)
        # stdscr.addstr(0, 0, whstr, curses.color_pair(1))

        # отрисовка текущей таблицы
        data = printer.get_data()
        # Если отрисовываем таблицу
        if type(data) is list:
            if len(data):
                for line in data:
                    stdscr.addstr(start_y + offset_y, start_x, '[ ]\t' + line)
                    offset_y += 2
            else:
                    stdscr.addstr(start_y + offset_y, start_x, '[ ]\t' + 'Нет данных')
                    offset_y += 2
        # Если заливаем новую прошивку в базу
        elif type(data) is int:
            # Просим пользователя ввести путь до файла прошивки
            stdscr.addstr(start_y + offset_y, start_x, 'Укажите имя файла СПО: ')
            # Формируем путь до файла СПО на FTP-сервере
            st = (printer.pkey + '/' + printer.bkey + '/' + printer.sbkey +
                    '/' + str(data+1))
            # Переводим путь в int-представление
            st = ''.join(map(str,list(map(lambda x: '/' if x=='/' else ord(x), st))))
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
                    stdscr.addstr(start_y + offset_y, start_x, '\t' + st + '/' + file_name + '\t' + hash)
                    # Проверяем налчие прошики с данной md5 в базе
                    request = "SELECT md5 FROM spo WHERE owner_id=(SELECT id FROM ownersSPO WHERE products_name='" + printer.pkey + "' AND block_name='" + printer.bkey + "' AND sub_block_name='" + printer.sbkey + "');"
                    cur.execute(request)
                    # Если прошивка с указанной md5 уже есть в базе - СТОП
                    if (hash,) in cur.fetchall():
                        stdscr.addstr(start_y + offset_y, start_x, '\nСПО С ДАННОЙ md5 УЖЕ ИМЕЕТСЯ В БАЗЕ!')
                    else:
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
                        stdscr.addstr(start_y + offset_y + 2, start_x, 'Укажите контрольную сумму СПО: ')
                        curses.echo()
                        ksum = stdscr.getstr().strip().decode("utf-8")
                        curses.noecho()
                        stdscr.addstr(start_y + offset_y + 4, start_x, 'Укажите комментарий: ')
                        curses.echo()
                        comment = stdscr.getstr().strip().decode("utf-8")
                        curses.noecho()
                        stdscr.addstr(start_y + offset_y + 6, start_x, 'Статус СПО (True или False): ')
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
                        stdscr.addstr(start_y + offset_y + 8, start_x, 'Спо добавлено в базу'.upper())
            # Если не смогли открыть файл с прошивкой
            except:
                stdscr.addstr(start_y + offset_y, start_x, '\nФАЙЛ НЕ НАЙДЕН!')
            offset_y += 2

        offset_y -= 2

        # Set cursor borders
        if cursor_y < 5:
            cursor_y = 5

        if cursor_y > start_y + offset_y:
            cursor_y = start_y + offset_y

        # Render status bar
        stdscr.attron(curses.color_pair(3))
        stdscr.addstr(height-1, 0, statusbarstr)
        stdscr.addstr(height-1, len(statusbarstr),
                        " " * (width - len(statusbarstr) - 1))
        stdscr.attroff(curses.color_pair(3))

        # Turning on attributes for title
        # stdscr.attron(curses.color_pair(2))
        # stdscr.attron(curses.A_BOLD)

        # Rendering title
        # stdscr.addstr(0, start_x_title, title)

        # Turning off attributes for title
        # stdscr.attroff(curses.color_pair(2))
        # stdscr.attroff(curses.A_BOLD)

        # Print rest of text
        # stdscr.addstr(start_y + 1, start_x_subtitle, subtitle)
        # stdscr.addstr(start_y + 3, (width // 2) - 2, '-' * 4)
        # stdscr.addstr(start_y + 5, start_x_keystr, keystr)

        # Move cursor to position (cursor_y, cursor_x)
        stdscr.move(cursor_y, cursor_x)

        # Draw current cursor position
        stdscr.addstr(cursor_y, cursor_x, '*')

        current_str = stdscr.instr(cursor_y, cursor_x + 2).strip().decode("utf-8")

        # Refresh the screen
        stdscr.refresh()

        # Wait for next input
        k = stdscr.getch()


def main():

    # Resize terminal in Windows
    if os.name == 'nt':
        os.system('mode con: cols=150 lines=50')

    dbname = input('Укажите БД: ')
    user = input('Логин: ')
    passwd = input('Пароль: ')

    # Try to connect to DataBase
    try:
        """Connect to PostgresQL server"""
        conn = psycopg2.connect(dbname=dbname, host='192.168.7.24',
                                user=user)
        connection_status = 'Connected to database ' + dbname
    except:
        print('DataBase connection error!')
        exit()

    # Start curses
    curses.wrapper(draw_menu, connection_status, user, conn)

    # End SQL sesion
    cur.close()
    conn.close()

    # Resize terminal in Windows
    if os.name == 'nt':
        os.system("mode con: cols=80 lines=24")

if __name__ == "__main__":

    main()
