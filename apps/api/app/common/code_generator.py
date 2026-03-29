from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.code_sequence import CodeSequence


async def generate_code(session: AsyncSession, prefix: str) -> str:
    """
    Generate a human-readable code like PAY-2026-03-000012.

    Uses the code_sequences table to track the last assigned number
    per prefix-month combination, ensuring uniqueness.
    """
    now = datetime.now(timezone.utc)
    year_month = now.strftime("%Y-%m")

    # Find or create the sequence for this prefix + month
    # with_for_update() locks the row so concurrent requests wait in line
    result = await session.execute(
        select(CodeSequence)
        .where(
            CodeSequence.prefix == prefix,
            CodeSequence.year_month == year_month,
        )
        .with_for_update()
    )
    sequence = result.scalar_one_or_none()

    if sequence is None:
        # First code for this prefix in this month
        sequence = CodeSequence(
            prefix=prefix, year_month=year_month, last_sequence=1
        )
        session.add(sequence)
    else:
        # Increment the sequence
        sequence.last_sequence += 1

    # Format: PAY-2026-03-000012
    code = f"{prefix}-{year_month}-{sequence.last_sequence:06d}"
    return code
