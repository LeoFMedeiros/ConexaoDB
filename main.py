import yfinance as yf
import pandas as pd
from conexao_db import PostgresDB
from datetime import date
import fundamentus as fd
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
    
def main():
    # --- Configurações ---
    start_date = "2018-01-01"
    end_date = date.today().strftime('%Y-%m-%d') # Pega até a data atual
    table_name_cotacoes = "cotacoesAcoes" 
    table_name_acoes = "acoes"          

    # Definição do schema da tabela de cotações
    table_schema_cotacoes = """
        date TEXT, 
        ticker TEXT, 
        open FLOAT, 
        high FLOAT, 
        low FLOAT, 
        close FLOAT, 
        adjclose FLOAT,
        volume BIGINT,
        PRIMARY KEY (date, ticker) 
    """
    # Definição do schema da tabela de ações
    table_schema_acoes = """
        acao TEXT PRIMARY KEY,
        empresa TEXT,
        setor TEXT,
        subsetor TEXT
    """

    # --- Inicializar conexão com DB ---
    print("Conectando ao banco de dados...")
    db = PostgresDB() # Agora não precisa passar credenciais, pega do .env

    # --- Criar tabelas (se não existirem) ---
    print(f"Verificando/Criando tabela {table_name_cotacoes}...")
    try:
        db.create_table(table_name_cotacoes, table_schema_cotacoes)
        print(f"Tabela {table_name_cotacoes} verificada/criada com sucesso.")
    except Exception as e:
        print(f"Erro ao criar/verificar tabela {table_name_cotacoes}: {e}")
        return # Sai se não conseguir criar a tabela de cotações

    print(f"Verificando/Criando tabela {table_name_acoes}...")
    try:
        db.create_table(table_name_acoes, table_schema_acoes)
        print(f"Tabela {table_name_acoes} verificada/criada com sucesso.")
    except Exception as e:
        print(f"Erro ao criar/verificar tabela {table_name_acoes}: {e}")
        

    # --- Buscar, filtrar e inserir/atualizar dados de AÇÕES da Fundamentus --- 
    print("\n--- Atualizando Tabela de Ações ({table_name_acoes}) ---")
    try:
        print("Buscando dados raw do Fundamentus...")
        df_resultado_raw = fd.get_resultado_raw()
        print(f"Encontrados {len(df_resultado_raw)} papéis raw.")

        print("Filtrando papéis com Cotação > 0 e Liquidez (2 meses) > 10000000...")
        df_filtrado = df_resultado_raw[ (df_resultado_raw['Cotação'] > 0) & (df_resultado_raw['Liq.2meses'] > 10000000) ]
        tickers_filtrados = df_filtrado.index.tolist()
        print(f"{len(tickers_filtrados)} papéis passaram no filtro.")
        df_fundamentus = pd.DataFrame()
        print("Buscando dados detalhados (Empresa, Setor, Subsetor) para papéis filtrados...")
        for ticker in tickers_filtrados:
            try:
                df = fd.get_papel(ticker)[['Papel', 'Empresa', 'Setor', 'Subsetor']]
                df_fundamentus = pd.concat([df_fundamentus, df]).reset_index(drop=True)
            except Exception as e:
                print(f"Erro no ticker {ticker} (Fundamentus): {e}")

        print(f"Detalhes buscados para {len(df_fundamentus)} papéis.")
        if not df_fundamentus.empty:
            df_fundamentus.columns = ['acao', 'empresa', 'setor', 'subsetor']
            df_fundamentus.drop_duplicates(subset=['acao'], inplace=True)
            print(f"Removendo duplicatas, restaram {len(df_fundamentus)} ações únicas.")

            print(f"Limpando tabela {table_name_acoes} antes da inserção...")
            db.execute_query(f"DELETE FROM {table_name_acoes}") 
            
            print(f"Inserindo {len(df_fundamentus)} ações na tabela {table_name_acoes}...")
            db.insert_dataframe(df_fundamentus, table_name_acoes)
            print(f"Tabela {table_name_acoes} atualizada com sucesso!")
        else:
            print("Nenhum dado da Fundamentus para inserir após busca e filtros.")

    except Exception as e:
        print(f"Erro GRANDE durante a atualização da tabela {table_name_acoes}: {e}")

    # --- Buscar tickers da tabela 'acoes' para processar cotações --- 
    print(f"\n--- Buscando Tickers da Tabela {table_name_acoes} para Cotações ---")
    try:
        # Usando a nova função query_df para obter os tickers diretamente como DataFrame
        df_tickers = db.query_df(f"SELECT acao FROM {table_name_acoes}")
        
        if df_tickers.empty:
            print(f"Nenhum ticker encontrado na tabela {table_name_acoes}. Verifique a etapa anterior ou o conteúdo da tabela.")
            return # Sai se não há ações para buscar cotações
            
        # Extrair a coluna 'acao' como lista e adicionar sufixo '.SA' para o yfinance
        tickers_para_yf = [ticker + '.SA' for ticker in df_tickers['acao'] if ticker]
        
        print(f"Encontrados {len(tickers_para_yf)} tickers no banco para buscar cotações: {tickers_para_yf[:5]}...{tickers_para_yf[-5:] if len(tickers_para_yf) > 5 else ''}") # Mostra alguns
    except Exception as e:
        print(f"Erro ao buscar tickers da tabela {table_name_acoes}: {e}")
        return # Sai se não conseguiu buscar os tickers

    # --- Loop para Baixar e Inserir Cotações para cada Ticker --- 
    print(f"\n--- Processando Cotações para Tickers do Banco ({start_date} a {end_date}) ---")
    total_tickers = len(tickers_para_yf)
    erros_cotacoes = []
    sucessos_cotacoes = 0

    for i, ticker in enumerate(tickers_para_yf):
        print(f"\nProcessando ticker {i+1}/{total_tickers}: {ticker}")

        # --- Baixar dados do yfinance ---
        print(f"  Baixando dados para {ticker}...")
        try:
            data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False, multi_level_index=False)
            if data.empty:
                print(f"  Aviso: Nenhum dado encontrado para {ticker} no período {start_date} a {end_date}.")
                continue # Pula para o próximo ticker
            print(f"  Download concluído para {ticker}. {len(data)} registros.")
        except Exception as e:
            msg_erro = f"Erro ao baixar dados do yfinance para {ticker}: {e}"
            print(f"  {msg_erro}")
            erros_cotacoes.append(msg_erro)
            continue # Pula para o próximo ticker

        # --- Preparar DataFrame para inserção ---
        print(f"  Preparando dados de {ticker} para inserção...")
        try:
            df_to_insert = data.reset_index() # Transforma o índice (Date) em coluna
            df_to_insert['Ticker'] = ticker   # Adiciona a coluna Ticker
            
            # Garante que as colunas esperadas existem antes de renomear
            cols_necessarias = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            if not all(col in df_to_insert.columns for col in cols_necessarias):
                 msg_erro = f"Erro: Colunas esperadas {cols_necessarias} não encontradas no DataFrame baixado para {ticker}. Colunas recebidas: {df_to_insert.columns.tolist()}"
                 print(f"  {msg_erro}")
                 erros_cotacoes.append(msg_erro)
                 continue

            df_to_insert.rename(columns={ 
                'Date': 'Date', 'Open': 'Open', 'High': 'High', 
                'Low': 'Low', 'Close': 'Close', 'Adj Close': 'AdjClose', 'Volume': 'Volume'
            }, inplace=True)
            # Seleciona e reordena as colunas conforme o schema do DB
            df_to_insert = df_to_insert[['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'AdjClose', 'Volume']]
            # Converte a coluna de data para string para corresponder ao schema TEXT
            df_to_insert['Date'] = df_to_insert['Date'].dt.strftime('%Y-%m-%d')
            # Converte nomes das colunas para minúsculas para corresponder ao DB
            df_to_insert.columns = [col.lower() for col in df_to_insert.columns]
            print(f"  Dados de {ticker} preparados.")
        except Exception as e:
            msg_erro = f"Erro ao preparar DataFrame para {ticker}: {e}"
            print(f"  {msg_erro}")
            erros_cotacoes.append(msg_erro)
            continue # Pula para o próximo ticker

        # --- Inserir dados no banco --- 
        print(f"  Inserindo/Atualizando {len(df_to_insert)} registros de cotações para {ticker} na tabela {table_name_cotacoes}...")
        try:
            # Limpar dados antigos PARA ESTE TICKER E PERÍODO antes de inserir os novos.
            print(f"  Limpando dados antigos para {ticker} no período {start_date} a {end_date}...")
            # Modificado para usar aspas no nome da tabela para garantir case-sensitivity
            db.execute_query(f'DELETE FROM "{table_name_cotacoes}" WHERE ticker = %s AND date >= %s AND date <= %s', 
                             (ticker, start_date, end_date))
            
            db.insert_dataframe(df_to_insert, table_name_cotacoes)
            print(f"  Dados de {ticker} inseridos com sucesso!")
            sucessos_cotacoes += 1
        except Exception as e:
            msg_erro = f"Erro ao inserir cotações de {ticker} no banco: {e}"
            print(f"  {msg_erro}")
            erros_cotacoes.append(msg_erro)
            # Não continua para o próximo ticker aqui, apenas registra o erro

    # --- Resumo Final --- 
    print("\n--- Processamento Concluído ---")
    print(f"Total de tickers para processar cotações: {total_tickers}")
    print(f"Tickers processados com sucesso (cotações inseridas): {sucessos_cotacoes}")
    print(f"Tickers com erro durante o processo de cotações: {len(erros_cotacoes)}")
    if erros_cotacoes:
        print("Detalhes dos erros:")
        for erro in erros_cotacoes:
            print(f"  - {erro}")

if __name__ == "__main__":
    main() 