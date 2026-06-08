class Node:

    def __init__(self, parent, data):
        self.parent = parent
        self.data = data
        self.children = set()
        if parent:
            parent.children.add(self)

    def remove(self, node):
        if not node:
            return
        self.children.remove(node)

    def find_version(self, package_name):
        stack = [self]
        while stack:
            node = stack.pop()
            if node.data.get('package_name') == package_name:
                return node.data.get('package_version')
            stack.extend(node.children)
        return None

    def __repr__(self):
        package_name = self.data.get('package_name')
        if package_name is None:
            return 'ROOT'
        package_name = package_name.replace('-', '_')
        package_version = self.data.get('package_version')
        package_extra = self.data.get('package_extra')
        if package_extra:
            package_name = f'{package_name}[{package_extra}]'
        return f'{package_name}-{package_version}'

    def get_bundle(self):
        return sorted(str(child) for child in self.children)

    def print_tree(self, indent="", last=True, root=True):
        if root:
            print(self)
        else:
            prefix = "└── " if last else "├── "
            print(indent + prefix + str(self))
        if root:
            new_indent = ""
        else:
            new_indent = indent + ("    " if last else "│   ")
        for i, child in enumerate(self.children):
            child.print_tree(new_indent, i == len(self.children) - 1, root=False)