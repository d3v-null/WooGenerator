# Ncurses interface for triggering syncing using woogenerator.py and merger.py

import curses
import re

def cleanup(stdscr):
    curses.nocbreak() # enable normal terminal line buffering
    stdscr.keypad(0)  # escape sequences left as in the input stream
    curses.echo()     # each character input is echoed to the screen as it is entered
    curses.endwin()   # De-initialize the library

def render_centered(stdscr, text, margin=None, border=None):
    """ renders the given text in the center of the current window,
    returning a tuple (pos_row, pos_col, size_row, size_col)
    Optional margin and border width params can be specified as tuples
    (top, right, bottom, left). Default for both is (1,1,1,1)"""

    if not border:
        border = (1,1,1,1)
    assert len(border) == 4
    assert all( map(lambda x: type(x) == int, border) )

    if not margin:
        margin = (1,1,1,1)
    assert len(border) == 4
    assert all( map(lambda x: type(x) == int, border) )

    text = unicode(text)
    lines = text.split('\n')
    screen_rows, screen_cols  = stdscr.getmaxyx()
    overhead_row = sum(
        border[1],
        border[3],
        margin[1],
        margin[3]
    )

    overhead_col = sum(
        border[0],
        border[2],
        margin[0],
        margin[2]
    )

    assert screen_rows > overhead_row
    assert screen_cols > overhead_col
    avail_cols = screen_cols - overhead_col
    avail_rows = screen_rows - overhead_row
    text_rows = 0
    text_cols = 0
    rendered_lines = []
    for line in lines:
        if len(line) >= screen_cols:
            # find best place to split line
            line_parial = line[:avail_cols]
            last_space_match = re.search(r"")

        text_cols = max(text_cols, len(line))


def main(stdscr):
    if curses.has_colors():
        bg = curses.COLOR_BLACK
        curses.init_pair(1, curses.COLOR_BLUE, bg)
        curses.init_pair(2, curses.COLOR_CYAN, bg)

    curses.nl()
    curses.noecho()
    stdscr.timeout(0)

    render_centered(
        stdscr,
        "This is some multiline text.\n" +
        "I hope it gets rendered properly\n" +
        "but I guess if not that's cool too.\n" +
        "\n" +
        "How about blank lines?\n",
        "How about really really really really really really really really really really long lines?\n",
        (2,2,2,2)
    )



if __name__ == '__main__':
    try:
        stdscr = curses.initscr()
        curses.wrapper(main, stdscr)
    except Exception as e:
        if(e):
            pass


