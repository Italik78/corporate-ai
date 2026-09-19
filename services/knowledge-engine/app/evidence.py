from dataclasses import dataclass, field
from enum import Enum
import re

class EvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONFLICT = "CONFLICT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

@dataclass(frozen=True)
class EvidenceResult:
    status: EvidenceStatus
    claims: list[dict] = field(default_factory=list)
    answerable: bool = False
    source_ids: list[int] = field(default_factory=list)
    reason: str = ""

class EvidenceEngine:
    VALUE_PATTERN = re.compile(
        r"(?<!\w)(\d+(?:[.,]\d+)?)\s*(евро|EUR|лева|лв\.?|дни|ден|часа|час|процента|%)\b",
        re.IGNORECASE,
    )
    WORD_PATTERN = re.compile(r"[А-Яа-яA-Za-z]{3,}")
    STOPWORDS = {
        "какъв","каква","какво","какви","как","има","при","за","на","в","по","от","до",
        "след","преди","с","се","са","е","трябва","служителят","служителя","всеки",
        "всяка","всички","този","това","тези","повече","по-малко","последователни",
        "ден","дни","час","часа","процента","евро","eur","лева","лв","срок",
    }

    def _normalize_word(self, word: str) -> str:
        word = word.lower()
        for suffix in ("овъчните","овъчни","ировката","ировка","ировъчни","ировъчна",
                       "ировъчно","ката","ите","ия","ят","та","ът","а","я","и","о","е"):
            if len(word) > len(suffix) + 3 and word.endswith(suffix):
                return word[:-len(suffix)]
        return word

    def _question_keywords(self, question):
        if not question:
            return set()
        result = set()
        for word in self.WORD_PATTERN.findall(question.lower()):
            if word in self.STOPWORDS:
                continue
            word = self._normalize_word(word)
            if len(word) >= 4:
                result.add(word[:7])
        return result

    def _sentence_for_position(self, text, position):
        start = max(
            text.rfind(".", 0, position),
            text.rfind("!", 0, position),
            text.rfind("?", 0, position),
            text.rfind("\n", 0, position),
        ) + 1
        ends = [x for x in (
            text.find(".", position), text.find("!", position),
            text.find("?", position), text.find("\n", position)
        ) if x != -1]
        return text[start:(min(ends) if ends else len(text))]

    def _extract_value_contexts(self, text, question_keywords):
        contexts = {}
        for match in self.VALUE_PATTERN.finditer(text):
            number, unit = match.group(1), match.group(2).lower()
            unit = {"eur":"евро","лв":"лева","лв.":"лева","ден":"дни",
                    "час":"часа","%":"процента"}.get(unit, unit)
            sentence = self._sentence_for_position(text, match.start())
            words = {
                self._normalize_word(w)[:7]
                for w in self.WORD_PATTERN.findall(sentence.lower())
                if w not in self.STOPWORDS
            }
            contexts.setdefault(unit, []).append({
                "number": number,
                "sentence": sentence,
                "overlap": question_keywords & words,
                "relevant": len(question_keywords & words) >= 3,
            })
        return contexts

    def _detect_numeric_conflicts(self, results, question=None):
        if len(results) < 2:
            return []
        qk = self._question_keywords(question)
        contextual = [self._extract_value_contexts(r.content, qk) for r in results]
        conflicts = []
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                for unit in sorted(set(contextual[i]) & set(contextual[j])):
                    a = {x["number"] for x in contextual[i][unit] if x["relevant"]}
                    b = {x["number"] for x in contextual[j][unit] if x["relevant"]}
                    if a and b and a != b:
                        conflicts.append({
                            "source_ids": [i + 1, j + 1],
                            "unit": unit,
                            "values_a": sorted(a),
                            "values_b": sorted(b),
                            "type": "numeric_conflict_candidate",
                        })
        return conflicts

    def evaluate(self, *, results, question=None):
        if not results:
            return EvidenceResult(
                status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
                answerable=False,
                reason="Няма намерени доказателства.",
            )

        question_keywords = self._question_keywords(question)
        relevant_source_ids = []
        for index, result in enumerate(results, start=1):
            content_words = {
                self._normalize_word(word)[:7]
                for word in self.WORD_PATTERN.findall(result.content.lower())
                if word not in self.STOPWORDS
            }
            overlap = question_keywords & content_words
            if len(overlap) >= 3:
                relevant_source_ids.append(index)

        if not relevant_source_ids:
            return EvidenceResult(
                status=EvidenceStatus.INSUFFICIENT_EVIDENCE,
                answerable=False,
                source_ids=[],
                reason="Намерени са семантично близки резултати, но няма достатъчно ключови съвпадения за надеждно доказателство.",
            )

        source_ids = list(range(1, len(results) + 1))
        conflicts = self._detect_numeric_conflicts(results, question)
        if conflicts:
            return EvidenceResult(
                status=EvidenceStatus.CONFLICT,
                claims=conflicts,
                answerable=False,
                source_ids=source_ids,
                reason="Установен е кандидат за конфликт между релевантни числови твърдения.",
            )
        return EvidenceResult(
            status=EvidenceStatus.SUPPORTED,
            answerable=True,
            source_ids=source_ids,
            reason="Не е установен релевантен числов конфликт.",
        )
