
from flask import Flask, render_template, request
import re
import networkx as nx
import matplotlib.pyplot as plt
import os

app = Flask(__name__)

METADADOS = {
    "Categoria": ["idCategoria", "Descricao"],
    "Produto": ["idProduto", "Nome", "Descricao", "Preco", "QuantEstoque", "Categoria_idCategoria"],
    "TipoCliente": ["idTipoCliente", "Descricao"],
    "Cliente": ["idCliente", "Nome", "Email", "Nascimento", "Senha", "TipoCliente_idTipoCliente", "DataRegistro"],
    "TipoEndereco": ["idTipoEndereco", "Descricao"],
    "Endereco": ["idEndereco", "EnderecoPadrao", "Logradouro", "Numero", "Complemento", "Bairro", "Cidade", "UF", "CEP", "TipoEndereco_idTipoEndereco", "Cliente_idCliente"],
    "Telefone": ["Numero", "Cliente_idCliente"],
    "Status": ["idStatus", "Descricao"],
    "Pedido": ["idPedido", "Status_idStatus", "DataPedido", "ValorTotalPedido", "Cliente_idCliente"],
    "Pedido_has_Produto": ["idPedidoProduto", "Pedido_idPedido", "Produto_idProduto", "Quantidade", "PrecoUnitario"]
}


class SQLValidator:
    def __init__(self):
        self.regex = re.compile(
            r"(?i)\bSELECT\b\s+(.*?)\s+\bFROM\b\s+([\w\.]+)(?:\s+\bJOIN\b\s+([\w\.]+)\s+\bON\b\s+(.+?))*(?:\s+\bWHERE\b\s+(.+?))?$"
        )

    def explain_validation(self, query):
        match = self.regex.match(query)
        if match:
            return {
                "select_clause": match.group(1),
                "from_clause": match.group(2),
                "joins": [match.group(3), match.group(4)] if match.group(3) else None,
                "where_clause": match.group(5) if match.group(5) else None
            }
        return None

def validar_campos(parsed):
    erros = []
    tabelas_env = [parsed['from_clause']]
    if parsed['joins']:
        tabelas_env.append(parsed['joins'][0])

    for tabela in tabelas_env:
        if tabela not in METADADOS:
            erros.append(f"Tabela '{tabela}' não existe.")

    campos_select = [c.strip() for c in parsed['select_clause'].split(",")]
    for campo in campos_select:
        if not campo_valido(campo, tabelas_env):
            erros.append(f"Campo do SELECT inválido: '{campo}'")

    if parsed['where_clause']:
        campos_where = extrair_campos(parsed['where_clause'])
        for campo in campos_where:
            if not campo_valido(campo, tabelas_env):
                erros.append(f"Campo do WHERE inválido: '{campo}'")

    if parsed['joins']:
        campos_on = extrair_campos(parsed['joins'][1])
        for campo in campos_on:
            if not campo_valido(campo, tabelas_env):
                erros.append(f"Campo do JOIN ON inválido: '{campo}'")

    return erros

def campo_valido(campo, tabelas):
    for tabela in tabelas:
        if tabela in METADADOS and campo in METADADOS[tabela]:
            return True
    return False

def extrair_campos(expressao):
    expressao_sem_strings = re.sub(r"'[^']*'|\"[^\"]*\"", "", expressao)

    tokens = re.findall(r"[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?", expressao_sem_strings)

    campos = []
    operadores = {"and", "or", "not", "in", "on", "join", "like"}

    for token in tokens:
        if '.' in token:
            _, campo = token.split('.', 1)
        else:
            campo = token
        if campo.lower() not in operadores:
            campos.append(campo)

    return campos

def to_relational_algebra(parsed):
    if not parsed:
        return "Consulta inválida"

    projection = f"π_{parsed['select_clause']}"
    base = parsed["from_clause"]

    if parsed["joins"] and parsed["joins"][0] and parsed["joins"][1]:
        join_table = parsed["joins"][0]  
        join_condition = parsed["joins"][1] 
        base = f"{base} ⨝_{join_condition} {join_table}"

    if parsed["where_clause"]:
        selection = f"σ_{parsed['where_clause']}({base})"
        return f"{projection}({selection})"

    return f"{projection}({base})"

def gerar_grafo(parsed):
    grafo = []
    node_id = 0

    def novo_no(tipo, conteudo, inputs=None):
        nonlocal node_id
        no = {
            "id": f"n{node_id}",
            "tipo": tipo,
            "conteudo": conteudo,
            "inputs": inputs or []
        }
        grafo.append(no)
        node_id += 1
        return no["id"]

    base_id = novo_no("tabela", parsed["from_clause"])

    if parsed["joins"]:
        join_table = parsed["joins"][0]
        join_cond = parsed["joins"][1]
        join_id = novo_no("junção", join_cond, [base_id, novo_no("tabela", join_table)])
    else:
        join_id = base_id

    if parsed["where_clause"]:
        selecao_id = novo_no("seleção", parsed["where_clause"], [join_id])
    else:
        selecao_id = join_id

    projecao_id = novo_no("projeção", parsed["select_clause"], [selecao_id])

    return grafo

def desenhar_grafo(grafo, filename='static/grafo.png'):
    import networkx as nx
    import matplotlib.pyplot as plt
    import os

    G = nx.DiGraph()

    for no in grafo:
        label = f"{no['tipo'].capitalize()}\n[{formatar_conteudo(no['conteudo'])}]"
        G.add_node(no["id"], label=label)

    for no in grafo:
        for inp in no["inputs"]:
            G.add_edge(inp, no["id"])

    pos = nx.spring_layout(G, seed=42)

    labels = nx.get_node_attributes(G, 'label')
    plt.figure(figsize=(12, 7))
    nx.draw(
        G, pos, with_labels=False, arrows=True,
        node_color='skyblue', node_size=3000, edgecolors='black', linewidths=1
    )
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=9, font_weight='bold')
    plt.title("Grafo de Operadores", fontsize=14)
    plt.axis('off')
    os.makedirs('static', exist_ok=True)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def formatar_conteudo(texto, largura=20):
    if not texto:
        return ""
    return "\n".join([texto[i:i+largura] for i in range(0, len(texto), largura)])

def gerar_plano_execucao(grafo):
    import networkx as nx

    G = nx.DiGraph()
    id_para_no = {}

    for no in grafo:
        G.add_node(no["id"])
        id_para_no[no["id"]] = no
        for inp in no["inputs"]:
            G.add_edge(inp, no["id"])

    try:
        ordem_ids = list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        return ["Erro: o grafo contém ciclos."]

    plano = []
    for i, no_id in enumerate(ordem_ids, 1):
        no = id_para_no[no_id]
        linha = f"{i}. {no['tipo'].capitalize()}: {no['conteudo']}"
        plano.append(linha)

    return plano

def otimizar_grafo(grafo):
    import networkx as nx

    grafo_otimizado = []
    id_map = {}
    novo_id = 0

    def copiar_no(no, novos_inputs):
        nonlocal novo_id
        novo = {
            "id": f"n{novo_id}",
            "tipo": no["tipo"],
            "conteudo": no["conteudo"],
            "inputs": novos_inputs
        }
        grafo_otimizado.append(novo)
        id_map[no["id"]] = novo["id"]
        novo_id += 1
        return novo["id"]

    G = nx.DiGraph()
    for no in grafo:
        G.add_node(no["id"])
        for inp in no["inputs"]:
            G.add_edge(inp, no["id"])

    try:
        ordem_ids = list(nx.topological_sort(G))
    except nx.NetworkXUnfeasible:
        return grafo

    id_to_node = {no["id"]: no for no in grafo}

    for no_id in ordem_ids:
        no = id_to_node[no_id]

        novos_inputs = [id_map[inp] for inp in no["inputs"]]

        if no["tipo"] == "seleção":
            campo = extrair_campos(no["conteudo"])[0] if extrair_campos(no["conteudo"]) else None
            for n in grafo_otimizado:
                if n["tipo"] == "tabela":
                    if campo and campo_valido(campo, [n["conteudo"]]):
                        novos_inputs = [n["id"]]
                        break
            copiar_no(no, novos_inputs)

        elif no["tipo"] == "projeção":
            continue

        else:
            copiar_no(no, novos_inputs)

    ultima_id = grafo_otimizado[-1]["id"]
    projecoes = [no for no in grafo if no["tipo"] == "projeção"]
    if projecoes:
        copiar_no(projecoes[0], [ultima_id])

    return grafo_otimizado


@app.route('/', methods=['GET', 'POST'])
def index():
    result = {}
    if request.method == 'POST':
        query = request.form['sql_query']
        validator = SQLValidator()
        parsed = validator.explain_validation(query)

        erros = []
        if parsed:
            erros = validar_campos(parsed)
            algebra = to_relational_algebra(parsed)
            grafo = gerar_grafo(parsed)
            desenhar_grafo(grafo)
            plano_execucao = gerar_plano_execucao(grafo)
            grafo_otimizado = otimizar_grafo(grafo)
            desenhar_grafo(grafo_otimizado, filename='static/grafo_otimizado.png')
            plano_otimizado = gerar_plano_execucao(grafo_otimizado)

        if parsed:
            result = {
                "parsed": parsed,
                "algebra": algebra,
                "original": query,
                "erros": erros,
                "grafo": grafo,
                "plano_execucao": plano_execucao,
                "grafo_otimizado": grafo_otimizado,
                "plano_otimizado": plano_otimizado
            }
        else:
            result = {
                "parsed": None,
                "algebra": "Consulta inválida",
                "original": query,
                "erros": ["Consulta inválida (sintaxe não reconhecida)."]
            }

        result = {
            "parsed": parsed,
            "algebra": algebra,
            "original": query,
            "erros": erros,
            "grafo": grafo,
            "plano_execucao": plano_execucao,
            "grafo_otimizado": grafo_otimizado,
            "plano_otimizado": plano_otimizado
        }

    return render_template('index.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)
