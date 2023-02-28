

async def get_change_icon(change: float) -> str:
    if change > 0:
        icon = "🟩"
    elif change < 0:
        icon = "🟥"
    else:
        icon = "➖"

    return icon
