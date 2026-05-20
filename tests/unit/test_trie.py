"""Tests for the DomainTrie module."""

from __future__ import annotations

from adfilter.trie import DomainTrie, TrieNode


class TestDomainTrie:
    def test_insert_and_contains(self):
        trie = DomainTrie()
        trie.insert("example.com")
        assert trie.contains("example.com")
        assert not trie.contains("other.com")

    def test_size_and_len(self):
        trie = DomainTrie()
        assert len(trie) == 0
        trie.insert("a.com")
        trie.insert("b.com")
        assert len(trie) == 2
        assert trie.size == 2

    def test_duplicate_insert(self):
        trie = DomainTrie()
        trie.insert("example.com")
        trie.insert("example.com")
        assert trie.size == 1

    def test_suffix_matching(self):
        trie = DomainTrie()
        trie.insert("example.com")
        assert trie.matches("sub.example.com")
        assert trie.matches("deep.sub.example.com")
        assert not trie.matches("other.com")

    def test_exact_match_via_matches(self):
        trie = DomainTrie()
        trie.insert("ads.example.com")
        assert trie.matches("ads.example.com")
        assert not trie.matches("example.com")

    def test_contains_operator(self):
        trie = DomainTrie()
        trie.insert("example.com")
        assert "sub.example.com" in trie
        assert "other.com" not in trie

    def test_find_parent(self):
        trie = DomainTrie()
        trie.insert("example.com")
        assert trie.find_parent("sub.example.com") == "example.com"
        assert trie.find_parent("other.com") is None

    def test_find_parent_no_match(self):
        trie = DomainTrie()
        trie.insert("ads.example.com")
        assert trie.find_parent("example.com") is None

    def test_remove(self):
        trie = DomainTrie()
        trie.insert("example.com")
        assert trie.remove("example.com")
        assert not trie.contains("example.com")
        assert trie.size == 0

    def test_remove_nonexistent(self):
        trie = DomainTrie()
        assert not trie.remove("example.com")

    def test_remove_non_terminal(self):
        trie = DomainTrie()
        trie.insert("sub.example.com")
        # example.com is not terminal
        assert not trie.remove("example.com")

    def test_all_domains(self):
        trie = DomainTrie()
        trie.insert("a.com")
        trie.insert("b.org")
        trie.insert("sub.a.com")
        domains = sorted(trie.all_domains())
        assert domains == ["a.com", "b.org", "sub.a.com"]

    def test_insert_with_data(self):
        trie = DomainTrie()
        trie.insert("example.com", data={"source": "test"})
        assert trie.contains("example.com")

    def test_empty_domain(self):
        trie = DomainTrie()
        trie.insert("")
        assert trie.size == 0
        assert not trie.contains("")
        assert not trie.matches("")
        assert trie.find_parent("") is None

    def test_trailing_dot(self):
        trie = DomainTrie()
        trie.insert("example.com.")
        assert trie.contains("example.com")

    def test_case_insensitive(self):
        trie = DomainTrie()
        trie.insert("Example.COM")
        assert trie.contains("example.com")
        assert trie.matches("SUB.EXAMPLE.COM")

    def test_remove_cleans_empty_branches(self):
        trie = DomainTrie()
        trie.insert("deep.sub.example.com")
        trie.remove("deep.sub.example.com")
        assert trie.size == 0
        # Root should have no children
        assert len(trie._root.children) == 0

    def test_remove_preserves_siblings(self):
        trie = DomainTrie()
        trie.insert("a.example.com")
        trie.insert("b.example.com")
        trie.remove("a.example.com")
        assert trie.size == 1
        assert trie.contains("b.example.com")
