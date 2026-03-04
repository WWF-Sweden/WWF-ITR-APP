"""
Database module for WWF ITR Tool.
Provides local SQLite storage for portfolio and provider data.
"""
from db.database import (
    init_db,
    save_dataset,
    load_dataset,
    list_datasets,
    delete_dataset,
    update_table,
    get_db_path,
)
