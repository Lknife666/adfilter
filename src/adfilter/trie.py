"""Domain trie — efficient domain matching data structure.

Used for fast suffix-based lookups in allowlist matching and
subdomain collapse operations. Supports O(k) lookup where k
is the number of labels in the domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TrieNode:
    """A node in the domain trie."""

    children: dict[str, TrieNode] = field(default_factory=dict)
    is_terminal: bool = False
    data: dict[str, object] = field(default_factory=dict)


class DomainTrie:
    """Trie structure for efficient domain suffix matching.

    Domains are stored in reverse label order (TLD first) for
    efficient suffix matching. For example, 'ads.example.com' is
    stored as ['com', 'example', 'ads'].

    Supports:
    - Exact domain match
    - Suffix match (parent domain covers all subdomains)
    - Wildcard lookups
    """

    def __init__(self) -> None:
        self._root = TrieNode()
        self._size = 0

    def insert(self, domain: str, *, data: dict[str, object] | None = None) -> None:
        """Insert a domain into the trie.

        Args:
            domain: domain name (e.g. 'ads.example.com')
            data: optional metadata to attach to this domain
        """
        labels = self._split_domain(domain)
        if not labels:
            return

        node = self._root
        for label in labels:
            if label not in node.children:
                node.children[label] = TrieNode()
            node = node.children[label]

        if not node.is_terminal:
            self._size += 1
        node.is_terminal = True
        if data:
            node.data.update(data)

    def contains(self, domain: str) -> bool:
        """Check if the exact domain is in the trie."""
        labels = self._split_domain(domain)
        if not labels:
            return False

        node = self._root
        for label in labels:
            if label not in node.children:
                return False
            node = node.children[label]
        return node.is_terminal

    def matches(self, domain: str) -> bool:
        """Check if domain matches any entry (exact or suffix).

        Returns True if the domain itself or any parent domain is
        in the trie (suffix matching). For example, if 'example.com'
        is in the trie, 'sub.example.com' will also match.
        """
        labels = self._split_domain(domain)
        if not labels:
            return False

        node = self._root
        for label in labels:
            if label not in node.children:
                return False
            node = node.children[label]
            # If we hit a terminal node, this is a suffix match
            if node.is_terminal:
                return True
        return False

    def find_parent(self, domain: str) -> str | None:
        """Find the shortest matching parent domain.

        Returns the parent domain that covers this domain via suffix
        matching, or None if no parent matches.
        """
        labels = self._split_domain(domain)
        if not labels:
            return None

        node = self._root
        for i, label in enumerate(labels):
            if label not in node.children:
                return None
            node = node.children[label]
            if node.is_terminal:
                # Reconstruct the parent domain
                matched_labels = labels[: i + 1]
                return ".".join(reversed(matched_labels))
        return None

    def remove(self, domain: str) -> bool:
        """Remove a domain from the trie. Returns True if removed."""
        labels = self._split_domain(domain)
        if not labels:
            return False

        # Walk to the node
        path: list[tuple[TrieNode, str]] = []
        node = self._root
        for label in labels:
            if label not in node.children:
                return False
            path.append((node, label))
            node = node.children[label]

        if not node.is_terminal:
            return False

        node.is_terminal = False
        node.data.clear()
        self._size -= 1

        # Clean up empty branches
        for parent, label in reversed(path):
            child = parent.children[label]
            if not child.children and not child.is_terminal:
                del parent.children[label]
            else:
                break

        return True

    def all_domains(self) -> list[str]:
        """Return all domains stored in the trie."""
        results: list[str] = []
        self._collect(self._root, [], results)
        return results

    def _collect(
        self, node: TrieNode, path: list[str], results: list[str]
    ) -> None:
        if node.is_terminal:
            results.append(".".join(reversed(path)))
        for label, child in node.children.items():
            path.append(label)
            self._collect(child, path, results)
            path.pop()

    @staticmethod
    def _split_domain(domain: str) -> list[str]:
        """Split domain into reversed labels for trie storage."""
        domain = domain.strip().lower().rstrip(".")
        if not domain:
            return []
        labels = domain.split(".")
        labels.reverse()
        return labels

    @property
    def size(self) -> int:
        """Number of domains stored in the trie."""
        return self._size

    def __len__(self) -> int:
        return self._size

    def __contains__(self, domain: str) -> bool:
        return self.matches(domain)
