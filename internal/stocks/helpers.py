import io
from typing import List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from prettytable import ALL, NONE, SINGLE_BORDER, PrettyTable


async def get_change_icon(change: float) -> str:
    if change > 0:
        icon = "🟩"
    elif change < 0:
        icon = "🟥"
    else:
        icon = "➖"

    return icon


async def pretty_table_defaults(headers=None) -> PrettyTable:

    template = PrettyTable(field_names=headers)
    template.set_style(SINGLE_BORDER)
    template.hrules = ALL
    template.vrules = NONE
    template.align = "r"
    return template


async def create_update_table(buff: io.BytesIO, df: pd.DataFrame):

    starting_cols = df.columns
    colors = ["red", "green", "lightgrey"]

    # get numeric cols to compare
    incept_change_values: pd.Series = df["$ Δ Inception"].astype("float16")
    weekly_change_values: pd.Series = df["$ Δ Weekly"].astype("float16")

    # create conditions
    incept_color_conds = await create_font_color_conditions(incept_change_values)
    weekly_color_conds = await create_font_color_conditions(weekly_change_values)

    # add cols to dataframe used be used for color formatting
    df["incept_color"] = np.select(incept_color_conds, colors, None)
    df["weekly_color"] = np.select(weekly_color_conds, colors, None)

    text_color = []
    # apply color formatting to the following cols: "$ Δ Inception", "$ Δ Weekly", "% Δ Weekly", "ROI Inception"
    for col in starting_cols:
        if col not in ("$ Δ Inception", "$ Δ Weekly", "% Δ Weekly", "ROI Inception"):
            text_color.append(["black"] * df.shape[0])
        elif col == "$ Δ Inception" or col == "ROI Inception":
            text_color.append(df["incept_color"].to_list())
        elif col == "$ Δ Weekly" or col == "% Δ Weekly":
            text_color.append(df["weekly_color"].to_list())

    # table color and formatting
    row_odd_color = "white"
    row_even_color = "#e4f8ff"
    fig_height = 60 + df.shape[0] * 20

    fig = go.Figure(
        data=[go.Table(
            header=dict(values=starting_cols,
                        line_color='white',
                        fill_color="darkslategrey",
                        align="center",
                        font_color="white",
                        ),
            cells=dict(values=df[starting_cols].values.T,
                       line_color='white',
                       fill_color=[[row_odd_color, row_even_color]
                                   * df.shape[0]],
                       align='right',
                       font=dict(color=text_color)
                       )
        )
        ])
    fig.update_layout(margin=dict(r=5, l=5, t=5, b=5), height=fig_height+5)
    fig.write_image(file=buff, format="png")


async def create_font_color_conditions(series: pd.Series) -> List[bool]:
    return [
        (series < 0),
        (series > 0),
        (series == 0),
    ]
