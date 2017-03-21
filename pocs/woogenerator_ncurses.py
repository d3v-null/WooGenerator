# Ncurses interface for triggering syncing using woogenerator.py and merger.py

import curses
import textwrap
import logging
from collections import namedtuple

Box = namedtuple('Box', ['top', 'right', 'bottom', 'left'])


def cleanup(stdscr):
    curses.nocbreak()  # enable normal terminal line buffering
    stdscr.keypad(0)  # escape sequences left as in the input stream
    curses.echo()     # each character input is echoed to the screen as it is entered
    curses.endwin()   # De-initialize the library


def render_centered(stdscr, text, margin=None, border=None, max_cols=70):
    """ renders the given text in the center of the current window,
    returning a tuple (pos_row, pos_col, size_row, size_col)
    Optional margin and border width params can be specified as tuples
    (top, right, bottom, left). Default for both is (1,1,1,1)"""

    if not border:
        border = Box(1, 1, 1, 1)

    if not margin:
        margin = Box(1, 1, 1, 1)

    screen_rows, screen_cols = stdscr.getmaxyx()

    logging.info("screen cols %2d, rows %2d", screen_cols, screen_rows)

    overhead_col = sum([
        border.right,
        border.left,
        margin.right,
        margin.left
    ])

    overhead_row = sum([
        border.top,
        border.bottom,
        margin.top,
        margin.bottom
    ])

    logging.info("overhead col %2d, row %2d", overhead_col, overhead_row)

    assert screen_rows > overhead_row
    assert screen_cols > overhead_col
    avail_cols = screen_cols - overhead_col
    avail_rows = screen_rows - overhead_row

    text_cols = 0
    wrap_col = min(max_cols, avail_cols)
    wrapped_lines = []

    for line in unicode(text).splitlines():
        for wrapped_line in textwrap.wrap(line, wrap_col):
            if len(wrapped_lines) >= avail_rows:
                break
            wrapped_lines.append(wrapped_line)
            text_cols = max(text_cols, len(wrapped_line))
    text_rows = len(wrapped_lines)

    offset_col = (avail_cols - text_cols) / 2 + border[3] + margin[3]
    offset_row = (avail_rows - text_rows) / 2 + border[0] + margin[0]

    for count, line in enumerate(wrapped_lines):
        logging.info("writing to col %2d, row %2d; %s", offset_col, offset_row
                     + count, line)
        stdscr.addstr(offset_row + count, offset_col, line)

    return (offset_col, offset_row, text_cols, text_rows)


def main(stdscr):
    if curses.has_colors():
        bg = curses.COLOR_BLACK
        curses.init_pair(1, curses.COLOR_BLUE, bg)
        curses.init_pair(2, curses.COLOR_CYAN, bg)

    # curses.nl()
    # curses.noecho()
    # stdscr.timeout(0)

    render_centered(
        stdscr,
        "This is some multiline text.\n" +
        "I hope it gets rendered properly\n" +
        "but I guess if not that's cool too.\n" +
        "\n" +
        "How about blank lines?\n" +
        "How about really really really really really really really really really really long lines?\n",
        Box(2, 2, 2, 2)
    )
    while 1:
        stdscr.refresh()


if __name__ == '__main__':
    logging.basicConfig(filename="woogenerator.log", level=logging.DEBUG)

    curses.wrapper(main)
    # try:
    # except Exception as exc:
    #     raise exc
