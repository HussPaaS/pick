
import curses
import textwrap
from collections import namedtuple
from dataclasses import dataclass, field
from typing import Any, Container, Generic, Iterable, List, Optional, Sequence, Tuple, TypeVar, Union

__all__ = ["Picker", "pick", "Option"]


@dataclass
class Option:
    label: str
    value: Any = None
    description: Optional[str] = None
    enabled: bool = True


KEYS_ENTER = (curses.KEY_ENTER, ord("\n"), ord("\r"))
KEYS_UP = (curses.KEY_UP, ord("k"))
KEYS_DOWN = (curses.KEY_DOWN, ord("j"))
KEYS_SELECT = (curses.KEY_RIGHT, ord(" "))

SYMBOL_CIRCLE_FILLED = "(x)"
SYMBOL_CIRCLE_EMPTY = "( )"

OPTION_T = TypeVar("OPTION_T", str, Option)
PICK_RETURN_T = Tuple[OPTION_T, int]

Position = namedtuple('Position', ['y', 'x'])

@dataclass
class Picker(Generic[OPTION_T]):
    options: Sequence[OPTION_T]
    title: Optional[str] = None
    indicator: str = "*"
    default_index: int = 0
    multiselect: bool = False
    min_selection_count: int = 0
    selected_indexes: List[int] = field(init=False, default_factory=list)
    index: int = field(init=False, default=0)
    screen: Optional["curses._CursesWindow"] = None
    position: Position = Position(0, 0)
    clear_screen: bool = True
    quit_keys: Optional[Union[Container[int], Iterable[int]]] = None

    def __post_init__(self) -> None:
        if len(self.options) == 0:
            raise ValueError("options should not be an empty list")

        if self.default_index >= len(self.options):
            raise ValueError("default_index should be less than the length of options")

        if self.multiselect and self.min_selection_count > len(self.options):
            raise ValueError(
                "min_selection_count is bigger than the available options, you will not be able to make any selection"
            )

        if all(isinstance(option, Option) and not option.enabled for option in self.options):
            raise ValueError(
                "all given options are disabled, you must at least have one enabled option."
            )

        self.index = self.default_index
        option = self.options[self.index]
        if isinstance(option, Option) and not option.enabled:
            self.move_down()

    def move_up(self) -> None:
        while True:
            self.index -= 1
            if self.index < 0:
                self.index = len(self.options) - 1
            option = self.options[self.index]
            if not isinstance(option, Option) or option.enabled:
                break

    def move_down(self) -> None:
        while True:
            self.index += 1
            if self.index >= len(self.options):
                self.index = 0
            option = self.options[self.index]
            if not isinstance(option, Option) or option.enabled:
                break

    def mark_index(self) -> None:
        if self.multiselect:
            if self.index in self.selected_indexes:
                self.selected_indexes.remove(self.index)
            else:
                self.selected_indexes.append(self.index)

    def get_selected(self) -> Union[List[PICK_RETURN_T], PICK_RETURN_T]:
        """return the current selected option as a tuple: (option, index)
        or as a list of tuples (in case multiselect==True)
        """
        if self.multiselect:
            return_tuples = []
            for selected in self.selected_indexes:
                return_tuples.append((self.options[selected], selected))
            return return_tuples
        else:
            return self.options[self.index], self.index

    def get_title_lines(self, *, max_width: int = 80) -> List[str]:
        if self.title:
            return textwrap.fill(self.title, max_width - 2, drop_whitespace=False).split("\n") + [""]
        return []

    def get_option_lines(self) -> List[str]:
        lines: List[str] = []
        for index, option in enumerate(self.options):
            if index == self.index:
                prefix = self.indicator
            else:
                prefix = len(self.indicator) * " "

            if self.multiselect:
                symbol = (
                    SYMBOL_CIRCLE_FILLED
                    if index in self.selected_indexes
                    else SYMBOL_CIRCLE_EMPTY
                )
                prefix = f"{prefix} {symbol}"

            option_as_str = option.label if isinstance(option, Option) else option
            lines.append(f"{prefix} {option_as_str}")

        return lines

    def get_lines(self, *, max_width: int = 80) -> Tuple[List[str], int]:
        title_lines = self.get_title_lines(max_width=max_width)
        option_lines = self.get_option_lines()
        lines = title_lines + option_lines
        current_line = self.index + len(title_lines) + 1
        return lines, current_line

    def draw(self, screen: "curses._CursesWindow") -> None:
        """draw the curses ui on the screen, handle scroll if needed"""
        if self.clear_screen:
            screen.clear()

        y, x = self.position  # start point

        max_y, max_x = screen.getmaxyx()
        max_rows = max_y - y  # the max rows we can draw

        lines, current_line = self.get_lines(max_width=max_x)

        # calculate how many lines we should scroll, relative to the top
        scroll_top = 0
        if current_line > max_rows:
            scroll_top = current_line - max_rows

        lines_to_draw = lines[scroll_top : scroll_top + max_rows]
