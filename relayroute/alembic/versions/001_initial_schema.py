"""Initial schema: cities, zones, restaurants, dropoff_points, partners, orders, task_events

Revision ID: 001_initial
Revises:
Create Date: 2026-03-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cities",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("api_key", sa.String(255), nullable=False),
        sa.Column("epsilon_km", sa.Float(), nullable=False),
        sa.Column("min_restaurants_per_zone", sa.Integer(), nullable=False),
        sa.Column("dropoff_spacing_km", sa.Float(), nullable=False),
        sa.Column("dropoff_capacity", sa.Integer(), nullable=False),
        sa.Column("zone_reasoning", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "zones",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("city_id", sa.String(64), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("boundaries", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("restaurant_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "restaurants",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("city_id", sa.String(64), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_id", sa.String(64), sa.ForeignKey("zones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("address", sa.String(512), nullable=False),
    )
    op.create_table(
        "dropoff_points",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("city_id", sa.String(64), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_id", sa.String(64), sa.ForeignKey("zones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("address", sa.String(512), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("current_load", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'active'")),
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("city_id", sa.String(64), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("restaurant_id", sa.String(64), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delivery_address", sa.String(512), nullable=False),
        sa.Column("delivery_lat", sa.Float(), nullable=False),
        sa.Column("delivery_lng", sa.Float(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("relay_chain", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("current_dropoff_id", sa.String(64), nullable=True),
        sa.Column("current_zone_id", sa.String(64), nullable=True),
        sa.Column("estimated_handoffs", sa.Integer(), nullable=False),
        sa.Column("remaining_handoffs", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "partners",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("city_id", sa.String(64), sa.ForeignKey("cities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_id", sa.String(64), sa.ForeignKey("zones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'available'")),
        sa.Column("current_order_id", sa.String(64), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "task_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.String(64), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("partner_id", sa.String(64), sa.ForeignKey("partners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event", sa.String(64), nullable=False),
        sa.Column("dropoff_id", sa.String(64), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("task_events")
    op.drop_table("partners")
    op.drop_table("orders")
    op.drop_table("dropoff_points")
    op.drop_table("restaurants")
    op.drop_table("zones")
    op.drop_table("cities")
