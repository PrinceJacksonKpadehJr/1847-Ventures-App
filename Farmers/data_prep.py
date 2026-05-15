"""
Data Preparation Utilities

Handles column and row operations, history tracking, and live preview generation.
"""
from datetime import datetime
from typing import Any, Dict, List
import copy


class DataPrepHistory:
    """Manages undo/redo history for data prep operations."""
    
    def __init__(self, history: List[Dict[str, Any]]):
        self.history = history or []
        self.current_index = len(history) - 1
    
    def add_operation(self, operation: str, data: Dict[str, Any]) -> None:
        """Add a new operation to history, discarding any redo states."""
        # Discard redo history
        self.history = self.history[:self.current_index + 1]
        
        self.history.append({
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        })
        self.current_index = len(self.history) - 1
    
    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return self.current_index > 0
    
    def can_redo(self) -> bool:
        """Check if redo is possible."""
        return self.current_index < len(self.history) - 1
    
    def undo(self) -> Dict[str, Any] | None:
        """Move back in history."""
        if self.can_undo():
            self.current_index -= 1
            return self.get_current_state()
        return None
    
    def redo(self) -> Dict[str, Any] | None:
        """Move forward in history."""
        if self.can_redo():
            self.current_index += 1
            return self.get_current_state()
        return None
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get the current state from history."""
        if self.current_index < 0 or self.current_index >= len(self.history):
            return {}
        return self.history[self.current_index].get("data", {})
    
    def serialize(self) -> List[Dict[str, Any]]:
        """Serialize history to list."""
        return self.history


class ColumnOperations:
    """Handles column-level operations."""
    
    @staticmethod
    def rename_column(metadata: Dict, original_name: str, new_name: str) -> Dict:
        """Rename a column."""
        if original_name not in metadata:
            metadata[original_name] = {}
        
        metadata[original_name]["rename"] = new_name
        metadata[original_name]["renamed_from"] = original_name
        return metadata
    
    @staticmethod
    def retype_column(metadata: Dict, column_name: str, new_type: str) -> Dict:
        """Change column data type."""
        if column_name not in metadata:
            metadata[column_name] = {}
        
        metadata[column_name]["type_override"] = new_type
        return metadata
    
    @staticmethod
    def hide_column(metadata: Dict, column_name: str, hidden: bool = True) -> Dict:
        """Hide or show a column."""
        if column_name not in metadata:
            metadata[column_name] = {}
        
        metadata[column_name]["hidden"] = hidden
        return metadata
    
    @staticmethod
    def tag_column_semantic(metadata: Dict, column_name: str, semantic_tag: str) -> Dict:
        """Mark column with semantic tag (dimension, measure, identifier, date, geographic)."""
        valid_tags = {"dimension", "measure", "identifier", "date", "geographic"}
        if semantic_tag not in valid_tags:
            raise ValueError(f"Invalid semantic tag: {semantic_tag}")
        
        if column_name not in metadata:
            metadata[column_name] = {}
        
        metadata[column_name]["semantic_tag"] = semantic_tag
        return metadata
    
    @staticmethod
    def remove_column(metadata: Dict, column_name: str) -> Dict:
        """Mark column for removal."""
        if column_name not in metadata:
            metadata[column_name] = {}
        
        metadata[column_name]["removed"] = True
        return metadata
    
    @staticmethod
    def merge_columns(metadata: Dict, source_columns: List[str], target_name: str, separator: str = "_") -> Dict:
        """Mark columns for merging."""
        for col in source_columns:
            if col not in metadata:
                metadata[col] = {}
            metadata[col]["merged"] = True
        
        # Store merge instruction on target
        metadata[target_name] = {
            "merge_target": True,
            "merge_sources": source_columns,
            "merge_separator": separator,
        }
        return metadata
    
    @staticmethod
    def split_column(metadata: Dict, column_name: str, split_char: str, target_names: List[str]) -> Dict:
        """Mark column for splitting."""
        if column_name not in metadata:
            metadata[column_name] = {}
        
        metadata[column_name]["split"] = True
        metadata[column_name]["split_char"] = split_char
        metadata[column_name]["split_targets"] = target_names
        return metadata


class RowOperations:
    """Handles row-level operations."""
    
    @staticmethod
    def remove_rows(row_ops: Dict, row_numbers: List[int]) -> Dict:
        """Mark rows for removal."""
        if "removed_rows" not in row_ops:
            row_ops["removed_rows"] = []
        
        row_ops["removed_rows"].extend(row_numbers)
        row_ops["removed_rows"] = list(set(row_ops["removed_rows"]))  # Deduplicate
        return row_ops
    
    @staticmethod
    def apply_filter(row_ops: Dict, column_name: str, operator: str, value: Any) -> Dict:
        """Apply a filter to rows."""
        if "filters" not in row_ops:
            row_ops["filters"] = []
        
        # Valid operators: equals, not_equals, gt, gte, lt, lte, contains, not_contains, is_null, is_not_null
        valid_ops = {"equals", "not_equals", "gt", "gte", "lt", "lte", "contains", "not_contains", "is_null", "is_not_null"}
        if operator not in valid_ops:
            raise ValueError(f"Invalid operator: {operator}")
        
        row_ops["filters"].append({
            "column": column_name,
            "operator": operator,
            "value": value,
        })
        return row_ops
    
    @staticmethod
    def exclude_nulls(row_ops: Dict, columns: List[str]) -> Dict:
        """Exclude rows with null values in specific columns."""
        if "exclude_nulls" not in row_ops:
            row_ops["exclude_nulls"] = []
        
        row_ops["exclude_nulls"].extend(columns)
        row_ops["exclude_nulls"] = list(set(row_ops["exclude_nulls"]))  # Deduplicate
        return row_ops
    
    @staticmethod
    def remove_duplicates(row_ops: Dict, columns: List[str] | None = None) -> Dict:
        """Mark to remove duplicate rows."""
        row_ops["remove_duplicates"] = True
        if columns:
            row_ops["duplicate_key_columns"] = columns
        return row_ops


class LivePreviewGenerator:
    """Generates live preview of data with applied operations."""
    
    @staticmethod
    def apply_column_operations(schema: List[Dict], metadata: Dict) -> List[Dict]:
        """Apply column metadata to schema."""
        result_schema = []
        
        for col_info in schema:
            col_name = col_info.get("column", "")
            
            # Skip removed columns
            if col_name in metadata and metadata[col_name].get("removed"):
                continue
            
            # Skip hidden columns
            if col_name in metadata and metadata[col_name].get("hidden"):
                continue
            
            # Copy column info
            new_col_info = copy.deepcopy(col_info)
            
            # Apply rename
            if col_name in metadata and "rename" in metadata[col_name]:
                new_col_info["column"] = metadata[col_name]["rename"]
                new_col_info["original_name"] = col_name
            
            # Apply type override
            if col_name in metadata and "type_override" in metadata[col_name]:
                new_col_info["type"] = metadata[col_name]["type_override"]
            
            # Apply semantic tag
            if col_name in metadata and "semantic_tag" in metadata[col_name]:
                new_col_info["semantic_tag"] = metadata[col_name]["semantic_tag"]
            
            result_schema.append(new_col_info)
        
        return result_schema
    
    @staticmethod
    def apply_row_operations(rows: List[Dict], row_ops: Dict) -> List[Dict]:
        """Apply row operations to rows."""
        if not row_ops:
            return rows
        
        result_rows = []
        
        for row_num, row in enumerate(rows, 1):
            # Skip removed rows
            if row_num in row_ops.get("removed_rows", []):
                continue
            
            # Check filters
            if "filters" in row_ops:
                passes_filters = True
                for filter_spec in row_ops["filters"]:
                    col = filter_spec["column"]
                    op = filter_spec["operator"]
                    val = filter_spec["value"]
                    
                    row_val = row.get(col)
                    
                    if not LivePreviewGenerator._check_filter(row_val, op, val):
                        passes_filters = False
                        break
                
                if not passes_filters:
                    continue
            
            # Check null exclusions
            if "exclude_nulls" in row_ops:
                has_nulls = False
                for col in row_ops["exclude_nulls"]:
                    if row.get(col) is None or str(row.get(col, "")).strip() == "":
                        has_nulls = True
                        break
                
                if has_nulls:
                    continue
            
            result_rows.append(row)
        
        # Remove duplicates if requested
        if row_ops.get("remove_duplicates"):
            if "duplicate_key_columns" in row_ops:
                # Dedup based on specific columns
                seen = set()
                deduped_rows = []
                for row in result_rows:
                    key = tuple(row.get(col) for col in row_ops["duplicate_key_columns"])
                    if key not in seen:
                        seen.add(key)
                        deduped_rows.append(row)
                result_rows = deduped_rows
            else:
                # Dedup based on entire row
                seen = set()
                deduped_rows = []
                for row in result_rows:
                    row_json = str(row)
                    if row_json not in seen:
                        seen.add(row_json)
                        deduped_rows.append(row)
                result_rows = deduped_rows
        
        return result_rows
    
    @staticmethod
    def _check_filter(value: Any, operator: str, filter_value: Any) -> bool:
        """Check if a value passes a filter condition."""
        if operator == "equals":
            return str(value).lower() == str(filter_value).lower()
        elif operator == "not_equals":
            return str(value).lower() != str(filter_value).lower()
        elif operator == "contains":
            return str(filter_value).lower() in str(value).lower()
        elif operator == "not_contains":
            return str(filter_value).lower() not in str(value).lower()
        elif operator == "is_null":
            return value is None or str(value).strip() == ""
        elif operator == "is_not_null":
            return value is not None and str(value).strip() != ""
        elif operator in {"gt", "gte", "lt", "lte"}:
            try:
                val_num = float(value)
                filter_num = float(filter_value)
                if operator == "gt":
                    return val_num > filter_num
                elif operator == "gte":
                    return val_num >= filter_num
                elif operator == "lt":
                    return val_num < filter_num
                elif operator == "lte":
                    return val_num <= filter_num
            except (ValueError, TypeError):
                return False
        return True
    
    @staticmethod
    def generate_preview(schema: List[Dict], rows: List[Dict], column_metadata: Dict, row_operations: Dict) -> Dict:
        """Generate full preview with applied operations."""
        prepared_schema = LivePreviewGenerator.apply_column_operations(schema, column_metadata)
        prepared_rows = LivePreviewGenerator.apply_row_operations(rows, row_operations)
        
        # Build column map for row transformation
        original_to_new = {}
        for col_info in schema:
            col_name = col_info.get("column", "")
            if col_name in column_metadata and "rename" in column_metadata[col_name]:
                original_to_new[col_name] = column_metadata[col_name]["rename"]
        
        # Transform rows to use new column names
        transformed_rows = []
        for row in prepared_rows:
            new_row = {}
            for original_col, value in row.items():
                new_col = original_to_new.get(original_col, original_col)
                # Skip if column was removed or hidden
                skip = False
                for col_info in prepared_schema:
                    if col_info.get("column") == new_col:
                        new_row[new_col] = value
                        break
            transformed_rows.append(new_row)
        
        return {
            "schema": prepared_schema,
            "rows": transformed_rows,
            "row_count": len(transformed_rows),
            "column_count": len(prepared_schema),
            "original_row_count": len(rows),
            "original_column_count": len(schema),
            "rows_removed": len(rows) - len(transformed_rows),
            "columns_removed": len(schema) - len(prepared_schema),
        }
