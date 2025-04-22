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


def to_relational_algebra(parsed):
    if not parsed:
        return "Consulta inválida"

    # Projeção
    projection = f"π_{parsed['select_clause']}"

    # Tabela
    base = parsed["from_clause"]

    # JOIN
    if parsed["joins"] and parsed["joins"][0] and parsed["joins"][1]:
        join_table = parsed["joins"][0]  
        join_condition = parsed["joins"][1] 
        base = f"{base} ⨝_{join_condition} {join_table}"

    # Seleção
    if parsed["where_clause"]:
        selection = f"σ_{parsed['where_clause']}({base})"
        return f"{projection}({selection})"

    return f"{projection}({base})"

# AQUI ESSA MAIN AQUI É SÓ PRA TESTAR

# if __name__ == "__main__":
#     query = input("Digite a consulta SQL: ")

#     validator = SQLValidator()
#     parsed = validator.explain_validation(query)
#     algebra = to_relational_algebra(parsed)

#     print("\n parser:", parsed, "\n")
#     print("Álgebra Relacional:", algebra, "\n")
