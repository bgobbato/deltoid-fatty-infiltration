# Protocolo de medição do DFDI a partir de TC em NIfTI com máscara do deltoide

Versão 0.1 (08/11/2026). Motor de referência: `src/dfdi/` (v0.1.0).
Artigo-base: Rescigno G, Suraci F, Benelli C, Maffulli N, Vadalà A. *The Deltoid Fatty Degeneration Index (DFDI): a CT-based composite measure associated with functional outcome after Reverse Total Shoulder Arthroplasty.* Eur J Orthop Surg Traumatol 2026;36:424. doi:10.1007/s00590-026-05018-z

> Pergunta respondida aqui: "já tenho a TC em NIfTI e a segmentação manual do deltoide; como gero o índice de infiltração gordurosa automaticamente?"
> Resposta curta: a conta (CSA, HU médio, z-scores, DFDI e as métricas extras) é 100% automática. O que **não** é automático, e precisa da sua confirmação, é: (1) o eixo da diáfise, se for reorientar; (2) a escolha do corte de referência; (3) a exclusão de hematoma, líquido e fragmentos, que não se separam do músculo pelo HU.

---

## 1. O que o artigo fez (resumo operacional)

| Item | Artigo |
|---|---|
| Aquisição | TC sem contraste, 64 canais (GE Revolution EVO), 120 kVp, mA modulado (~110–260), reconstrução 1,25 mm, kernel partes moles "standard" |
| Reformatação | axial **perpendicular à diáfise umeral**, coronal **paralelo ao plano da escápula** |
| Corte de referência | primeira imagem, no sentido craniocaudal, ao nível do topo da tuberosidade maior que mostra: tuberosidade maior com cortical circunferencial, cabeça umeral visível e **ausência** do colo cirúrgico |
| ROI | deltoide inteiro (anterior + médio + posterior), à mão livre ou polígono, pela **fáscia interna**; exclui cortical, gordura subcutânea, fáscia externa; exclui hematoma grosseiro, coleções e fragmentos corticais deslocados; edema difuso inseparável fica dentro |
| Software | MicroDicom Viewer: devolve CSA (mm²) e HU médio da ROI |
| Índice | Z = (X − média)/DP **dentro da coorte**; DFDI = 0,50·(−Z_HU) + 0,50·(−Z_CSA). DFDI maior = mais degeneração |
| Coorte | n = 100; HU_mean 42,9 ± 3,8 (32,5–52,0); CSA 3651,6 ± 662,2 mm² (2390–5060); DFDI 0,00 ± 0,87 |
| Confiabilidade | ICC two-way mixed, absolute agreement, single measure: intra 0,91 (0,84–0,95); inter 0,89 (0,81–0,93), 20 exames |

Observações que importam para replicar:

- O HU médio do artigo é a média de **todos** os pixels da ROI, sem limiar de HU. A gordura intramuscular entra na média, e é exatamente isso que faz o HU cair com a degeneração. **Não** se deve recortar a ROI para −29..150 HU antes de calcular o HU do DFDI, porque isso apagaria o sinal.
- O DP de 0,87 do DFDI publicado implica correlação de aproximadamente 0,51 entre HU e CSA naquela coorte (Var = 0,25 + 0,25 + 2·0,25·r = 0,87²). É dedução nossa, o artigo não informa essa correlação.
- No próprio artigo, a CSA sozinha correlacionou um pouco mais com o CMS (ρ = 0,80) do que o DFDI (ρ = −0,78). Os autores dizem explicitamente que o DFDI não é superior aos componentes.

---

## 2. Requisitos de entrada

### 2.1 TC (NIfTI)

- Valores em **HU** (o nibabel aplica `scl_slope`/`scl_inter` automaticamente). O motor avisa (`tc_pode_nao_estar_em_HU_ar_ausente_ou_offset`) se o mínimo do volume for maior que −500, o que sugere offset de +1024 ou volume recortado sem ar.
- Converter do DICOM com `dcm2niix` mantendo o JSON lateral (`-b y`). O motor copia para a saída os campos que existirem (fabricante, modelo, kernel, espessura, kVp...). O NIfTI sozinho perde esses dados, e eles são essenciais para saber se dá para juntar casos na mesma coorte.
- Ideal: sem contraste, 120 kVp, ~1–1,25 mm, kernel de partes moles. Contraste IV aumenta o HU do músculo; kernel ósseo aumenta o ruído e o DP; kVp diferente muda o HU da gordura e do músculo. O motor avisa se a espessura for diferente de 1,25 mm (`espessura_..._diferente_do_artigo`), mas **não consegue** detectar contraste nem kernel sem o JSON.

### 2.2 Máscara do deltoide (NIfTI)

- **Mesma grade da TC** (mesmo shape e mesmo affine). Se não for, o motor recusa. Com `--resample-mask` ele reamostra por vizinho mais próximo e registra o flag `mascara_reamostrada_para_grade_da_tc`. Prefira exportar a máscara já na grade da TC (3D Slicer: "Export to file" com a TC como referência; ITK-SNAP salva na grade da imagem principal).
- Convenção de labels:
  - padrão: qualquer valor > 0 = deltoide;
  - `--labels 1,2,3`: usa só esses labels (por exemplo 1 = anterior, 2 = médio, 3 = posterior). Se houver mais de um label no corte, o motor devolve também a CSA de cada parte (`csa_mm2_label_N`);
  - `--exclude-label 9`: label que você pinta **por cima** de hematoma, coleção, fragmento ou artefato metálico. Esses voxels saem da ROI (`n_excluidos_label`).
- O motor conta em quantos cortes a máscara existe e decide o fluxo:

| Máscara | O que o motor faz |
|---|---|
| **Um único corte** (você desenhou só a ROI do artigo) | esse corte é o de referência (`corte_origem = mascara_em_corte_unico`). Só métricas 2D. Não dá para reorientar: o corte já tem de ter sido desenhado na imagem reorientada. |
| **3D (deltoide inteiro ou um bloco)** | precisa saber qual é o corte de referência: `--slice-index N`, ou `--auto-slice` com `--humerus` (candidato a confirmar). Sem isso, devolve só métricas 3D e o flag `corte_de_referencia_nao_definido_so_metricas_3d`. Calcula também a média multicorte e o volume. |

- Índice do corte: **0-based**, no eixo de voxel do arquivo mais alinhado com o eixo craniocaudal. No 3D Slicer é o K do IJK mostrado no Data Probe (0-based). Em outros visualizadores, confirme se o índice começa em 0 ou em 1.

### 2.3 Máscara do úmero (opcional)

Necessária só para reorientar (`--reorient`), sugerir o corte (`--auto-slice`) ou medir a inclinação da diáfise. Pode vir do TotalSegmentator (classes `humerus_left`/`humerus_right` da tarefa `total`), de limiar ósseo com edição, ou de segmentação manual. Só precisa estar razoável na diáfise e na cabeça. A precisão fina do contorno não importa para o eixo.

### 2.4 Variante RM

O DFDI do artigo é definido em TC. Em RM, o sinal T1/T2 não tem escala absoluta e **não** substitui o HU. Opções:

- **Dixon / PDFF** (fração de gordura em %): trocar HU_mean por PDFF_mean, com sinal invertido no índice (PDFF alto = mais gordura, logo usar +Z_PDFF). A CSA funciona igual, desde que o corte seja equivalente.
- Os z-scores precisam ser calculados numa coorte de RM. Não se misturam com TC.
- Goutallier/Fuchs em T1 continua sendo escala qualitativa e não entra no índice.
- **Não implementado no motor v0.1.** As faixas de HU (gordura, LAMA, NAMA, limpeza) não valem para RM. Hoje rodar uma RM no motor daria números sem sentido.

---

## 3. Pipeline passo a passo

```
TC.nii.gz + deltoide.nii.gz (+ umero.nii.gz)
   │
   ├─1. carregar (nibabel), checar grade, checar escala HU, ler JSON do dcm2niix
   ├─2. montar máscara: labels escolhidos − label de exclusão
   ├─3. [opcional] eixo da diáfise por PCA + centroides → reorientar (reslice)
   ├─4. escolher o corte de referência (informado | corte único | candidato automático)
   ├─5. limpar a ROI: tirar > 200 HU (osso/metal) e < −200 HU (ar); a gordura fica
   ├─6. métricas do corte (artigo + extras), multicorte, 3D
   ├─7. DFDI: z-scores pela referência (coorte própria ou artigo, aproximação)
   └─8. QC: flags + overlay PNG + montagem dos candidatos ao corte
```

### Passo 1: carregar e checar a geometria

- shape e affine iguais (tolerância de 1e-3) entre TC e máscara;
- eixo craniocaudal = eixo de voxel mais alinhado ao eixo S do mundo; o motor registra a obliquidade da grade (`obliquidade_grade_graus`);
- área do pixel = |a × b| dos dois vetores de voxel no plano (vale também em grades oblíquas); volume do voxel = |det(affine)|.

### Passo 2: máscara

Ver 2.2. A máscara binária final é: (labels do deltoide) menos (label de exclusão).

### Passo 3: reorientação perpendicular à diáfise (opcional, `--reorient --humerus`)

**Por que importa.** Se a diáfise está inclinada θ em relação ao eixo do tomógrafo, o corte axial nativo corta o deltoide obliquamente e a CSA fica inflada por 1/cos θ. O HU quase não muda.

| Inclinação θ | Superestimação da CSA |
|---|---|
| 5° | 0,4% |
| 10° | 1,5% |
| 15° | 3,5% |
| 20° | 6,4% |
| 30° | 15,5% |

Mesmo sem `--reorient`, se você passar `--humerus`, o motor mede θ e emite `diafise_inclinada_Xgraus_CSA_superestimada_~Y%` quando θ > 5°.

**Como o eixo é estimado (automático):**

1. Pontos (mm) de todos os voxels do úmero → PCA → eixo longo aproximado. Esse primeiro eixo sai enviesado pela cabeça.
2. Iteração (3×): usa só a metade distal do comprimento visível (a diáfise), corta lajes de 2 mm perpendiculares ao eixo atual, calcula o centroide de cada laje e ajusta uma reta pelos centroides (SVD).
3. Lajes que tocam a borda do volume são descartadas, porque ali o úmero foi cortado pelo FOV. **Sem esse descarte, o eixo errava 1,2° no fantoma.**
4. Saídas: vetor do eixo, ângulo com o eixo S, comprimento visível, RMS dos centroides. Flags: `umero_visivel_curto_eixo_pouco_confiavel` (< 80 mm), `poucos_centroides_na_diafise`, `diafise_curva_ou_mascara_irregular` (RMS > 2 mm).

**Reamostragem:** nova grade com k = eixo da diáfise (k crescente = cranial), pixel no plano = menor espaçamento da TC, passo entre cortes = espessura original, recortada na caixa deltoide + úmero + 15 mm. A TC usa interpolação linear; a máscara usa interpolação linear com limiar de 0,5 (a área fica mais fiel que no vizinho mais próximo); labels usam vizinho mais próximo. Com `--save-reoriented`, o motor salva TC, deltoide e úmero reorientados para revisão no Slicer.

**Plano escapular:** a rotação **no plano** (deixar o coronal paralelo à escápula) **não muda** a área nem o HU do corte axial, só a apresentação. O motor usa uma orientação fixa e não precisa da escápula para calcular. O código aceita uma direção de referência (`lateral_hint` em `basis_from_axis`) para quem quiser alinhar a imagem para leitura.

**Precisa de confirmação humana:**

- abrir a TC reorientada e conferir se a diáfise está "em pé";
- em **fraturas em 4 partes**, o eixo é calculado na diáfise (fragmento distal), o que é bom, mas a cabeça está deslocada: o corte automático **não** funciona e a escolha tem de ser manual, como no artigo ("closest reproducible reference level");
- diáfise curta no FOV (TC só do ombro): o eixo fica pouco confiável (flag).

**Cuidado: volume parcial ao reamostrar.** Interpolar a TC mistura a borda da ROI com o tecido vizinho. No fantoma inclinado (músculo 50 HU encostado em gordura −100 HU), o HU médio reorientado caiu para **47,7 HU** (viés de −2,3 HU), enquanto o núcleo da ROI erodido em 1 px ficou em **49,96 HU**. Por isso o motor devolve `hu_mean_nucleo_erodido1px`. Recomendações:

1. melhor opção: reorientar **antes** de segmentar e desenhar a ROI já na imagem reorientada, como no artigo; depois medir com `--slice-index` e sem `--reorient`;
2. se a máscara 3D já existe na grade original, reorientar é aceitável, mas **todos** os casos da coorte precisam passar pelo mesmo caminho. Não misture casos reorientados com casos nativos na mesma padronização z;
3. comparar `hu_mean` com `hu_mean_nucleo_erodido1px`: uma diferença grande indica borda contaminada (gordura subcutânea ou osso).

### Passo 4: escolha do corte de referência

Prioridade no motor:

1. `--slice-index N` (você escolheu): `corte_origem = informado_pelo_usuario`;
2. máscara em corte único: esse corte;
3. `--auto-slice --humerus`: **candidato**, com o flag `corte_automatico_requer_confirmacao`;
4. nenhum dos anteriores: sem métricas de corte.

**Heurística do candidato automático (não validada clinicamente):**

- perfil da área da secção do úmero corte a corte, de cranial para caudal;
- ápice da cabeça = primeiro corte com área > 20 mm²;
- janela de 60 mm abaixo do ápice; área máxima da janela ≈ cabeça/tuberosidades no nível do colo anatômico;
- candidato = primeiro corte, de cima para baixo, com área ≥ **0,70 × área máxima** (`--area-fraction`). Fica sempre acima do pico de área e, portanto, acima do colo cirúrgico;
- saída: índice, distância do ápice (mm), razão de área e a figura `*_candidatos_corte.png` com 7 cortes (3 acima, o sugerido, 3 abaixo; úmero em verde, deltoide em vermelho).

**O que a heurística NÃO verifica:** a cortical "circunferencial" da tuberosidade maior, que é o critério do artigo. A máscara do úmero não diz se a tuberosidade aparece como ilha corticada. A fração de 0,70 foi escolhida por geometria (esfera) e **precisa ser calibrada** com os seus casos:

1. nos primeiros 20–30 casos, escolha o corte à mão pelo critério do artigo e rode com `--slice-index N --humerus umero.nii.gz`;
2. o motor devolve `calib_razao_area_umero_no_corte` e `calib_distancia_apice_mm` do corte que você escolheu;
3. use a mediana dessas razões como `--area-fraction` e confira a dispersão. Se o IQR da distância ao ápice for maior que ~2 cortes, a heurística não substitui a escolha manual;
4. mesmo calibrado, o candidato só serve para acelerar. Quem aceita é você, olhando a montagem.

Alternativa mais robusta (futuro): um detector da tuberosidade maior como componente lateral do úmero (direção lateral = vetor do centro do úmero para o centroide do deltoide). Não implementado.

### Passo 5: limpeza da ROI

| Pixel dentro da máscara | Destino | Motivo |
|---|---|---|
| −190 a −30 HU (gordura) | **fica** | é o sinal de infiltração |
| −200 a 200 HU | fica | tecido mole |
| > 200 HU | sai (`n_excluidos_osso_200hu`) | cortical, fragmento, metal, calcificação: o artigo exclui |
| < −200 HU | sai (`n_excluidos_ar`) | ar ou erro de máscara |
| label de exclusão | sai | hematoma, coleção ou fragmento pintado por você |

- Hematoma agudo (~40–80 HU) e líquido (~0–20 HU) **se sobrepõem ao músculo** no HU. Não há limiar que os separe. Só saem com o label de exclusão. Edema difuso fica, como no artigo.
- Os valores sem limpeza também são devolvidos (`csa_mm2_bruto`, `hu_mean_bruto`), que equivalem ao que o MicroDicom daria para a mesma ROI. Com uma ROI bem desenhada, os dois são praticamente iguais.

### Passo 6: métricas

**(a) Réplica do artigo, no corte de referência:**

| Coluna | Definição |
|---|---|
| `csa_mm2` | nº de pixels da ROI limpa × área do pixel |
| `hu_mean` | média do HU de **todos** os pixels da ROI limpa (gordura incluída) |
| `dfdi_coorte` | 0,5·(−Z_HU) + 0,5·(−Z_CSA), com média e DP (amostral) da **sua** coorte |
| `dfdi_artigo_aprox` | o mesmo com média e DP **publicados** (42,9 ± 3,8 HU; 3651,6 ± 662,2 mm²) |

`dfdi_artigo_aprox` é **aproximação**. O artigo padroniza dentro da própria coorte, de um único tomógrafo, com 34% de fraturas e 68% de mulheres. Num tomógrafo ou kernel diferente, um desvio sistemático de poucos HU já desloca o Z_HU (DP de 3,8 HU: 2 HU a mais ou a menos = 0,5 DP). Serve para ter ordem de grandeza ou para validação externa explícita, não para classificar um paciente.

**(b) Extras recomendados:**

| Coluna | Definição | Uso |
|---|---|---|
| `pct_gordura_imat` | % de pixels de −190 a −30 HU | gordura intramuscular "visível" |
| `pct_baixa_atenuacao_lama` | % de −29 a 29 HU | músculo de baixa atenuação (miosteatose) |
| `pct_atenuacao_normal_nama` | % de 30 a 150 HU | músculo de boa qualidade |
| `area_musculo_magro_mm2` | área de −29 a 150 HU | CSA "magra" (sem a gordura) |
| `area_atenuacao_normal_mm2` | área de 30 a 150 HU | CSA de músculo de boa qualidade |
| `hu_mean_musculo_magro` | HU médio só de −29 a 150 | miosteatose sem a gordura macroscópica |
| `hu_median`, `hu_sd`, `hu_p05`, `hu_p95` | distribuição | robustez a outliers; DP alto = ruído/kernel ou heterogeneidade |
| `hu_mean_nucleo_erodido1px` | HU do núcleo erodido em 1 px | controle de volume parcial |
| `csa_mm2_multicorte`, `hu_mean_multicorte`, `csa_cv_pct_multicorte` | média em N ± `--neighbors` cortes (padrão ±2 = 5 cortes, ~6 mm) | robustez à escolha do corte; CV alto = CSA muda rápido nesse nível |
| `vol3d_cm3`, `hu_mean_3d`, `pct_gordura_imat_3d`, `vol_musculo_magro_cm3` | métricas no volume inteiro da máscara | só valem se a máscara cobre o deltoide **inteiro** (origem a inserção); o FOV de TC de ombro costuma cortar a inserção no V deltoideo |
| `csa_mm2_label_N` | CSA por label | anterior/médio/posterior, se segmentados separadamente |

As faixas de −190/−30 e −29/150 vêm da literatura de composição corporal (L3, sarcopenia/miosteatose). No deltoide **não há** pontos de corte validados. Use como contínuas.

Histograma: o overlay PNG mostra o histograma da ROI com as três faixas sombreadas. A rotina `metrics.histogram` devolve os bins de 10 HU, se você quiser guardar.

### Passo 7: DFDI e referência dos z-scores

- **Coorte própria (recomendado):** `dfdi batch` calcula média e DP de `hu_mean` e `csa_mm2` de todos os casos válidos do lote e grava em `referencia_coorte.json`.
- **Referência fixa:** `--cohort-csv arquivo.csv` (colunas `hu_mean`, `csa_mm2`). Use para medir um caso novo contra uma coorte já fechada, sem que ele altere a referência.
- **Pesos:** `--weight-hu 0.5` (artigo). Os pesos de 0,25 a 0,75 da análise de sensibilidade são só exploratórios.
- Por construção, o DFDI da coorte tem média 0. Ele é relativo: "DFDI = +1" quer dizer "pior que a média desta coorte", não um grau absoluto de infiltração.

### Passo 8: controle de qualidade

**Figura por caso** (`*_overlay.png`): TC em janela W400/L40, contorno da ROI em vermelho, gordura em amarelo, pixels excluídos em ciano, histograma e cabeçalho com CSA, HU, % de gordura, DFDI e flags (em vermelho se houver alerta). **Olhar todas as figuras** antes da estatística.

**Flags automáticos** (coluna `flags`, separados por `;`):

| Flag | Gatilho | Ação |
|---|---|---|
| `poucos_pixels` | < 200 px na ROI | máscara errada/corte errado |
| `csa_fora_faixa_plausivel` | fora de 1000–8000 mm² | conferir corte e máscara |
| `hu_fora_faixa_plausivel` | HU médio fora de 0–80 | contraste? offset? ROI na gordura? |
| `muitos_pixels_excluidos_osso_ou_ar` | > 2% da ROI excluída | contorno invadindo osso |
| `mascara_encosta_em_osso` | > 5% do contorno vizinho a > 200 HU | provável inclusão de cortical/acrômio |
| `mascara_toca_borda_do_fov` | ROI toca a borda da imagem | deltoide cortado pelo FOV: CSA subestimada |
| `tc_pode_nao_estar_em_HU...` | mínimo > −500 | conferir conversão |
| `espessura_..._diferente_do_artigo` | espessura ≠ 1,25 ± 0,3 mm | registrar; não misturar sem análise |
| `diafise_inclinada_...` | θ > 5° sem reorientar | reorientar ou aceitar o viés (igual para todos) |
| `reorientado_automaticamente_conferir_eixo` | `--reorient` | conferir o volume reorientado |
| `corte_automatico_requer_confirmacao` | `--auto-slice` | conferir a montagem de candidatos |
| eixo: `umero_visivel_curto...`, `poucos_centroides...`, `diafise_curva...` | ver passo 3 | |

Informativos, sem flag: `n_componentes_conexos` (o deltoide nesse nível costuma ser 1 componente em "C"; partes separadas por label ou por septo podem dar mais), `n_pixels_buracos` (furos na máscara), `pct_contorno_vizinho_osso`.

**Confiabilidade (como no artigo):**

- amostragem sistemática (1 a cada 5) de ≥ 20 exames;
- **intraobservador:** você repete o corte **e** a ROI após ≥ 2 semanas, sem ver a primeira;
- **interobservador:** um segundo leitor (radiologista ou cirurgião) faz o mesmo de forma independente;
- calcular o ICC **por parâmetro** (CSA, HU, DFDI; o artigo só publicou o ICC "global"), modelo two-way, absolute agreement, single measure. Comando: `dfdi icc --csv medidas.csv --cols obs1,obs2` devolve ICC(A,1) e ICC(C,1). O IC 95% fica no `pingouin.intraclass_corr` (ICC2 = A,1) ou no `irr::icc` do R;
- medir separadamente a reprodutibilidade da **escolha do corte** (diferença em mm entre leitores), que costuma ser a maior fonte de variação. Quando houver segmentação automática, comparar também a Dice da ROI.

---

## 4. Resumo: o que é automático e o que precisa de você

| Etapa | Automático? | Confirmação necessária |
|---|---|---|
| Ler NIfTI, checar grade e escala HU | sim | só se houver flag |
| Segmentar o deltoide | não (fora do escopo deste motor; outros agentes estão pesquisando) | sempre revisar a máscara |
| Excluir osso/ar da ROI | sim (> 200 / < −200 HU) | — |
| Excluir hematoma/líquido/fragmento | **não** (sobreposição de HU) | pintar o label de exclusão |
| Eixo da diáfise | sim (PCA + centroides) | conferir visualmente; fraturas |
| Plano escapular | não implementado (não altera as métricas) | — |
| Corte de referência | **candidato** heurístico | **sempre** confirmar; calibrar `--area-fraction` |
| CSA, HU, extras, 3D, multicorte | sim | olhar o overlay |
| Z-scores e DFDI | sim | escolher e declarar a referência |
| Estatística de desfecho | não (plano na seção 6) | — |

---

## 5. Onde entra a radiômica (pyradiomics)

**O DFDI não precisa de radiômica.** São duas grandezas elementares: média de intensidade (estatística de 1ª ordem) e área (forma 2D). Equivalências no pyradiomics, configurado em 2D no corte de referência:

| DFDI | pyradiomics | Configuração para bater com o motor |
|---|---|---|
| `hu_mean` | `original_firstorder_Mean` | sem normalização (`normalize: false`), sem reamostragem; `resegmentRange: [-200, 200]` reproduz a limpeza |
| `csa_mm2` | `original_shape2D_PixelSurface` | `force2D: true`, `force2Ddimension` = eixo do corte; **não** usar `MeshSurface` (área da malha suavizada, um pouco menor) |
| `hu_median`, `hu_sd`, `hu_p05/p95` | `firstorder_Median`, `firstorder_StandardDeviation` (populacional, ddof=0; o motor usa ddof=1), `10Percentile`/`90Percentile` | percentis diferentes dos nossos (5/95) |
| `pct_gordura_imat` | sem equivalente direto | contar no histograma |

**Quando a textura poderia acrescentar algo** (pesquisa, não rotina):

- GLCM/GLRLM/GLSZM descrevem o padrão da infiltração (estrias finas difusas × ilhas grosseiras), coisa que a média de HU não distingue;
- possível uso: prever o desfecho além do DFDI, ou separar edema de gordura em fraturas.

**Cuidados, se for explorar:**

- com n ≈ 100 e ~100 features, o risco de **overfitting** é muito alto. Pré-especificar poucas features, usar validação cruzada aninhada (seleção de features *dentro* das dobras) e validação externa;
- textura depende fortemente de kernel, espessura, mA/ruído e reamostragem. Padronizar a aquisição, reamostrar para pixel isotrópico fixo e usar discretização por **bin width fixo** (p.ex. 25 HU) para TC;
- seguir as definições **IBSI** e declarar todos os parâmetros (arquivo YAML do pyradiomics junto com os dados). O pyradiomics é amplamente compatível com o IBSI, mas tem diferenças documentadas (p.ex. na definição de algumas features de 1ª ordem e na discretização). Conferir a documentação da versão usada;
- reprodutibilidade das features: ICC teste-reteste e entre leitores **antes** de usá-las; descartar features com ICC < 0,75;
- ComBat ou harmonização, se houver mais de um tomógrafo.

O pyradiomics **não** é dependência do motor; dá para rodar à parte, com a mesma máscara.

---

## 6. Plano estatístico para reproduzir e validar na sua coorte

**Desenho:** retrospectivo, RTSA primária, ≥ 50 anos, TC pré-operatória adequada, seguimento ≥ 12 meses. Mesmos critérios de exclusão do artigo (revisão/conversão, infecção prévia, doença neuromuscular, TC inadequada).

**Tamanho:** para detectar ρ ≈ 0,5 com poder de 80% e α = 0,05 bastam ~30 pacientes (z de Fisher). Para a regressão com 4 preditores e validação interna estável, ≥ 80–100.

**Análise (espelhando o artigo):**

1. Descritiva: média ± DP ou mediana [IQR] de HU, CSA, DFDI e escores; distribuição do DFDI (histograma).
2. **Spearman:** DFDI, HU_mean e CSA × CMS, ASES e OSS de 12 meses.
3. **Regressão linear multivariável:** CMS_12m ~ DFDI + idade + sexo + indicação (fratura × degenerativa). Reportar B, β padronizado, IC 95%, p, R² e R² ajustado. Conferir resíduos e VIF.
4. **Validação interna:**
   - bootstrap com 2000 reamostragens e otimismo de Harrell: ajusta no bootstrap, avalia no bootstrap e no original, otimismo = média da diferença, R² corrigido = R² aparente − otimismo;
   - validação cruzada 10-fold repetida 100×: R², RMSE, MAE médios;
   - **importante:** dentro de cada reamostragem/dobra, recalcular os z-scores **só com os dados de treino** (média e DP do treino aplicados ao teste). Calcular o DFDI na coorte inteira antes da CV vaza informação. O artigo não deixa claro como fez isso.
5. **Sensibilidade:** pesos HU:CSA de 25:75, 40:60, 50:50, 60:40 e 75:25; **comparar com a CSA sozinha e o HU sozinho** (no artigo a CSA isolada foi tão boa quanto o DFDI); multicorte × corte único; com e sem fraturas.
6. **Validação externa do artigo:** aplicar `dfdi_artigo_aprox` (média e DP publicados) e comparar com `dfdi_coorte`: correlação, Bland-Altman e deslocamento sistemático do HU entre os tomógrafos. Isso mede o quanto os z-scores do artigo são transportáveis.
7. Opcional: normalizar a CSA por tamanho corporal (altura², diâmetro da cabeça umeral) e incluir IMC. O artigo cita isso como limitação.

**Recalibração obrigatória:** os z-scores dependem da coorte e do tomógrafo. Use um conjunto de referência por tomógrafo/protocolo (ou harmonização), declare qual referência foi usada (`dfdi_referencia`) e **não** aplique "pontos de corte" do DFDI. O próprio artigo não propõe nenhum.

---

## 7. Validação do motor em fantomas sintéticos (resultados reais, 08/11/2026)

`tests/test_measure.py`, 9 testes, todos passando (`.venv/bin/pytest -v -s`). Nenhum dado de paciente.

**Fantoma 1, anel** (pixel 0,75 × 0,75 mm, corte 1,25 mm; anel de raio 25–45 mm, músculo 50 HU; em cada corte, 10% dos pixels a −80 HU (gordura), 5% a 10 HU (LAMA) e 3 pixels a 800 HU (osso, devem ser excluídos)). Corte 20:

| Métrica | Obtido | Esperado pela construção |
|---|---|---|
| CSA limpa (mm²) | 4399,3125 | 4399,3125 (exato) |
| CSA bruta (mm²) | 4401,0000 | 4401,0000 (analítico π(45²−25²) = 4398,23; erro de discretização de 0,06%) |
| HU médio | 35,0019 | 35,0019 (exato) |
| HU médio bruto (com os 3 px de osso) | 35,2952 | 35,2952 |
| % gordura / LAMA / NAMA | 9,9987 / 4,9994 / 85,0019 | idem |
| Área de músculo magro (mm²) | 3959,4375 | 3959,4375 |
| Volume 3D (cm³, 30 cortes) | 164,9742 | 164,9742 |
| DFDI (referência do artigo) | +0,4747 | +0,4747 (calculado à mão) |
| Flags | nenhum | nenhum |

- Com ruído gaussiano de DP 8 HU: HU 34,97 contra 35,00 esperado.
- Máscara em corte único: o corte é detectado sozinho.
- Labels 1/2/3: as CSAs parciais somam a CSA total.
- O label de exclusão remove a região certa.
- Lote de 5 fantomas com gordura de 0 a 30% e área decrescente: DFDI da coorte com média 0, DP(Z_HU) = 1 e DFDI monotonicamente crescente (−1,19; −0,64; −0,11; +0,61; +1,32).

**Fantoma 2, inclinado 20°** (úmero = cilindro + cabeça esférica R 22 mm; deltoide = tubo coaxial com raios de 26–42 mm, 50 HU):

| Métrica | Obtido | Esperado |
|---|---|---|
| Ângulo da diáfise | 19,97° | 20° |
| CSA no axial nativo | 3639,0 mm² | 3637,4 (= verdadeira / cos 20°) |
| Flag | `diafise_inclinada_20graus_CSA_superestimada_~6pct` | — |
| CSA após reorientar (corte automático) | 3417,6 mm² | 3418,1 (verdadeira) |
| HU após reorientar | 47,74 (núcleo erodido: 49,96) | 50 (viés de volume parcial, ver passo 3) |
| Distância ápice → corte automático | 10,0 mm | 9,95 mm (geometria da esfera com fração 0,70) |

- **ICC:** dados clássicos de Shrout & Fleiss (1979), ICC(A,1) = 0,29 e ICC(C,1) = 0,71, como publicado.

Os fantomas verificam **a aritmética e a geometria**. Eles **não** validam a heurística do corte em anatomia real, nem o comportamento com ruído, kernel e volume parcial de uma TC de verdade.

---

## 8. Pendências e limitações conhecidas

1. Heurística do corte automático sem validação em TC real e sem verificar a "cortical circunferencial" da tuberosidade. Calibrar e medir a concordância com a escolha manual (diferença em mm, ICC das métricas resultantes).
2. Variante RM (PDFF) não implementada.
3. Sem detecção automática de contraste IV ou kernel quando falta o JSON do dcm2niix.
4. IC 95% do ICC não implementado (usar pingouin ou R).
5. Plano escapular não implementado (não afeta as métricas, só a apresentação).
6. Volume parcial ao reorientar uma máscara já desenhada: viés de ~2 HU no fantoma. Preferir segmentar na imagem reorientada.
7. As métricas 3D dependem da máscara cobrir o deltoide inteiro; o FOV de ombro costuma cortar a inserção.
8. O motor não faz a regressão nem o bootstrap de desfecho. O plano está na seção 6; o script pode ser feito quando houver a planilha clínica.
