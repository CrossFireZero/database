# Interface
import curses
# FTP
import ftplib
# PostgresQL
import psycopg2


class Products():
    """Хранит данные об изделиях, блока и подблоках"""

    def __init__(self, params):
        self.dct = {}
        for tpl in params:
            if tpl[3] not in self.dct.keys():
                self.dct[tpl[3]] = {}
            if tpl[2] not in self.dct[tpl[3]].keys():
                self.dct[tpl[3]][tpl[2]] = []
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

    def __init__(self, prod):
        self.data = prod
        self.pkey = ''
        self.bkey = ''
        self.position = 0
        self.current_str = 0


    def move_position(self, step):
        """Меняет текущую позицию"""

        self.position += step
        if self.position < 0:
            self.position = 0
        elif self.position > 2:
            self.position = 2

        if self.position == 1:
            self.pkey = self.data.get_products()[self.current_str]
        elif self.position == 2:
            self.bkey = self.data.get_blocks(self.pkey)[self.current_str]
        self.current_str = 0
    def move_current_str(self, step):
        self.current_str += step

    def get_data(self):

        if self.position == 0:
            return self.data.get_products()
        elif self.position == 1:
            return self.data.get_blocks(self.pkey)
        elif self.position == 2:
            return self.data.get_sblocks(self.pkey, self.bkey)


def select(cur, from_, select='*', where=''):
    """Запрос данных из таблицы"""

    # Making the request
    # Образец запроса для получения списка таблиц
    """SELECT table_name FROM information_schema.tables
           WHERE table_schema = 'public'"""
    if len(where) == 0:
        request = "SELECT " + select + " FROM " + from_ +";"
    else:
        request = ("SELECT " + select + " FROM " + from_ + " WHERE "
                    + where +";")
    # Sending request
    cur.execute(request)
    # Return request result
    return cur.fetchall()

def draw_menu(stdscr, connection_status, user, cur):
    """Отрисовка"""

    # Current key
    k = 0

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
    printer = Printer(Products(select(cur, 'ownersSPO')))

    # Таблица с индексом 0 добавляется в хранилище экземпляра класса Printer
    # printer.tables.append(rows)
    # printer.current_table = 0
    # Loop where k is the last character pressed
    # while (k != ord('q')):
    while (k != 27):        # 'Esc'

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
            printer.move_position(-1)
        elif k == curses.KEY_RIGHT:
            printer.move_position(1)
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
        for str in printer.get_data():
            stdscr.addstr(start_y + offset_y, start_x, '[ ]\t' + str)
            offset_y += 2
        # for line in printer.tables[printer.current_table]:
        #     stdscr.addstr(start_y + offset_y, start_x, '[ ]\t' + line.get_str())
        #     offset_y += 2
        # for product in products:
        #     stdscr.addstr(start_y + offset_y, start_x, '[ ]\t' +
        #                     product.get_str())
        #     offset_y += 2
        offset_y -= 2
        # stdscr.addstr(0, 0, str(offset_y))
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

        # Refresh the screen
        stdscr.refresh()

        # Wait for next input
        k = stdscr.getch()


def main():

    dbname = input('Укажите БД: ')
    user = input('Логин: ')
    passwd = input('Пароль: ')
    # Try to connect to DataBase
    try:
        """Connect to PostgresQL server"""
        conn = psycopg2.connect(dbname=dbname, host='192.168.7.24',
                                user=user)
        cur = conn.cursor()
        connection_status = 'Connected to database ' + dbname
    except:
        print('DataBase connection error!')
        exit()

    # Start curses
    curses.wrapper(draw_menu, connection_status, user, cur)

    # End SQL sesion
    cur.close()
    conn.close()

if __name__ == "__main__":

    main()
