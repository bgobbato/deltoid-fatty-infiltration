# Plano de trabalho — ferramenta DFDI (infiltração gordurosa do deltoide)

Data: 08/nov/2026. Base: Rescigno et al. 2026, *Eur J Orthop Surg Traumatol* 36:424 (DFDI).

## 1. Ideia em uma frase

Uma página web simples: envia a TC, gira o volume como no artigo, escolhe o corte de referência,
o cirurgião desenha o deltoide à mão, e o sistema calcula HU médio, área e DFDI.

O artigo **não segmenta automaticamente**. Ele desenha o ROI à mão em um corte (MicroDicom).
Então a primeira versão faz o mesmo. A automação vem depois, como ajuda, não como requisito.

## 2. Fluxo do usuário

1. **Enviar** a TC (DICOM em zip ou NIfTI `.nii.gz`).
2. **Janela**: botões prontos — partes moles/músculo (W 400 / L 50), osso (W 2000 / L 500), personalizada.
3. **Reorientar** (MPR):
   - Axial perpendicular à diáfise do úmero.
   - Coronal paralelo ao plano da escápula.
   - V1: o cirurgião marca 2 pontos no centro da diáfise (proximal e distal) e 3 pontos na escápula
     (ou gira com alças na tela). O servidor reamostra o volume.
4. **Escolher o corte**: rola o axial reorientado. Lista de checagem na tela, igual ao artigo:
   - tuberosidade maior com cortical em toda a volta;
   - cabeça do úmero visível;
   - sem colo cirúrgico.
   O cirurgião confirma o corte. (Decisão clínica: dele.)
5. **Desenhar** o deltoide pela fáscia interna (anterior + médio + posterior).
   Ferramentas: caneta com preenchimento automático, polígono, borracha, desfazer.
   Excluir osso cortical, gordura subcutânea, fáscia externa, hematoma, líquido, fragmentos.
6. **Medir**: botão "Calcular". Mostra na hora:
   - área (mm²) e HU médio — os dois números do artigo;
   - DFDI (com a referência escolhida, ver §6);
   - extras: % de gordura intramuscular (−190 a −30 HU), % de músculo de baixa atenuação (−29 a 29 HU),
     HU mediana e desvio, histograma;
   - imagem PNG com o contorno sobre a TC (controle de qualidade).
7. **Salvar** o caso. Exportar todos os casos em CSV para a estatística.

## 3. O que reaproveitar do SchulterPlan

Encontrado no ai-memory e nos repositórios (`Advita/schulterplan-backend` e `Advita/gps-web-planner Implantcast`).

| Peça | Onde está | Uso aqui |
|---|---|---|
| Visualizador NiiVue (lê NIfTI no navegador, MPR 3 planos) | frontend, `MPR_PLAN.md`, `js/landmarks/mpr.js` | tela de MPR, janelas e rolagem de cortes |
| Conversão DICOM → NIfTI com checagem de geometria | backend v2, `sp_pipeline/ingest/dicom_to_nifti.py` + pré-voo (ADR-006) | etapa de envio |
| Leitura de metadados DICOM e desidentificação | backend v2, `sp_pipeline/ingest/dicom_metadata*.py` (ADR-004) | anonimizar antes de salvar |
| Eixo do úmero por PCA + RANSAC | backend v2, `sp_pipeline/anatomy/proximal_humerus_metrics.py` | V2: sugerir o eixo da diáfise sozinho |
| Segmentação de úmero e escápula (ArmCortNet, nnU-Net, roda no Mac via MPS) | app offline, `desktop/engine/` | V2: alimentar o eixo e o plano da escápula |
| Amostragem oblíqua trilinear de NIfTI | navsim, `ctOblique` | reamostrar o volume reorientado |
| Coordenadas clique → mm por plano | `js/landmarks/mpr.js` | marcar pontos na diáfise e na escápula |

NiiVue (pesquisa 4, código-fonte da 0.68.1): tem desenho — `setDrawingEnabled`, `setPenValue(v, isFilledPen)`
(caneta que preenche o contorno fechado), `drawUndo`, `drawBitmap` (máscara em JS para mandar ao servidor), `loadDrawing`.
Janela por `cal_min`/`cal_max`. **Não faz plano oblíquo 2D** → a reorientação é feita no servidor (SimpleITK) e volta
como um NIfTI novo, já alinhado. Ainda não testado no nosso código.

**Cuidado:** a máscara é desenhada na grade reorientada. HU e área são medidos nesse volume reamostrado
(interpolação linear do HU, voxel isotrópico, p. ex. 0,5 mm). O sistema registra a matriz e o tamanho do voxel usados.
O artigo também mediu em imagem reformatada (MPR), então isso segue o método.

**Decisão do cirurgião (08/nov/2026): projeto separado.** Este projeto **copia** as peças. Não mexe nos repositórios do SchulterPlan
(eles têm regras próprias de revisão e fases).

## 4. Arquitetura

```
Navegador (uma página HTML, NiiVue via CDN, sem build)
   │  envia TC, pontos do eixo, corte escolhido, máscara desenhada
   ▼
Servidor Python (FastAPI) — dentro de 1 container Docker
   ├─ ingest:   DICOM zip → NIfTI (cópia do SchulterPlan)
   ├─ reorient: pontos → matriz → volume reamostrado (SimpleITK/scipy)
   ├─ measure:  motor DFDI (src/dfdi, feito pelo agente do protocolo)
   └─ store:    SQLite + pasta de casos (NIfTI, máscara, PNG, JSON)
```

- Local: `docker compose up` → `http://localhost:8080`.
- VPS: o mesmo container atrás do Caddy (HTTPS automático) com login simples.
  Dados de paciente só desidentificados. Backup da pasta de casos.

## 5. Fases

| Fase | Entrega | Prova de pronto |
|---|---|---|
| 0 | Repositório, `.venv`, estrutura de pastas | `git status` limpo, README |
| 1 | **Motor de medição** (TC NIfTI + máscara → HU, área, extras, DFDI, PNG) | **Feito** (08/nov): `src/dfdi`, comando `dfdi measure / batch / icc`; 9 testes em fantoma passam. Falta testar em TC real |
| 2 | Página: enviar NIfTI, janelas, MPR 3 planos, rolar cortes | **Feito** (08/nov): `app/server.py` + `app/static/index.html`; zip DICOM real (Toshiba, 658 arquivos) → 9 séries em 13 s; 3 planos, janelas, barra de cortes, HU na mira. kVp não aparece no `.json` do dcm2niix (falta ler do DICOM) |
| 3 | Desenho do deltoide no corte + botão Calcular | **Feito** (08/nov): página e motor em inglês; caneta que preenche, Exclude (label 2), apagar, desfazer, área ao vivo; checklist do corte; Calculate → métricas, flags, PNG, `results.csv`. Testado na TC real: máscara volta à grade nativa sem espelhar (permRAS −1). Desenho real pelo cirurgião ainda não testado |
| 4 | Reorientação manual (2 pontos na diáfise + plano da escápula) | **Feito** (08/nov): 2 cliques no centro do canal (distal e proximal) + glenoide anterior/posterior opcional → série nova "⟂ REORIENTED" (mesmo pixel e espessura, caixa 20×20 cm). TC real: inclinação de 25,7° (área nativa ~11% maior); diáfise vertical no coronal e sagital na tela. Teste com fantoma 20°: área dentro de 2% |
| 5 | Lista de casos, exportar CSV, DFDI pela coorte | CSV abre no Excel/R com 1 linha por caso |
| 6 | Docker local (`docker compose up`) | **Feito** (08/nov): `Dockerfile` (python 3.14-slim, usuário sem root, healthcheck), `docker-compose.yml` (porta só em 127.0.0.1, `./dados` montado em `/data`, fuso SP), versões fixas em `requirements.lock`. Imagem 535 MB, build ~2 min. 14 testes passam dentro do container; envio do zip real em 16 s; medida do desenho do cirurgião idêntica ao Mac (1823,7 mm², HU 25,55) |
| 7 | VPS: HTTPS, login, backup | **Feito** (08/nov): https://dfdi.aioraflow.com — tudo na VPS (decisão do cirurgião). Container em 127.0.0.1:18090, nginx novo com HTTPS + senha, DNS na Vercel. Outros serviços da VPS intactos. Teste pela internet: sem senha 401, com senha 200; zip de 87 MB em 62 s; medida idêntica ao Mac. Backup ainda não configurado |
| 8 | Validação como no artigo: 20 casos, ICC intra e interobservador; comparar com MicroDicom/Horos no mesmo corte | ICC calculado; diferença média de HU e área |
| 9 | Automação (ajuda, opcional) — ver §7 | cada ajuda medida contra o desenho manual |

Ordem sugerida: 1 → 2 → 3 → 5 → 6 (já dá para usar em pesquisa com TC já alinhada) → 4 → 7 → 8 → 9.

## 6. Cuidados com o DFDI

- **Máscara negativa de osso (pedido do cirurgião, 08/nov):** `src/dfdi/bone.py`, ligada por padrão na página.
  Cortical > 200 HU → fechamento por osso (raio 6 mm; fragmentos a < 4 mm contam como um osso) → preenche buracos
  no axial, coronal e sagital → dilata 1 px. Remove cortical **e medula** de todos os ossos do corte.
  Testado na TC real (cortes 95–122: medula preenchida, sem invadir o deltoide) e em fantomas.
  Limite: janela cortical muito larga (fratura, cisto grande) pode deixar parte da medula; conferir em azul na tela.
  Próximo passo opcional: trocar pelo úmero/escápula do ArmCortNet (SchulterPlan, 4–16 min por TC) ou TotalSegmentator.

- HU do DFDI = média de todos os pixels da ROI (gordura incluída), como o MicroDicom do artigo.
  Só sai osso (> 200 HU) e ar (< −200 HU). Os valores sem limpeza também vão na saída.
- Desenhar já na imagem reorientada. Reorientar uma máscara pronta puxa o HU para baixo
  (fantoma: 47,7 contra 50). Não misturar casos reorientados e nativos na mesma coorte.
- Na validação cruzada, recalcular os z-scores só com os dados de treino de cada dobra.

- O artigo calcula o Z **dentro da própria coorte** (HU 42,9 ± 3,8; área 3651,6 ± 662,2 mm²; n = 100).
- Usar a média e o desvio do artigo em outro tomógrafo é só **aproximação**. Fica marcado assim na tela.
- O certo: calcular o Z na sua coorte, por tomógrafo e protocolo. O sistema guarda a referência usada em cada caso.
- O artigo usou TC sem contraste, 120 kVp, 1,25 mm. O sistema avisa se o DICOM fugir disso (kVp, contraste, espessura).
- O próprio artigo diz que a área sozinha teve correlação um pouco maior que o DFDI. O sistema sempre mostra os dois componentes.

## 7. Automação depois (fase 9)

Do mais fácil para o mais difícil:

1. **Eixo e corte sugeridos**: úmero segmentado (ArmCortNet do SchulterPlan) → eixo por PCA → sugere o corte
   na tuberosidade maior. O cirurgião confirma.
2. **Pré-desenho por limiar**: dentro de um laço grosso, manter só −29 a 150 HU e tirar osso pelo úmero segmentado.
3. **Ferramenta interativa**: nnInteractive ou MedSAM2 (cliques no corte). Licença do nnInteractive é não comercial.
4. **Modelo do deltoide em TC do grupo CAOS 2025** (Rajabzadeh-Oghaz … Gobbato, Roche, Kumar; doi 10.29007/tx68):
   97% das máscaras aceitáveis para cirurgiões. Não é público. Caminho: pedir ao grupo (você é coautor).
   Trabalho de base (pesquisa 5): *J Clin Med* 2024, doi 10.3390/jcm13051273 — SwinUNETR, treino 78 / teste 20,
   Dice 0,93 ± 0,03, deltoide 3D; gordura = voxels −190 a −30 HU ÷ (gordura + músculo −29 a 150 HU).
   Código e pesos não aparecem como públicos.
5. **Treinar nosso modelo 2D**: os desenhos manuais da fase 3 viram dados de treino (nnU-Net 2D, só o corte de referência).
   Um corte só é bem mais fácil que o deltoide 3D inteiro.

## 8. Documentos desta pasta

- `docs/artigo_DFDI_texto.txt` — texto do artigo.
- `docs/pesquisa_1_modelos_prontos.md` — modelos e bases com deltoide (agente Haiku).
- `docs/pesquisa_2_estrategias.md` — como melhorar a segmentação (agente Haiku).
- `docs/pesquisa_3_literatura.md` — como outros mediram (agente Haiku).
- `docs/protocolo_medicao_DFDI.md` — protocolo do motor de medição (agente do protocolo).

As pesquisas Haiku marcam o que não conseguiram verificar. Algumas fontes deram erro 403 (MDPI).
