import re

# Define the levels of numbering/hierarchy
hierarchy_levels = [
    ('lowercase', re.compile(r'^\(([a-z])\)')),  # First level: a, b, c...
    ('number', re.compile(r'^\((\d+)\)')),  # Second level: 1, 2, 3...
    ('roman', re.compile(r'^\((i{1,3}|iv|v|vi{0,3}|ix|x{1,3})\)')),  # Third level: i, ii, iii...
    ('uppercase', re.compile(r'^\(([A-Z])\)')),  # Fourth level: A, B, C...
]


# Function to determine the level based on the symbol
def determine_level(line):
    for level_index, (_, pattern) in enumerate(hierarchy_levels):
        match = pattern.match(line.strip())
        if match:
            return level_index, match.group(1)
    return None, None


# Function to infer the hierarchy
def infer_hierarchy(lines):
    hierarchy = []
    stack = []
    current_indent_level = -1

    for line in lines:
        level_index, symbol = determine_level(line)

        if level_index is not None:
            # Update stack based on the level index
            while len(stack) > level_index:
                stack.pop()
            stack.append(symbol)
            current_indent_level = level_index
            indent = '  ' * current_indent_level
            hierarchy.append((indent, line.strip()))
            print(
                f"DEBUG HEADER: '{line.strip()}', Level: {level_index}, Indent: {current_indent_level}, Stack: {stack}")
        else:
            indent = '  ' * (current_indent_level + 1)
            hierarchy.append((indent, line.strip()))
            print(f"DEBUG CONTENT: '{line.strip()}', Indent: {current_indent_level + 1}, Stack: {stack}")

    return hierarchy


# Example document lines
lines = [
    "(a) First level",
    "Some content for the first level.",
    "(1) Second level",
    "Some content for the second level.",
    "(i) Third level",
    "Some content for the third level.",
    "(A) Fourth level",
    "Some content for the fourth level.",
    "More content for the fourth level.",
    "(ii) Another third level",
    "Content for another third level.",
    "(2) Another second level",
    "Content for another second level.",
]

# Infer the hierarchy
hierarchy = infer_hierarchy(lines)

# Print the inferred hierarchy
print("\nFINAL OUTPUT:")
for indent, line in hierarchy:
    print(f"{indent}{line}")
