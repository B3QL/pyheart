from pyheart.tree import GameTree, Node


def test_create_tree():
    tree = GameTree()

    assert tree.nodes == 1
    assert tree.height == 0

    tree.root.add_children(Node() for _ in range(10))
    assert tree.nodes == 11
    assert tree.height == 1

    tree.root.children[0].add_children(Node() for _ in range(5))
    assert tree.nodes == 16
    assert tree.height == 2


def test_select_node():
    tree = GameTree()

    assert tree.select_node(tree.root, tree.game) == tree.root
