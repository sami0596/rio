from __future__ import annotations

from typing import *  # type: ignore

from . import class_container

__all__ = [
    "Spacer",
]


@final
class Spacer(class_container.ClassContainer):
    """
    An invisible component which grows by default.

    Spacers are invisible components which add empty space between other
    components. While similar effects can often be achieved using margins and
    alignment, code utilizing spacers can sometimes be easier to read.

    Note that unlike most components in Rio, `Spacer` does not have a `natural`
    size. Instead it defaults to a width and height of `grow`, as that is how
    they're most frequently used.


    ## Examples

    This example will display two texts in a Row, with one of them being pushed
    to the very left and the other to the very right:

    ```python
    rio.Row(
        rio.Text("Hello"),
        rio.Spacer(),
        rio.Text("World"),
    )
    ```
    """

    def __init__(
        self,
        *,
        min_width: float | None = None,
        min_height: float | None = None,
        max_width: float | None = None,
        max_height: float | None = None,
        width: float | Literal["grow", "natural"] | None = None,
        height: float | Literal["grow", "natural"] | None = None,
        grow_x: bool = True,
        grow_y: bool = True,
        key: str | int | None = None,
    ):
        """
        ## Parameters
            width: How much space the spacer should take up horizontally.
            height: How much space the spacer should take up vertically.
        """

        super().__init__(
            None,
            ["rio-spacer"],
            key=key,
            min_width=min_width,
            min_height=min_height,
            max_width=max_width,
            max_height=max_height,
            width=width,
            height=height,
            grow_x=grow_x,
            grow_y=grow_y,
        )

    def _get_debug_details(self) -> dict[str, Any]:
        result = super()._get_debug_details()

        # Don't inherit the content from `rio.ClassContainer`.
        del result["content"]

        return result


# Make sure the component is recognized as `ClassContainer`, rather than a new
# component.
Spacer._unique_id = class_container.ClassContainer._unique_id
