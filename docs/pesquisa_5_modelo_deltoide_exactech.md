# Pesquisa 5: modelo de segmentação do deltoide em TC (Exactech)

Data da pesquisa: 2026-11-08. Escopo: CAOS 2025, Algorithms 2025, J Clin Med 2024 e outros métodos automáticos de deltoide/gordura em TC (2023-2026).

## Resumo

- **CAOS 2025 (EPiC Series in Health Sciences, vol. 8, p. 134-138, DOI 10.29007/tx68, publicado em 5/jan/2026):** validação especialista de um modelo de TC para deltoide. 97% das máscaras foram clinicamente aceitáveis; 6% exigiram correções maiores; erro mediano de volume e infiltração gordurosa abaixo de 1% frente às máscaras corrigidas pelo cirurgião. Análise de não inferioridade com p<0,05.
- **Autores (CAOS 2025):** Rajabzadeh-Oghaz, Elwell, Boux de Casson, Polakovic, Singh, Raushan, Shetty, Schoch, Aibinder, Gobbato, Roche, Kumar. Afiliações completas não estão na página do EasyChair (não verificado).
- **Arquitetura:** ajuste fino (fine-tuning) de SwinUNETR pré-treinado. Confirmado no CAOS (via busca) e no Algorithms.
- **Algorithms 18(7):432 (14/jul/2025, DOI 10.3390/a18070432):** versão estendida. Validação com 3 cirurgiões de ombro em 32 pacientes; 97% aceitáveis; apenas um caso rejeitado.
- **J Clin Med 2024 (DOI 10.3390/jcm13051273):** é o trabalho com Dice 0,93. Treino com 78 pacientes, teste com 20 pacientes, Dice 0,93 ± 0,03, deltoide 3D, volume médio 342,2 ± 113,0 cm³.
- **Definição de gordura (JCM 2024):** voxels de -190 a -30 HU = gordura; -29 a 150 HU = músculo; percentual = voxels de gordura / (gordura + músculo).
- **Código e pesos:** nenhum dos artigos lidos afirma que estão públicos. Não verificado para o CAOS (PDF não extraível).
- **Outros métodos (2023-2026):** não há outro método de deltoide com gordura em TC com Dice publicado que eu tenha encontrado. Os demais estudos cobrem manguito rotador ou músculos do ombro com TotalSegmentator.

## 1. CAOS 2025 (EPiC, DOI 10.29007/tx68)

Fonte: [página EasyChair](https://easychair.org/publications/paper/XzjR), com texto do resumo e metadados. Acesso ao PDF: o link `/publications/paper/XzjR/download` devolveu um PDF binário que não pôde ser extraído pela ferramenta. O arquivo ficou salvo na sessão, sem leitura confirmada do conteúdo.

Verificado no resumo:
- 97% das máscaras clinicamente aceitáveis; 6% com correções maiores.
- Erro mediano de volume e infiltração abaixo de 1% vs. máscaras corrigidas.
- Não inferioridade vs. variação entre cirurgiões, p<0,05.

Não verificado (apenas em snippet de busca, não no texto completo):
- Margem de não inferioridade de Dice de 0,08.
- Número de pacientes no conjunto de validação.

Não encontrado na página: Dice, tamanho do treino, definição de HU, 2D/3D, código/pesos, referências do trabalho anterior.

## 2. Algorithms 2025 (DOI 10.3390/a18070432)

Fonte: [Crossref](https://api.crossref.org/works/10.3390/A18070432) e [página DOI](https://doi.org/10.3390/a18070432).

Verificado:
- Título: "Clinical Validation of a Computed Tomography Image-Based Machine Learning Model for Segmentation and Quantification of Shoulder Muscles". Título e escopo do artigo não coincidem: o estudo valida apenas o deltoide, segundo a busca.
- Afiliações: Rajabzadeh-Oghaz, Elwell, Kumar, Roche (Exactech, Gainesville FL); Schoch e Wessell (Mayo Clinic, Jacksonville FL); Aibinder (University of Michigan); Gobbato (endereço em Jaraguá do Sul, SC, sem nome de instituição).
- Modelo SwinUNETR; 32 pacientes; 97% aceitáveis.

Não acessível: texto completo (MDPI retornou HTTP 403 em todas as tentativas). Dice, tamanho do treino e definição de HU não foram lidos. Um snippet de busca cita um caso rejeitado com Dice 0,75; não verificado no texto.

## 3. J Clin Med 2024 (DOI 10.3390/jcm13051273)

Título: "Impact of Deltoid Computer Tomography Image Data on the Accuracy of Machine Learning Predictions of Clinical Outcomes after Anatomic and Reverse Total Shoulder Arthroplasty". Fonte: [PMC10931952](https://pmc.ncbi.nlm.nih.gov/articles/PMC10931952/).

Verificado:
- Modelo SwinUNETR ajustado (fine-tuning).
- Treino com 78 pacientes (contorno manual por estudantes de medicina supervisionados); teste com 20 pacientes.
- Dice 0,93 ± 0,03.
- Deltoide segmentado em 3D; volume médio 342,2 ± 113,0 cm³.
- Gordura: -190 a -30 HU; músculo: -29 a 150 HU; fração = gordura / (gordura + músculo).
- Afiliações: Exactech (Rajabzadeh-Oghaz, Kumar, Polakovic, Elwell, Roche); UC San Diego (Berry, Singh); Mayo Clinic (Schoch); University of Michigan (Aibinder).
- Coorte de 1057 pacientes (585 mulheres, 469 homens) em aplicação de desfecho (Equinoxe, Exactech).

Não verificado: se código ou pesos estão disponíveis (a página não informa).

Nota: Dice 0,93 vem do JCM. O CAOS 2025 relata validação por especialistas, não Dice head-to-head.

## 4. Outros métodos automáticos (2023-2026)

Verificado nas buscas, sem leitura integral de todos:

- **Skeletal Radiology 2025 (DOI 10.1007/s00256-025-04991-6), Cleveland Clinic** ([PMC12338071](https://pmc.ncbi.nlm.nih.gov/articles/PMC12338071/)): DeepLabV3+ ResNet50 em 2D, métricas em 3D. 53 pacientes TSA (treino/val/teste 32/11/10). Dice 0,928 no pré-operatório (T0) e 0,916 em 2 anos. Gordura: corte único de -29 HU; fração = gordura / (gordura + músculo) x 100%. Apenas manguito rotador (supra, infra/teres minor, subescapular); deltoide não incluído. Código não informado; dados não compartilháveis.
- **JSES International 2026, Kyoto/Kobe** ([PMC13416661](https://pmc.ncbi.nlm.nih.gov/articles/PMC13416661/)): TotalSegmentator sem medida de Dice; 13 pacientes; deltoide 3D com 201,7 ± 66,1 cm³; faixas HU 30-150 / -30-30 / -190 a -30 (Goodpaster). Sem treino próprio.
- **PubMed 40902715 (2025)**: 952 TCs, manguito; HU para gordura 3D. Página não lida (cookie).
- **Rotator cuff, CNN 2020 (PMC7755645)**: Dice médio de 88% (automático) vs. 89% (manual); R² 0,91 para infiltração gordurosa. Manguito, não deltoide.
- **Semi-automático (busca)**: Dice 0,961 ± 0,005 para músculos do ombro incluindo deltoide. Método diferente; não atribuir ao modelo SwinUNETR.
- **CAOS 2022 (busca)**: Dice médio 0,904 para deltoide, 102 TCs de treino. Não lido diretamente.

Autores da série Exactech/Rajabzadeh-Oghaz e Kumar aparecem nos trabalhos acima. Não encontrei outro grupo com método de deltoide e infiltração gordurosa em TC.

## 5. Lacunas e não verificado

- Texto completo do CAOS 2025 não extraído (PDF binário).
- Texto completo do Algorithms 2025 não acessível (HTTP 403 no MDPI e PMC indisponível).
- Não encontrei o "trabalho recente" citado no CAOS com números de acurácia.
- Código e pesos: não informados em nenhum artigo lido.
- Dice do modelo final do Algorithms: não verificado.
- Afiliação completa do CAOS 2025: não verificada.
