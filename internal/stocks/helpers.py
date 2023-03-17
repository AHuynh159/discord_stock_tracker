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