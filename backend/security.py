import re


PURE_DOC_PATTERN = re.compile(r"(?<!\d)(\d{11}|\d{14})(?!\d)")
FORMATTED_CPF_PATTERN = re.compile(r"(?<!\d)\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
FORMATTED_CNPJ_PATTERN = re.compile(r"(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)")


# Mantem os ultimos digitos visiveis e mascara o restante.
def _mask_digits_keep_last(value: str, keep: int = 4) -> str:
    digits_seen = 0
    masked = []

    for char in reversed(value):
        if char.isdigit():
            digits_seen += 1
            masked.append(char if digits_seen <= keep else "*")
        else:
            masked.append(char)

    return "".join(reversed(masked))


# Mascara CPF/CNPJ em logs para reduzir exposicao de dados sensiveis.
def mask_sensitive_text(text: str) -> str:
    safe_text = str(text or "")

    for pattern in (FORMATTED_CPF_PATTERN, FORMATTED_CNPJ_PATTERN, PURE_DOC_PATTERN):
        safe_text = pattern.sub(lambda match: _mask_digits_keep_last(match.group(0)), safe_text)

    return safe_text
