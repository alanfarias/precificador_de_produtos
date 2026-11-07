# Preçificador de Produtos - NF-e

Este projeto foi desenvolvido para processar arquivos XML de Nota Fiscal Eletrônica (NF-e), identificar os produtos e calcular um preço de venda sugerido com base em custos, despesas, impostos e margem de lucro desejada.

A aplicação é composta por duas partes:

- Backend em Python com FastAPI
- Frontend em HTML + JavaScript puro

O objetivo principal é permitir que o usuário importe um XML da NF-e, ajuste algumas porcentagens e veja os produtos com custo real e preço sugerido de venda.

---

## Visão geral do processo

### 1. Importação do XML
O usuário seleciona um arquivo `.xml` de NF-e no frontend.

### 2. Envio para o backend
O arquivo é enviado para a API em:

- `POST http://127.0.0.1:8000/api/processar-xml`

### 3. Leitura e análise do XML
O backend usa a biblioteca padrão `xml.etree.ElementTree` para ler o arquivo e identificar os dados importantes da NF-e, como:

- dados do fornecedor
- CNPJ / razão social
- total da nota
- itens do produto
- valores de produto, frete, seguro, outros valores e impostos

### 4. Cálculo do custo real
Para cada item, o sistema:

- calcula a proporção do valor do item no total da nota
- rateia despesas globais (frete, seguro, outros)
- soma impostos relevantes
- divide o custo total pelo quantidade para obter o custo unitário real

### 5. Cálculo do preço sugerido
A fórmula utilizada considera:

- despesas fixas
- Simples Nacional
- taxa do cartão
- lucro desejado

O cálculo usa uma lógica de markup com base na soma dessas porcentagens, retornando um valor sugerido de venda para cada produto.

### 6. Exibição no frontend
O frontend mostra:

- fornecedor e CNPJ no cabeçalho dos resultados
- quantidade de itens
- tabela com todos os produtos, custo da nota, custo real e preço sugerido

Todos os campos e valores financeiros seguem o padrão brasileiro, com separador de milhar em pontos e decimal em vírgula, por exemplo: `R$10.000,00`.

---

## Estrutura do projeto

```text
notaFiscal/
├── main.py
├── index.html
├── xml/
│   └── 41261000376001000135550010000210611000223808.xml
├── .venv/
├── requirements.txt
└── README.md
```

### Arquivos principais

- `main.py`: backend FastAPI com lógica de processamento do XML
- `index.html`: frontend para upload do XML e visualização dos resultados
- `xml/...xml`: exemplo de NF-e para testes
- `requirements.txt`: dependências do projeto

---

## Tecnologias utilizadas

- Python 3
- FastAPI
- Uvicorn
- XML parsing com `ElementTree`
- HTML + JavaScript
- CSS customizado para dashboard visual

---

## Como executar o projeto

## 1. Entrar na pasta do projeto

```bash
cd /home/alan/Desenv/Jerusalem/precificador_de_produtos
```

## 2. Criar ou ativar o ambiente virtual

Se ainda não existir, crie o ambiente:

```bash
python3 -m venv .venv
```

Ative o ambiente:

```bash
source .venv/bin/activate
```

## 3. Instalar as dependências

```bash
pip install fastapi uvicorn python-multipart
```

Ou, se o projeto já tiver `requirements.txt`:

```bash
pip install -r requirements.txt
```

## 4. Rodar o backend

No terminal, execute:

```bash
python3 main.py
```

Isso inicia o servidor FastAPI em:

```text
http://127.0.0.1:8000
```

O arquivo `main.py` já está configurado para subir o app com `uvicorn` na porta 8000.

## 5. Abrir o frontend

Abra o arquivo `index.html` no navegador.

Você também pode iniciar um servidor simples para servir a página, caso deseje:

```bash
python3 -m http.server 8001
```

E então abrir:

```text
http://127.0.0.1:8001
```

> Importante: em produção, o frontend precisa apontar para o mesmo domínio do backend ou para uma URL customizada via `window.__APP_API_URL`. O valor padrão usa a origem atual do navegador para chamar `/api/processar-xml`, evitando o problema de `127.0.0.1` em deploys remotos.

Além disso, o backend aceita upload do XML pela interface do navegador ou também pode processar um arquivo já presente na pasta `xml/` no servidor, passando `filename` no formulário da requisição.

---

## Como usar no navegador

1. Ajuste os valores das porcentagens no painel lateral:
   - Despesas Fixas
   - Simples Nacional
   - Taxa do Cartão
   - Lucro Desejado
2. Use a calculadora de despesas fixas para descobrir o percentual ideal:
   - informe as despesas fixas mensais
   - informe o faturamento mensal estimado
   - o sistema calcula automaticamente a porcentagem e pode aplicá-la ao campo "Despesas Fixas (%)"
3. Clique em "Importar XML"
4. Selecione o arquivo `.xml` da NF-e
5. O backend processa o arquivo e exibe os produtos
6. Confira o custo real, preço sugerido e tabela de itens

---

## Exemplo de XML de teste

O projeto já inclui um arquivo de exemplo em:

```text
xml/41261000376001000135550010000210611000223808.xml
```

Esse arquivo pode ser usado para testar o fluxo completo da aplicação.

---

## Endpoints da API

### POST `/api/processar-xml`

Recebe:

- `file`: arquivo XML
- `pct_fixo`: percentual de despesas fixas
- `pct_simples`: percentual do Simples Nacional
- `pct_cartao`: percentual da taxa do cartão
- `pct_lucro`: percentual de lucro desejado

Retorna:

- fornecedor
- configurações aplicadas
- lista de produtos com custo e preço sugerido

---

## Observações importantes

- O backend utiliza CORS para permitir comunicação com o frontend em ambiente local.
- O código trata diferentes namespaces de NF-e, garantindo compatibilidade com XMLs que tenham variações no padrão da estrutura.
- Caso o arquivo não seja válido ou a soma das margens ultrapasse 100%, a API retorna erro com mensagem clara.

---

## Como rodar tudo de uma vez

Em um terminal:

```bash
cd /home/alan/Desenv/Jerusalem/notaFiscal
source .venv/bin/activate
python3 main.py
```

Em outro terminal:

```bash
cd /home/alan/Desenv/Jerusalem/notaFiscal
python3 -m http.server 8001
```

Depois abra o front no navegador e teste com um XML de NF-e.

---

## Dica de desenvolvimento

Para uma futura evolução, este projeto pode receber:

- upload em múltiplos arquivos
- exportação em CSV ou Excel
- edição direta de preços finais
- cálculo por categoria de produto
- autenticação e histórico de simulações
- painel administrativo para gestão de margens por loja

---

## Conclusão

Este projeto combina processamento de XML, cálculo financeiro e interface web simples para transformar uma NF-e em uma ferramenta prática para precificação de produtos. Ele serve como base sólida para gestão de preços e pode ser expandido para cenários comerciais mais complexos.
