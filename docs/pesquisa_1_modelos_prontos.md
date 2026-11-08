# Pesquisa 1: modelos prontos e datasets com rótulo de deltoide

Data da pesquisa: 2026-11-08. Objetivo: encontrar modelos, ferramentas e datasets públicos com rótulo de deltoide (ou músculos do ombro) para segmentação em TC e, se possível, RM do ombro.

Legenda: **Sim** = confirmado em fonte; **Não** = confirmado ausente; **Não verificado** = não consegui confirmar nas fontes acessadas.

## Resumo rápido

- Nenhum modelo público testado tem um rótulo de deltoide validado em TC com boa acurácia documentada.
- O único estudo com deltoide em TC validado por cirurgiões de ombro é o grupo de CAOS 2025 (com coautoria do Bruno Gobbato). O modelo não aparece como liberado.
- TotalSegmentator tem tarefas de músculos de coxa e ombro também em RM (`thigh_shoulder_muscles_mr`), com deltoide listado. Não encontrei Dice para esse rótulo.
- Para RM, MRSegmentator e VIBESegmentator são as opções abertas mais citadas, mas não confirmei o rótulo de deltoide em nenhum dos dois.

## Tabela de itens

| # | Item | Modalidade | Rótulo de deltoide | Dice do deltoide reportado | Licença | Viabilidade em Mac (Apple Silicon) |
|---|---|---|---|---|---|---|
| 1 | Estudo CAOS 2025, deltoide em TC (Rajabzadeh-Oghaz, Gobbato et al.) | TC | Sim | Não reportado. Relatado: 97% das máscaras clinicamente aceitáveis; 6% precisaram de correção maior; erro mediano de volume e de gordura <1% | Não informada; código e pesos não citados no resumo | Depende de contato com os autores. Sem modelo público, não há o que rodar |
| 2 | TotalSegmentator, tarefa `thigh_shoulder_muscles` | TC | Sim (lista de rótulos) | Não encontrado | Acadêmica/comercial (paga para uso comercial) | Já testada pelo grupo (segundo o pedido). Rodar em CPU no Mac é possível, mas lento |
| 3 | TotalSegmentator, tarefa `thigh_shoulder_muscles_mr` | RM | Sim (lista de rótulos) | Não encontrado | Acadêmica/comercial | Igual à 2. Não consta que o grupo tenha testado esta versão de RM |
| 4 | MRSegmentator (hhaentze/MRSegmentator) | RM e TC | Não verificado | DSC 0.91 (Dixon in-phase) e 0.85 (T2 TSE) em RM de corpo inteiro. Não há Dice por músculo | Não verificada (checar LICENSE do repositório) | Não verificado. Código em PyTorch; provavelmente roda em CPU ou MPS, sem confirmação |
| 5 | VIBESegmentator (robert-graf/VIBESegmentator) | RM (tronco) | Não verificado. 71 estruturas, incluindo 10 músculos, sem lista | Dice 0.90 ± 0.06 em teste interno com GRE (não é deltoide) | Não verificada; artigo em CC BY 4.0 (não se aplica ao código) | Não verificado |
| 6 | VISTA3D (Project-MONAI/VISTA, NVIDIA) | TC (principal) | Não verificado. 127 classes | Não encontrado | Conflitante: código Apache-2.0; pesos NCLS v1 ou não comercial, dependendo do cartão | Não verificado; requer GPU segundo as descrições |
| 7 | SAT (Segment Anything with Text, zhaoziheng) | TC, RM, PET | Não verificado (497 alvos, sem lista de deltoide confirmada) | Não encontrado | Não especificada no repositório, segundo agregador | Não verificado |
| 8 | nnInteractive (MIC-DKFZ) | TC e RM | Não é modelo de rótulo fixo: segmentação interativa por cliques | Não aplicável | Código Apache-2.0; checkpoint CC BY-NC-SA 4.0 (não comercial) | Não verificado (suporte a MPS não encontrado) |
| 9 | MOOSE (ENHANCE-PET, `moosez`) | PET/TC | Não verificado | Não aplicável | Não verificada | Não recomendado para RM; foco em PET/TC |
| 10 | MedSAM, MedSAM2, SAM-Med3D, BiomedParse | Variável | Não verificado | Não pesquisado | Não verificada | Não verificado |
| 11 | Estudo de 3D U-Net para deltoide e manguito (102 TC, MONAI) | TC | Sim | Dice médio 0.904 para deltoide | Não verificada | Não verificado. Estudo não identificado com precisão |
| 12 | Taghizadeh et al. 2020 (Eur Radiol), manguito rotador | TC | Não (só supraespinal, infraespinal, subescapular e redondo menor) | Não aplicável | Não verificada | Não verificado |
| 13 | Dataset OBPP pediátrico (Conze et al.; Pons et al. 2017) | RM | Sim (deltoide entre 4 músculos do manguito, 24 exames) | Não aplicável | Sem link de download encontrado | Dataset pequeno, pediátrico |
| 14 | TotalSegmentator MRI (dataset no Zenodo) | RM | Não verificado | Não aplicável | Não verificada | Não verificado |
| 15 | ShoulderMRI (Roboflow Universe) | RM | Não verificado | Não aplicável | CC BY 4.0 | Não verificado |

## Observações por item

**1. Estudo CAOS 2025 (deltoide em TC).** Rajabzadeh-Oghaz, Elwell, Boux de Casson, Polakovic, Singh, Raushan, Shetty, Schoch, Aibinder, Gobbato, Roche, Kumar. Modelo de SwinUNETR pré-treinado, ajustado com máscaras manuais do deltoide. O resumo não informa arquitetura detalhada, tamanho do treino nem Dice. Um artigo complementar em MDPI *Algorithms* (18(7):432) descreve 32 pacientes e três cirurgiões. Não consegui acessar o texto completo (HTTP 403). **Não verificado:** número exato de máscaras com correção maior (o resumo do CAOS diz 6%; a versão MDPI descreve 2 de 32).

**2 e 3. TotalSegmentator, tarefas de ombro.** Confirmado pela página do repositório (resumo automático da página, não pelo código): as tarefas `thigh_shoulder_muscles` (TC) e `thigh_shoulder_muscles_mr` (RM) incluem deltoide, supraespinal, infraespinal e subescapular, além de coracobraquial, redondo maior, trapézio, peitoral menor, serrátil anterior e tríceps. Não há "redondo menor" isolado. O grupo já testou a versão de TC (segundo o pedido). **Não verificado:** Dice do deltoide nessas tarefas, e se a versão de RM foi testada.

**4. MRSegmentator.** Modelo aberto para 40 estruturas em RM e TC, com cobertura de ombro a joelho. Os músculos citados são glúteos, autóctones e iliopsoas. **Não verificado:** deltoide na lista de 40 classes.

**5. VIBESegmentator.** Modelo de RM de tronco (NAKO e UK Biobank), publicado em *European Radiology* (out/2025). Os pesos e o código são citados como abertos no GitHub. Ainda assim, o texto diz 10 músculos sem nomeá-los. **Não verificado:** deltoide.

**6. VISTA3D.** Modelo de 127 classes com segmentação automática e interativa. A licença dos pesos é inconsistente entre os cartões do Hugging Face (NCLS v1, NVIDIA Open Model License, e uma licença não comercial acadêmica). Antes de usar, leia o LICENSE do repositório exato.

**7. SAT.** Segmentação guiada por texto para volumes 3D (TC, RM e PET), 497 alvos. Não encontrei confirmação de pesos abertos.

**8. nnInteractive.** Não é um modelo de rótulo fixo: o usuário clica no deltoide e o modelo segmenta. Pode servir para corrigir máscaras automáticas com menos esforço, mas o checkpoint é CC BY-NC-SA 4.0 (uso não comercial). Suporte a Apple Silicon **não verificado**.

**11 e 13.** O estudo de 3D U-Net (102 TC, Dice 0.904 para o deltoide) não foi identificado com precisão. O dataset OBPP tem 24 exames de RM pediátrica com o deltoide entre os músculos anotados, mas não encontrei link de download.

## Lacunas e próximos passos

1. Pedir ao grupo do CAOS 2025 (incluindo a coautoria do Bruno Gobbato) o modelo ou as máscaras de treino, e o texto completo do artigo MDPI.
2. Checar a lista de rótulos de `thigh_shoulder_muscles_mr` na documentação oficial do TotalSegmentator (github.com/wasserth/TotalSegmentator), e se há Dice por músculo no artigo de RM (*Radiology*, 2025).
3. Abrir os LICENSE de MRSegmentator (github.com/hhaentze/MRSegmentator) e VIBESegmentator (github.com/robert-graf/VIBESegmentator) e listar os rótulos de músculos.
4. Verificar se o suporte a MPS (Apple Silicon) do nnU-Net e do nnInteractive funciona na prática.

## URLs consultadas

- TotalSegmentator (repositório, lista de tarefas): https://github.com/wasserth/TotalSegmentator
- Estudo CAOS 2025, deltoide em TC: https://easychair.org/publications/paper/XzjR
- Artigo MDPI *Algorithms* sobre deltoide em TC: https://www.mdpi.com/1999-4893/18/7/432
- TotalSegmentator MRI (arXiv): https://arxiv.org/abs/2405.19492v1
- TotalSegmentator MRI (Radiology, card RSNA): https://atlas.rsna.org/cards/06a25bb5-e2fe-4561-8417-8298cdb236ee
- MRSegmentator (arXiv): https://arxiv.org/html/2405.06463v2
- MRSegmentator (RSNA atlas): https://atlas.rsna.org/cards/569183a1-bfeb-471e-b1d3-d265003a4e62
- MRSegmentator (código): https://github.com/hhaentze/MRSegmentator
- VIBESegmentator (arXiv): https://arxiv.org/abs/2406.00125v4
- VIBESegmentator (código): https://github.com/robert-graf/VIBESegmentator
- VISTA3D (CVPR 2025): https://openaccess.thecvf.com/content/CVPR2025/papers/He_VISTA3D_A_Unified_Segmentation_Foundation_Model_For_3D_Medical_Imaging_CVPR_2025_paper.pdf
- VISTA3D (cartão de licença NV-Segment-CT): https://huggingface.co/nvidia/NV-Segment-CT/blob/main/README.md
- SAT (arXiv): https://arxiv.org/abs/2312.17183v5
- nnInteractive (código): https://github.com/MIC-DKFZ/nnInteractive
- nnInteractive (pesos): https://huggingface.co/MIC-DKFZ/nnInteractive
- MOOSE (PET/TC): https://jnm.snmjournals.org/content/63/12/1941
- Taghizadeh et al. 2020 (manguito, TC): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7755645/
- Dataset OBPP (Conze et al.; referência do estudo de RM): https://arxiv.org/pdf/2203.07846
- Roboflow ShoulderMRI: https://universe.roboflow.com/shouldermri-g3eem/shouldermri-svqvs
- TotalSegmentator MRI dataset (Zenodo): https://zenodo.org/records/11367005

## Não verificado (resumo)

- Deltoide em MRSegmentator, VIBESegmentator, VISTA3D, SAT, MedSAM, SAM-Med3D e BiomedParse.
- Dice do deltoide em todas as ferramentas, exceto na 3D U-Net de 0.904 (estudo não identificado).
- Licenças de código de MRSegmentator, VIBESegmentator e SAT.
- Desempenho em Apple Silicon de todas as ferramentas.
- Conteúdo das tarefas de TotalSegmentator: o texto veio de resumo automático da página, não do código.
