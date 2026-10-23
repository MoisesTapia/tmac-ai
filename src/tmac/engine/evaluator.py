import logging
import re
from typing import Any, Dict, List

from tmac.models.rule import CheckCondition

logger = logging.getLogger(__name__)


class Evaluator:
    """Evaluates rule conditions against resource attributes."""

    def evaluate(self, condition: CheckCondition, attributes: Dict[str, Any]) -> bool:
        """
        Evaluate a single check condition against the resource attributes.
        Returns True if the resource MATCHES the condition (meaning a finding),
        or False if it's secure or doesn't match.
        """
        val = self._get_attribute_value(condition.attribute, attributes)

        logger.debug(
            "Evaluating condition: attribute=%s, condition=%s, expected=%s, actual=%s",
            condition.attribute,
            condition.condition,
            condition.values,
            val,
        )

        # If the resolved value is a list of dicts (e.g. multiple ingress blocks),
        # evaluate against every element and return True if any element matches (any-semantics).
        # Also apply any-semantics to lists of scalars collected from multiple blocks
        # (e.g. ingress.from_port → [443, 22]).  Native scalar lists (e.g. cidr_blocks)
        # are handled by _evaluate_condition directly.
        if isinstance(val, list) and val and all(isinstance(v, dict) for v in val):
            # List of block dicts — evaluate each block
            matched = any(
                self._evaluate_condition(condition.condition, condition.values, item)
                for item in val
            )
        elif isinstance(val, list) and val and not all(isinstance(v, dict) for v in val):
            # Could be scalars collected from multiple blocks OR a native scalar list.
            # Try per-element any-semantics first; if the whole-list evaluation differs,
            # prefer the whole-list result (native list attributes like cidr_blocks).
            # Heuristic: if the attribute path contains a dot, it was collected from blocks.
            if "." in condition.attribute:
                matched = any(
                    self._evaluate_condition(condition.condition, condition.values, item)
                    for item in val
                )
            else:
                matched = self._evaluate_condition(condition.condition, condition.values, val)
        else:
            matched = self._evaluate_condition(condition.condition, condition.values, val)

        if matched and condition.and_check:
            matched = matched and self.evaluate(condition.and_check, attributes)

        return matched

    def resolve_attribute(self, attribute_path: str, attributes: Dict[str, Any]) -> Any:
        """Resolve a dotted attribute path; values from repeated blocks come back as a list."""
        return self._get_attribute_value(attribute_path, attributes)

    def _get_attribute_value(self, attribute_path: str, attributes: Dict[str, Any]) -> Any:
        parts = attribute_path.split(".")
        current: Any = attributes
        for i, part in enumerate(parts):
            if isinstance(current, dict):
                current = current.get(part, None)
            elif isinstance(current, list) and current and isinstance(current[0], dict):
                # We have a list of blocks (e.g. multiple ingress rules).
                # Collect the value of `part` from every element and return the list
                # so the caller can apply `any` semantics across all blocks.
                remaining_parts = parts[i + 1 :]
                result = []
                for item in current:
                    if isinstance(item, dict):
                        sub: Any = item.get(part, None)
                        # Descend into remaining path parts within this element
                        for rpart in remaining_parts:
                            if isinstance(sub, dict):
                                sub = sub.get(rpart, None)
                            else:
                                sub = None
                                break
                        if sub is not None:
                            result.append(sub)
                return result if result else None
            else:
                return None
        return current

    def _evaluate_condition(self, condition: str, expected_values: List[Any], actual_value: Any) -> bool:
        if condition == "exists":
            return actual_value is not None
        if condition == "not_exists":
            return actual_value is None

        # Convert list of single element to single element for comparison
        if isinstance(actual_value, list) and len(actual_value) == 1:
            actual_value = actual_value[0]

        if condition == "equals":
            return actual_value in expected_values if expected_values else False
        if condition == "not_equals":
            return actual_value not in expected_values if expected_values else False
        if condition == "in":
            return actual_value in expected_values
        if condition == "not_in":
            return actual_value not in expected_values
        if condition == "contains":
            if isinstance(actual_value, list):
                return any(v in actual_value for v in expected_values)
            elif isinstance(actual_value, str) and expected_values:
                return expected_values[0] in actual_value
            return False
        if condition == "not_contains":
            if isinstance(actual_value, list):
                return all(v not in actual_value for v in expected_values)
            elif isinstance(actual_value, str) and expected_values:
                return expected_values[0] not in actual_value
            return False
        if condition == "regex":
            if not actual_value or not expected_values:
                return False
            pattern = re.compile(str(expected_values[0]))
            return bool(pattern.search(str(actual_value)))

        return False
