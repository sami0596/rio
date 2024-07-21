from __future__ import annotations

from typing import *  # type: ignore

import rio

from .fundamental_component import FundamentalComponent

__all__ = [
    "NodeOutput",
]


@final
class NodeOutput(FundamentalComponent):
    """
    ## Metadata

    public: False
    """

    name: str
    color: rio.Color

    def __init__(
        self,
        name: str,
        color: rio.Color,
        # Note that the key is required. Connections use the port's key to
        # identify their start and end points.
        key: str,
        *,
        margin: float | None = None,
        margin_x: float | None = None,
        margin_y: float | None = None,
        margin_left: float | None = None,
        margin_top: float | None = None,
        margin_right: float | None = None,
        margin_bottom: float | None = None,
        min_width: float | None = None,
        min_height: float | None = None,
        max_width: float | None = None,
        max_height: float | None = None,
        width: float | Literal["grow", "natural"] | None = None,
        height: float | Literal["grow", "natural"] | None = None,
        grow_x: bool = False,
        grow_y: bool = False,
        # SCROLLING-REWORK scroll_x: Literal["never", "auto", "always"] = "never",
        # SCROLLING-REWORK scroll_y: Literal["never", "auto", "always"] = "never",
    ):
        # Make sure the building component is a Node
        # TODO

        super().__init__(
            key=key,
            margin=margin,
            margin_x=margin_x,
            margin_y=margin_y,
            margin_left=margin_left,
            margin_top=margin_top,
            margin_right=margin_right,
            margin_bottom=margin_bottom,
            min_width=min_width,
            min_height=min_height,
            max_width=max_width,
            max_height=max_height,
            width=width,
            height=height,
            grow_x=grow_x,
            grow_y=grow_y,
            # SCROLLING-REWORK scroll_x=scroll_x,
            # SCROLLING-REWORK scroll_y=scroll_y,
        )

        self.name = name
        self.color = color


NodeOutput._unique_id = "NodeOutput-builtin"
