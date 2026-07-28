# StarPets MM2 Price Monitor

Monitora preços de itens do Murder Mystery 2 no [StarPets](https://starpets.gg/pt/mm2), envia alertas no Discord
para pechinchas e publica um painel web com todos os preços.

## Como funciona

- `monitor.py` — busca itens (armas, pets, diversos) na API do StarPets, detecta itens **$4+** com **50%+ de desconto**
  sobre o preço médio de mercado, e envia alerta no Discord (webhook + menção ao usuário). Evita alertas duplicados
  usando `state.json`. Registra cada alerta enviado em `docs/alerts_log.json` (para o painel).
- `dashboard_data.py` — busca todos os itens (sem filtro de desconto) e salva em `docs/data.json` para o painel.
  Também acumula um histórico de preço médio por categoria em `docs/history.json`.
- `docs/index.html` — painel web estático (sem dependências externas) que lê os arquivos acima.
- `.github/workflows/monitor.yml` — roda tudo isso automaticamente **a cada 5 minutos, 24/7**, mesmo com o
  computador desligado, via GitHub Actions. Depois de cada execução, commita os dados atualizados de volta pro repo.

## Onde tudo está hospedado

- **Repositório**: https://github.com/folladorgabriel/starpets-mm2-monitor (público — sem segredos no código;
  o webhook do Discord fica em *Settings → Secrets → Actions → DISCORD_WEBHOOK*)
- **Painel web**: https://folladorgabriel.github.io/starpets-mm2-monitor/ (GitHub Pages, atualiza a cada 5 min)
- **Alertas**: chegam no canal do Discord configurado no webhook, te marcando (`<@1443748218843168839>`)

## Ajustando os critérios de alerta

Edite as constantes no topo de `monitor.py`:

```python
DISCOUNT_THRESHOLD = 0.5   # 50% abaixo do preço médio
MIN_PRICE = 4.0            # preço mínimo pra considerar
ITEM_TYPES = ["weapon", "pet", "misc"]
```

Depois é só commitar e dar push — o próximo ciclo do GitHub Actions já usa os novos valores.

## Funcionalidades do painel

- Abas por categoria (Armas / Pets / Diversos / Todos)
- Busca por nome, filtro por raridade, filtro "só pechinchas" e "só Godly $4+"
- Favoritos (★) salvos no navegador (localStorage) — não sincroniza entre dispositivos
- Exportar CSV da lista filtrada atual
- Feed de alertas recentes e gráfico de tendência de preço médio por categoria
- Alternância manual de tema claro/escuro (além de seguir o tema do sistema)

## Rodando manualmente

```bash
pip install -r requirements.txt
DISCORD_WEBHOOK="https://discord.com/api/webhooks/..." python3 monitor.py
python3 dashboard_data.py
```

## Forçar uma execução no GitHub Actions sem esperar o cron

```bash
gh workflow run monitor.yml --repo folladorgabriel/starpets-mm2-monitor
```

## Limitações conhecidas

- O histórico de preços (`docs/history.json`) guarda até 1000 pontos (~3,5 dias em ciclos de 5 min) e depois
  descarta os mais antigos.
- O painel puxa dados públicos do StarPets; se a API deles mudar de formato, `monitor.py` e `dashboard_data.py`
  vão precisar de ajuste (o formato esperado da API está comentado no código).
- Netlify foi testado mas abandonado em favor do GitHub Pages (limite de minutos de build no plano grátis
  não aguenta deploys a cada 5 min). Pode ser removido do painel do Netlify se não for mais usado.
