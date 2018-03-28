from pyheart.tree import GameTree, Node, ActionGenerator


def test_create_tree():
    tree = GameTree()

    assert tree.nodes == 1
    assert tree.height == 0

    tree.root.add_children(Node() for _ in range(10))
    assert tree.nodes == 11
    assert tree.height == 1

    list(tree.root.children)[0].add_children(Node() for _ in range(5))
    assert tree.nodes == 16
    assert tree.height == 2


def test_tree_policy():
    tree = GameTree()

    assert tree.tree_policy() != tree.root
    assert tree.nodes == 2
    assert tree.tree_policy()
    assert tree.nodes == 3


def test_node_path():
    tree = GameTree()
    root = tree.root
    root.add_children(Node() for _ in range(10))
    first_level = list(root.children)[0]
    first_level.add_children(Node() for _ in range(5))

    leaf = list(first_level.children)[0]

    assert leaf.is_leaf
    assert list(leaf.path) == [leaf, first_level, root]


def test_node_expand_abilities():
    tree = GameTree()
    root = tree.root
    tree.game.start()
    actions = list(ActionGenerator(tree.game))
    assert root.is_expandable
    for _ in actions:
        tree.expand(root)
        assert root.is_expandable
    assert len(root.children) == len(actions)
    tree.expand(root)
    assert len(root.children) == len(actions)
    assert not root.is_expandable
