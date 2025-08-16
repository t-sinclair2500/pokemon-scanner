"""Resolve package for Pokemon card identification."""

from .poketcg import get_card, search_by_number_name

__all__ = ["get_card", "search_by_number_name"]
