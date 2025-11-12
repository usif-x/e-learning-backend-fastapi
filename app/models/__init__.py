"""
Models package initialization
Import all models and setup relationships
"""

from .admin import Admin
from .categories import Category
from .courses import Course

# Import and setup relationships
from .relations import setup_relationships

# Import all models first
from .user import User

# Setup all relationships after models are imported
setup_relationships()

# Make models available at package level
__all__ = ["User", "Category", "Course", "Admin"]
