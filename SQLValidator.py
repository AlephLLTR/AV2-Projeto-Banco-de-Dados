import re

class SQLValidator:
    def __init__(self):
        # Define o regex para validação
        self.regex = re.compile(
            r"(?i)\bSELECT\b\s+(.*?)\s+\bFROM\b\s+([\w\.]+)(?:\s+\bJOIN\b\s+([\w\.]+)\s+\bON\b\s+(.+?))*(?:\s+\bWHERE\b\s+(.+?))?$"
        )

    def validate(self, query):
        match = self.regex.match(query)
        return match

    def explain_validation(self, query):
        match = self.regex.match(query)
        if match:
            details = {
                "select_clause": match.group(1),
                "from_clause": match.group(2),
                "joins": [match.group(3), match.group(4)] if match.group(3) else None,
                "where_clause": match.group(5) if match.group(5) else None
            }
            return details
        else:
            return "Consulta inválida!"
