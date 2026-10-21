"""
Shared Plotly figure builders. Pages pass in data and labels; layout choices
live here so every page draws charts the same way.

These builders reproduce the pre-refactor figures exactly (same traces, same
layout). A shared visual theme and recession shading come in a later change.
"""

import plotly.graph_objects as go

REFERENCE_LINE = {"line_dash": "dash", "line_color": "gray"}


def _layout(fig: go.Figure, **kwargs) -> go.Figure:
    """Apply layout settings, skipping any left as None."""
    fig.update_layout(**{k: v for k, v in kwargs.items() if v is not None})
    return fig


def line_chart(
    x,
    y,
    name: str,
    *,
    height: int,
    yaxis_title: str,
    hline: float | None = None,
    hline_annotation: str | None = None,
    title: str | None = None,
    margin_top: int = 20,
) -> go.Figure:
    """Single time-series line, with an optional dashed reference line."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
    if hline is not None:
        extra = {"annotation_text": hline_annotation} if hline_annotation else {}
        fig.add_hline(y=hline, **REFERENCE_LINE, **extra)
    return _layout(
        fig,
        height=height,
        yaxis_title=yaxis_title,
        title=title,
        margin={"t": margin_top},
    )


def multi_line_chart(
    traces: list[dict],
    *,
    height: int,
    yaxis_title: str,
    xaxis_title: str | None = None,
    xaxis_type: str | None = None,
    margin_top: int = 20,
) -> go.Figure:
    """
    Several lines on one axis. Each trace is a dict with x, y, name, and
    optionally mode (default "lines") and dash.
    """
    fig = go.Figure()
    for t in traces:
        extra = {"line": {"dash": t["dash"]}} if t.get("dash") else {}
        fig.add_trace(
            go.Scatter(
                x=t["x"], y=t["y"], mode=t.get("mode", "lines"), name=t["name"], **extra
            )
        )
    return _layout(
        fig,
        height=height,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        xaxis_type=xaxis_type,
        margin={"t": margin_top},
    )


def dual_axis_chart(
    x,
    y_left,
    name_left: str,
    title_left: str,
    y_right,
    name_right: str,
    title_right: str,
    *,
    height: int,
    hline_left: float | None = None,
) -> go.Figure:
    """Two series on independent left/right y-axes, legend across the top."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y_left, name=name_left, yaxis="y1"))
    fig.add_trace(go.Scatter(x=x, y=y_right, name=name_right, yaxis="y2"))
    if hline_left is not None:
        fig.add_hline(y=hline_left, **REFERENCE_LINE, yref="y1")
    return _layout(
        fig,
        height=height,
        margin={"t": 20},
        yaxis={"title": title_left},
        yaxis2={"title": title_right, "overlaying": "y", "side": "right"},
        legend={"orientation": "h", "y": 1.1},
    )


def heatmap_chart(
    z,
    x,
    y,
    *,
    zmid: float,
    colorbar_title: str,
    hovertemplate: str,
    height: int,
) -> go.Figure:
    """Diverging red-to-green heatmap centred on `zmid`."""
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            colorscale="RdYlGn",
            zmid=zmid,
            colorbar={"title": colorbar_title},
            hovertemplate=hovertemplate,
        )
    )
    return _layout(fig, height=height, margin={"t": 20})


def bar_chart(x, y, *, height: int, yaxis_title: str) -> go.Figure:
    """Simple vertical bar chart."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=y))
    return _layout(fig, height=height, yaxis_title=yaxis_title, margin={"t": 20})
