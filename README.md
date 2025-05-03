# Projeto de Automação de Coleta de Dados Financeiros com PostgreSQL

## Descrição

Este projeto automatiza o processo de coleta de dados de ações brasileiras de fontes como Fundamentus e Yahoo Finance, armazenando-os de forma organizada em um banco de dados PostgreSQL. Ele utiliza uma classe dedicada (`PostgresDB`) para gerenciar a interação com o banco de dados, tornando o código mais modular, reutilizável e fácil de manter.

## Estrutura do Projeto

-   `main.py`: Script principal que orquestra a coleta, processamento e armazenamento dos dados.
-   `conexao_db.py`: Módulo contendo a classe `PostgresDB` para interagir com o banco de dados PostgreSQL.
-   `.env`: Arquivo para armazenar as credenciais de conexão com o banco de dados de forma segura (não versionado).
-   `requirements.txt`: Lista as dependências Python do projeto.

## Classe `PostgresDB` (`conexao_db.py`)

### Importância

A classe `PostgresDB` é um componente central deste projeto. Sua construção visa encapsular toda a lógica de interação com o banco de dados PostgreSQL, trazendo diversos benefícios:

-   **Abstração:** Esconde os detalhes de baixo nível da biblioteca `psycopg2`, oferecendo uma interface mais simples e focada nas operações comuns de banco de dados (conectar, executar query, inserir dados, etc.).
-   **Reutilização:** A classe pode ser facilmente reutilizada em outras partes do projeto ou em projetos futuros que necessitem interagir com o PostgreSQL.
-   **Manutenção:** Centraliza a lógica de conexão e execução de comandos SQL. Se for necessário alterar a forma de conexão ou otimizar queries, as modificações ficam contidas dentro da classe.
-   **Gerenciamento de Conexão:** Garante que as conexões e cursores sejam abertos e fechados corretamente, evitando vazamento de recursos. Os métodos gerenciam a conexão internamente, simplificando o uso no script principal.
-   **Segurança:** Facilita o uso de variáveis de ambiente (via `.env`) para as credenciais do banco, evitando que informações sensíveis sejam expostas diretamente no código.

### Funcionalidades (Métodos Principais)

-   `__init__(self)`: Inicializa a classe buscando as credenciais do banco de dados a partir das variáveis de ambiente (`.env`).
-   `_connect(self)`: Estabelece a conexão com o banco de dados e cria um cursor. É chamado internamente pelos outros métodos quando necessário.
-   `_close(self)`: Fecha o cursor e a conexão com o banco. Também chamado internamente para garantir a liberação de recursos.
-   `create_table(self, table_name, schema)`: Cria uma tabela no banco de dados se ela ainda não existir, utilizando a sintaxe SQL fornecida.
-   `execute_query(self, query, params=None)`: Executa um comando SQL genérico (como `INSERT`, `UPDATE`, `DELETE`, `CREATE`, etc.) que não retorna dados.
-   `query(self, query, params=None)`: Executa uma consulta `SELECT` e retorna os resultados como uma lista de dicionários (formato JSON-like), útil para APIs ou processamento direto.
-   `query_df(self, query, params=None)`: Executa uma consulta `SELECT` e retorna os resultados diretamente como um DataFrame Pandas, ideal para análise de dados.
-   `insert_dataframe(self, df, table_name)`: Realiza a inserção em massa (bulk insert) de um DataFrame Pandas inteiro em uma tabela específica do banco de dados de forma eficiente.

## Automação com `main.py`

O script `main.py` demonstra como utilizar a classe `PostgresDB` para criar uma automação completa de coleta e armazenamento de dados financeiros:

1.  **Configuração:** Define os nomes das tabelas, esquemas e o período de coleta de dados.
2.  **Conexão:** Instancia a classe `db = PostgresDB()`, que automaticamente busca as credenciais do `.env`.
3.  **Criação/Verificação de Tabelas:** Utiliza `db.create_table()` para garantir que as tabelas `acoes` e `cotacoesAcoes` existam no banco.
4.  **Atualização da Tabela de Ações:**
    -   Busca dados do Fundamentus.
    -   Filtra os dados relevantes.
    -   Limpa a tabela `acoes` existente usando `db.execute_query()`.
    -   Insere os novos dados de ações na tabela usando `db.insert_dataframe()`.
5.  **Busca de Tickers:** Obtém a lista de tickers da tabela `acoes` usando `db.query_df()`.
6.  **Processamento de Cotações:**
    -   Itera sobre cada ticker obtido.
    -   Baixa os dados históricos do Yahoo Finance.
    -   Prepara o DataFrame com as colunas corretas.
    -   **Limpa dados antigos:** Utiliza `db.execute_query()` para deletar registros existentes para o ticker e período específico antes de inserir os novos (garantindo idempotência parcial).
    -   **Insere/Atualiza cotações:** Utiliza `db.insert_dataframe()` para inserir os dados de cotação na tabela `cotacoesAcoes`.
7.  **Resumo:** Imprime um resumo do processo, incluindo tickers processados com sucesso e eventuais erros.

Ao utilizar a classe `PostgresDB`, o `main.py` foca na lógica de negócio (buscar, processar, organizar dados) e delega toda a complexidade da interação com o banco de dados para a classe, tornando o código mais limpo e legível.

## Pré-requisitos

-   Python 3.8+
-   PostgreSQL instalado e configurado
-   Bibliotecas Python listadas em `requirements.txt`

## Configuração

1.  Clone o repositório.
2.  Crie um arquivo `.env` na raiz do projeto com as suas credenciais do PostgreSQL:
    ```env
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432
    POSTGRES_DB=seu_banco_de_dados
    POSTGRES_USER=seu_usuario
    POSTGRES_PASSWORD=sua_senha
    ```
3.  Crie e/ou atualize o arquivo `requirements.txt` com as dependências:
    ```
    pandas
    psycopg2-binary  # Ou psycopg2, dependendo da sua instalação
    python-dotenv
    yfinance
    fundamentus
    # Adicione outras dependências se houver
    ```
4.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

## Como Executar

Execute o script principal a partir do terminal:
```bash
python main.py
```

O script conectará ao banco, criará/verificará as tabelas e iniciará o processo de coleta e armazenamento dos dados.

## Dependências Principais

-   `pandas`: Manipulação de dados.
-   `psycopg2`: Driver PostgreSQL para Python.
-   `python-dotenv`: Carregamento de variáveis de ambiente do arquivo `.env`.
-   `yfinance`: Download de dados do Yahoo Finance.
-   `fundamentus`: Coleta de dados do site Fundamentus.

---
