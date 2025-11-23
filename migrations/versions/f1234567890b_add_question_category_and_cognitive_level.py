# Add question_category and cognitive_level columns to user_generated_questions table

"""add question category and cognitive level columns"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f1234567890b"
down_revision = "dac520301aa6"
branch_labels = None
depends_on = None


def upgrade():
    # Add question_category column
    op.add_column(
        "user_generated_questions",
        sa.Column(
            "question_category",
            sa.String(50),
            nullable=True,
            comment="Primary question category: standard, critical, linking",
        ),
    )

    # Add cognitive_level column
    op.add_column(
        "user_generated_questions",
        sa.Column(
            "cognitive_level",
            sa.String(50),
            nullable=True,
            comment="Cognitive level: remember, understand, apply, analyze, evaluate, create",
        ),
    )


def downgrade():
    # Remove the columns
    op.drop_column("user_generated_questions", "cognitive_level")
    op.drop_column("user_generated_questions", "question_category")
