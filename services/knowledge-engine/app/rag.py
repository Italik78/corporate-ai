import json

NO_ANSWER = "Няма достатъчно информация в предоставените документи."

def build_messages(question: str, results) -> list[dict]:
    blocks = []
    for index, result in enumerate(results, start=1):
        blocks.append("\n".join([
            f"[SOURCE_ID: {index}]",
            f"document_id: {result.document_id}",
            f"source_file: {result.source_file}",
            f"page: {result.page}",
            f"section: {result.section}",
            f"score: {result.score:.6f}",
            "content:",
            result.content,
        ]))
    context = "\n\n".join(blocks)
    system = """Ти си корпоративен AI асистент. Отговаряй САМО въз основа на предоставените източници. Не измисляй факти. Отговаряй на български. Всеки факт трябва да има source_ids. Ако информацията липсва, използвай текста Няма достатъчно информация в предоставените документи. Върни само валиден JSON с answerable, answer, source_ids, claims и unanswered_parts."""
    user = f"""ВЪПРОС:\n{question}\n\nПРЕДОСТАВЕНИ ИЗТОЧНИЦИ:\n{context}\n\nВърни само валиден JSON."""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]

def parse_decision(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = text.replace("```json", "", 1).replace("```", "").strip()
    data = json.loads(text)
    if not isinstance(data, dict): raise ValueError("LLM response is not an object")
    for key in ("answerable", "answer", "source_ids", "claims"):
        if key not in data: raise ValueError(f"Missing {key}")
    data.setdefault("unanswered_parts", [])
    if not isinstance(data["answerable"], bool): raise ValueError("answerable must be boolean")
    if not isinstance(data["answer"], str): raise ValueError("answer must be string")
    if not isinstance(data["source_ids"], list): raise ValueError("source_ids must be list")
    if not isinstance(data["claims"], list): raise ValueError("claims must be list")
    if not isinstance(data["unanswered_parts"], list): raise ValueError("unanswered_parts must be list")
    return data