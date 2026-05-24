from __future__ import annotations

import random
import unicodedata
from dataclasses import dataclass


_LATIN_KEYBOARD_ADJACENCY = {
    "a": "sqw",
    "b": "vghn",
    "c": "xdfv",
    "d": "serfcx",
    "e": "wsdr",
    "f": "drtgvc",
    "g": "ftyhbv",
    "h": "gyujnb",
    "i": "ujko",
    "j": "huikmn",
    "k": "jiolm",
    "l": "kop",
    "m": "njk",
    "n": "bhjm",
    "o": "iklp",
    "p": "ol",
    "q": "wa",
    "r": "edft",
    "s": "awedxz",
    "t": "rfgy",
    "u": "yhji",
    "v": "cfgb",
    "w": "qase",
    "x": "zsdc",
    "y": "tghu",
    "z": "asx",
}

_LATIN_PUNCT = ["!", "?", "...", ",", "!!", "?!"]


@dataclass
class NoiseInjector:
    seed: int = 42

    def _rng(self, seed: int | None = None) -> random.Random:
        return random.Random(self.seed if seed is None else seed)

    def _clusters(self, text: str) -> list[str]:
        clusters: list[str] = []
        current = ""
        for char in text:
            if current and unicodedata.combining(char):
                current += char
                continue
            if current:
                clusters.append(current)
            current = char
        if current:
            clusters.append(current)
        return clusters

    def _is_latin_cluster(self, cluster: str) -> bool:
        base = cluster[0]
        return base.isascii() and base.isalpha()

    def _substitute_cluster(self, cluster: str, rng: random.Random) -> str:
        if not cluster:
            return cluster
        base = cluster[0]
        lower = base.lower()
        if self._is_latin_cluster(cluster) and lower in _LATIN_KEYBOARD_ADJACENCY:
            replacement_pool = _LATIN_KEYBOARD_ADJACENCY[lower]
            replacement = rng.choice(replacement_pool)
            if base.isupper():
                replacement = replacement.upper()
            return replacement + cluster[1:]

        codepoint = ord(base)
        for step in (1, -1, 2, -2):
            candidate = chr(codepoint + step)
            if unicodedata.category(candidate)[0] in {"L", "N"}:
                return candidate + cluster[1:]
        return base + cluster[1:]

    def inject(self, text: str, noise_rate: float = 0.15, noise_types: list[str] | None = None, seed: int | None = None) -> str:
        rng = self._rng(seed)
        requested_types = noise_types or ["deletion", "repeat", "substitution"]
        clusters = self._clusters(text)
        if not clusters:
            return text

        edit_budget = max(1, int(round(len(clusters) * noise_rate)))
        output: list[str] = []
        index = 0

        while index < len(clusters):
            cluster = clusters[index]
            if edit_budget > 0 and rng.random() < noise_rate:
                noise_type = rng.choice(requested_types)
                if noise_type == "deletion":
                    edit_budget -= 1
                    index += 1
                    continue
                if noise_type == "repeat":
                    output.append(cluster)
                    output.append(cluster)
                    edit_budget -= 1
                    index += 1
                    continue
                if noise_type == "substitution":
                    output.append(self._substitute_cluster(cluster, rng))
                    edit_budget -= 1
                    index += 1
                    continue
                if noise_type == "extra_punct":
                    output.append(cluster)
                    output.append(rng.choice(_LATIN_PUNCT))
                    edit_budget -= 1
                    index += 1
                    continue

            output.append(cluster)
            index += 1

        noisy = "".join(output)
        if noise_rate > 0 and rng.random() < noise_rate / 2 and "extra_punct" in requested_types:
            noisy += rng.choice(_LATIN_PUNCT)
        return noisy
