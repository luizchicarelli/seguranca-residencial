# Checklist do grupo (prazo: 24/11, 23:59; meta: enviar até 22h)

Os passos técnicos detalhados estão no README, em "Como reproduzir".

## Situação

- [x] Banco e API na Supabase (versão 2: lote, status e alarme)
- [x] Simulação no Wokwi com 3 sensores Hall, PIR e 2 LEDs, testada com POST 201 - 4 leituras
- [x] Painel com a planta da casa testado com dados reais
- [x] Painel republicado no Cloudflare Pages com a versão 2
- [x] Commits de firmware, painel e documentação
- [x] Vídeo
- [x] Relatório em PDF e entrega no Moodle

## Commits

O histórico precisa mostrar quem fez o quê. Cada pessoa commita a própria parte, **da própria conta**:

| Pessoa | Arquivos | Situação |
| --- | --- | --- |
| Luiz Henrique Soares Chicareli de Andrade | `supabase/`, `scripts/`, `README.md` | ✅ versões 1 e 2 enviadas |
| Gabriel Almeida Ermenegildo | `firmware/diagram.json`, `firmware/main.py` | versão 1 ✅ · versão 2 ✅ |
| Felipe Augusto Santos Dorta de Oliveira | `frontend/index.html` | ✅ versão 2 enviada |
| Enzo Luiz Tsutsumi de Almeida José | `docs/relatorio.md`, `docs/CHECKLIST.md`, links e nomes no `README.md` | ✅ |

Antes de cada commit do firmware, confiram que o `main.py` está com `COLOQUE_A_DEVICE_KEY_AQUI` e não com a chave real.

Cada pessoa deve entender e saber explicar a própria parte, porque todos apresentam.

## Roteiro do vídeo (cerca de 5 minutos)

Deixem 3 janelas visíveis: Wokwi, Supabase (Edge Functions → readings → Logs) e o painel. Antes de gravar, coloquem os 3 sliders no máximo (tudo fechado) e deixem o alarme desarmado.

1. **Fluxo completo:**
   - mover o slider da **porta de entrada** no Wokwi;
   - o Serial mostra POST 201 - 4 leituras;
   - os Logs da Supabase mostram "4 leitura(s) recebida(s)";
   - a porta desliza na planta e fica laranja (ABERTA).
2. **Outros sensores:** abrir a **janela da sala** e a **janela do quarto**, depois simular movimento no **PIR**. Mostrar cada um reagindo na planta.
3. **Alerta com alarme desarmado:** deixar uma janela aberta por mais de 10 s. Ela pisca em vermelho, a faixa mostra "ALERTA" e o LED vermelho acende.
4. **Alarme:**
   - fechar tudo e clicar em **Armar alarme** no painel;
   - no próximo envio, o LED amarelo acende no Wokwi;
   - abrir a porta, e a faixa **"INTRUSÃO DETECTADA"** aparece sem esperar 10 s;
   - desarmar no final.
5. **Histórico:** clicar numa janela na planta e mostrar o gráfico e a tabela só dela.
6. **Interrupção e retomada:** pausar o Wokwi; após ~30 s aparece **"DADOS DESATUALIZADOS"**. Dar play e o painel volta ao normal.
7. **Painel fechado:**
   - fechar a aba do painel;
   - mexer nos sensores;
   - abrir https://uamnpagnpwvdsnxwnvhc.supabase.co/functions/v1/readings/status no navegador (ou rodar `./scripts/teste-api.ps1 -SomenteConsulta`) e mostrar que as leituras foram gravadas;
   - reabrir o painel.

Publicar no YouTube como **Não listado**.

## Prints para o relatório

- [x] Tabela `readings` na Supabase com leituras dos 4 sensores
- [x] Erro 401 com chave errada
- [x] Planta em alerta e em "INTRUSÃO DETECTADA"
- [x] Planta com "DADOS DESATUALIZADOS"
- [x] Diagrama da arquitetura (README no GitHub)

## Entrega no Moodle (uma pessoa envia)

- [x] PDF do relatório (2 a 4 páginas), com nomes e todos os links
- [x] Link do GitHub: https://github.com/luizchicarelli/seguranca-residencial
- [x] Link do Wokwi: https://wokwi.com/projects/481506936104773633
- [x] Link do painel: https://seguranca-residencial.pages.dev
- [x] Link do vídeo: https://youtu.be/f7NLYSfg5Vc
- [x] Preencher a tabela de links e de integrantes no README
