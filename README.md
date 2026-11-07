# Preçificador de Produtos - NF-e

Aplicação web para ler arquivos XML de NF-e, calcular custo real dos produtos e
sugerir preços de venda. O backend usa FastAPI; a interface é HTML, CSS e
JavaScript e é servida pelo próprio backend.

## Arquitetura

```text
app/
├── api/routes.py             # validação HTTP e upload
├── domain/
│   ├── models.py             # modelos internos
│   └── pricing.py            # cálculo de custo e preço
├── infrastructure/nfe_xml.py # leitura segura do XML da NF-e
└── main.py                   # composição da aplicação e páginas
deploy/
├── nginx.conf                # proxy reverso para Ubuntu
└── precificador.service      # serviço systemd de exemplo
tests/
└── fixtures/nfe.xml          # XML sintético para testes
```

O navegador e a API usam a mesma origem. O Nginx é opcional para desenvolvimento
local, mas recomendado na VPS para expor a aplicação, terminar TLS e limitar o
tamanho dos uploads. O processo FastAPI fica vinculado a `127.0.0.1`; só o Nginx
deve aceitar conexões públicas.

## Desenvolvimento local

Requer Python 3.10 ou superior.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Abra <http://127.0.0.1:8000>. A interface e a API ficam disponíveis no mesmo
servidor; não inicie `python3 -m http.server` em outro terminal. O comando
`python3 main.py` continua disponível como atalho de desenvolvimento, também
com reload.

Execute os testes automatizados com:

```bash
python -m unittest discover -s tests -v
```

## Implantação em VPS Ubuntu

Os exemplos abaixo usam `/opt/precificacao_de_produtos`, `www-data`, o domínio
`exemplo.com` e uma instalação Ubuntu com Python 3. O serviço de exemplo roda
dois workers; ajuste esse número à memória e à carga da VPS. Esta aplicação não
tem autenticação de usuários: antes de torná-la pública, restrinja o acesso por
VPN/firewall ou configure autenticação no proxy reverso.

### 1. Instalar o sistema e preparar o código

```bash
sudo apt update
sudo apt install -y python3 python3-venv nginx
sudo mkdir -p /opt/precificacao_de_produtos
```

Copie ou clone o repositório para `/opt/precificacao_de_produtos`. Em seguida:

```bash
cd /opt/precificacao_de_produtos
sudo python3 -m venv .venv
sudo .venv/bin/python -m pip install --upgrade pip
sudo .venv/bin/python -m pip install -r requirements.txt
```

O código e o ambiente virtual precisam ser legíveis e executáveis pelo usuário
`www-data`. O serviço não precisa gravar XMLs: os arquivos enviados são
processados em memória e não são persistidos.

### 2. Ativar o serviço FastAPI

Revise os caminhos e o usuário em `deploy/precificador.service`, se necessário,
e instale:

```bash
sudo cp deploy/precificador.service /etc/systemd/system/precificador.service
sudo systemctl daemon-reload
sudo systemctl enable --now precificador
sudo systemctl status precificador
```

O backend escuta somente em `127.0.0.1:8000`. Para investigar problemas:

```bash
sudo journalctl -u precificador -f
curl http://127.0.0.1:8000/health
```

### 3. Configurar o Nginx

Edite `deploy/nginx.conf` e substitua `exemplo.com` pelo domínio da VPS. Copie e
ative o site:

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/precificador
sudo ln -s /etc/nginx/sites-available/precificador /etc/nginx/sites-enabled/precificador
sudo nginx -t
sudo systemctl reload nginx
```

Configure DNS para apontar o domínio à VPS e libere as portas 80 e 443 no
firewall da nuvem e no firewall do sistema. Exemplo com UFW:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 4. Habilitar HTTPS

Configure um certificado TLS válido antes de usar a aplicação com dados reais.
Com Certbot para Nginx, por exemplo:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d exemplo.com -d www.exemplo.com
```

Confira a renovação automática com `sudo certbot renew --dry-run`. Não envie
credenciais nem certificados ao repositório.

Como o aplicativo não possui login próprio, proteja-o no Nginx antes de liberar
acesso público. Uma opção simples para uma instalação privada é autenticação
Basic sobre HTTPS:

```bash
sudo apt install -y apache2-utils
sudo htpasswd -c /etc/nginx/precificador.htpasswd seu_usuario
sudo chown root:www-data /etc/nginx/precificador.htpasswd
sudo chmod 640 /etc/nginx/precificador.htpasswd
```

Adicione estas diretivas ao `server` HTTPS criado pelo Certbot, valide e
recarregue o Nginx:

```nginx
auth_basic "Precificador";
auth_basic_user_file /etc/nginx/precificador.htpasswd;
```

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Alternativamente, restrinja o acesso por VPN/firewall. Não exponha a aplicação
sem autenticação ou controle equivalente.

## Fluxo e API

`POST /api/processar-xml` recebe um arquivo `file` e os campos de formulário
opcionais `pct_fixo`, `pct_simples`, `pct_cartao` e `pct_lucro`. Os percentuais
por padrão são 15, 8.32, 3 e 20. A soma deve ser inferior a 100%. O arquivo é
limitado a 10 MiB e XMLs com DTD/entidades são rejeitados.

O endpoint também mantém a opção de ler um nome de arquivo da pasta `xml/` do
servidor; o uso normal da interface é enviar o arquivo diretamente. A rota
`/health` retorna o estado básico da aplicação para verificações operacionais.

Os arquivos NF-e contêm informações comerciais e podem conter dados pessoais.
Evite armazená-los no servidor ou em logs sem uma necessidade definida; a
aplicação não mantém histórico nem salva os uploads.
