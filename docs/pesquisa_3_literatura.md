# Pesquisa 3: literatura sobre medição do deltóide antes de artroplastia reversa

Data: 2026-11-08. Escopo: como outros grupos mediram qualidade e quantidade do deltóide (TC e RM), se há segmentação automática, radiômica e limiares de HU/Dixon.

**Legenda de verificação:** [LIDO] = conteúdo conferido no texto ou página do artigo. [SNIPPET] = visto só no resumo de busca, não aberto. [NÃO ENCONTRADO] = não localizado; não há DOI informado.

## Pontos principais

- **Rescigno et al. 2026 (DFDI) não foi localizado** na busca. A definição do índice e os cortes não foram verificados.
- Os estudos sobre deltóide são pequenos (n = 25 a 75), a maioria retrospectiva e de centro único.
- **Não encontrei nenhum estudo de segmentação automática do deltóide com código público.** Há modelos de manguito rotador em TC e RM, com Dice de 0,86 a 0,93.
- O limiar padrão de HU é músculo -29 a 150 e gordura intermuscular -190 a -30 (Amini 2019 [LIDO]). Não há limiar validado específico para o deltóide.
- Dixon não foi viável em um estudo de RM pós-RTSA por artefato metálico (Bogner 2025 [LIDO]).

## 1. Medição do deltóide em TC/RM antes ou após RTSA

**Wiater BP et al. 2015. Clin Orthop Relat Res 473(2):663-673. DOI 10.1007/s11999-014-4047-2 [LIDO]**
- RM, n = 30 de 222 pacientes com RTSA (subconjunto com RM pré-op). Área transversal (CSA) do deltóide em RM axial DP, somada nas três porções. Gordura por Fuchs 5 pontos e fração de gordura por limiar adaptativo em MATLAB.
- Achado: tamanho do deltóide correlacionou com Constant (rho 0,432; p = 0,017). Fração de gordura do deltóide correlacionou com ASES pós-op (rho -0,401; p = 0,047). Estudo preliminar, sem correção para múltiplas comparações.

**Yoon JP et al. 2017. PLoS ONE 12(3):e0174361. DOI 10.1371/journal.pone.0174361 [SNIPPET]**
- n = 35, RTSA por artropatia do manguito ou lesão irreparável. Volume 3D do deltóide com software de imagem e código próprio. Modalidade: RM segundo o resumo de busca; não confirmei no texto.
- Achado: volume ajustado por IMC associado ao Constant (p = 0,009); preditor independente em análise multivariada (p = 0,011).

**Bogner B, ... Jung M. 2025. Eur Radiol 36(1):484-495. DOI 10.1007/s00330-025-11836-2 [LIDO]**
- RM 1,5 T, n = 25 (18 mulheres, mediana 75 anos), um ano após RTSA. T2 axial com redução de artefato metálico. Fração de gordura areal (semiquantitativa) por contorno manual e crescimento de região. Dixon não foi viável por artefato. CSA normalizada pela altura.
- Achado: gordura anterior do deltóide vs. Constant rho = -0,79 (p < 0,001). CSA anterior normalizada vs. Constant rho = 0,55. Estudo transversal, sem dados pré-op.

**Lee HJ. 2025. Spartan Med Res J 10(2):29. DOI 10.51894/001c.143951 [LIDO]**
- TC, n = 75, retrospectivo, autor único. Segmentação manual por residentes/estudantes; software não informado. Radiômica descrita só como "features de forma e intensidade", sem nomes.
- Achado: volume médio do deltóide 293 ± 106 cm³; queda de 1,6% ao ano de idade. Correlação volume TC vs. espessura por ultrassom r = 0,45 (o autor considera o US fraco).

**Estudo de TC com deltóide (grupo do Exactech Equinoxe; MDPI, Journal of Clinical Medicine 13(5):1273) [NÃO VERIFICADO]**
- Página retornou erro 403. Pelo snippet: segmentação do deltóide em TC pré-op, coorte multicêntrica, volume normalizado e infiltração gordurosa associados a desfecho. DOI não confirmado.

**Outros, só por snippet [SNIPPET]:**
- Estudo de TC com CSA antes e 1 ano após RTSA com enxerto glenoide, n = 25 (Semin Arthroplasty 2023).
- TC de 99 pacientes, com e sem revisão, incluindo qualidade do deltóide (Skeletal Radiol 2025, DOI não confirmado).
- Resumo AAOS 2025 com 3D do deltóide em 960 pacientes (um snippet cita 1.057 em outra coorte; número a conferir).
- Fratura proximal do úmero: TC de 100 pacientes com Goutallier em três porções do deltóide; gordura grave na porção posterior em 26% (PubMed 29103059).
- Revisão e metanálise "Sarcopenia of the deltoid as an indicator of outcome following RTSA" (JSES Int, 2025; PMC12490665). Não consegui abrir o texto (redirecionamento não seguido); não sei o número de estudos.

**Não localizados:**
- **Rescigno 2026 (DFDI)**: nenhum registro encontrado na busca.
- **Knazek 2026**: nenhum artigo encontrado.
- **Allen 2026 (revisão sistemática)**: não encontrado. A revisão de 2025 acima é a mais próxima.
- **O'Dwyer 2025 (metanálise)**: não encontrado.
- **Greiner 2010**: não encontrado.
- **Henninger 2020 (CSA vs. volume)**: o mais próximo é um estudo de 2019 em cadáver com RM (Henninger, Christensen, Chalmers, Tashjian), que não trata de artroplastia. DOI não verificado.

## 2. Segmentação automática por deep learning

**Taghizadeh E, Büchler P. 2020. Eur Radiol 31(1):181-190. DOI 10.1007/s00330-020-07070-7 [LIDO]**
- TC, 103 exames de 95 pacientes com artrose glenoumeral. Modelo CNN para os quatro manguitos (não deltóide).
- Dice: 88 ± 9% (CNN) vs. 89 ± 6% (humanos). Por músculo: supraespinal 0,91; subescapular 0,91; infraespinal 0,89; redondo menor 0,86. Tempo < 1 s por caso.
- Código e pesos: não informados.

**Yang et al. (Li X, Cleveland Clinic). 2025. Skeletal Radiol 55(1):131-141. DOI 10.1007/s00256-025-04991-6 [LIDO]**
- TC longitudinal de TSA; 53 pacientes para treino/teste (32/11/10); 172 para quantificação. DeepLabV3+ com ResNet50, 2D.
- Dice do músculo: 0,928 (pré-op) e 0,916 (2 anos). Sem Dice para gordura, que foi calculada por limiar de HU entre -190 e -29.
- Músculos: supraespinal, infraespinal + redondo menor, subescapular. **Deltóide não incluído.**
- Código: não disponível; dados não compartilháveis (PHI). Sem validação externa.

**Deltóide em TC com SwinUNETR (Rajabzadeh-Oghaz et al.) [SNIPPET]**
- Ajuste fino de SwinUNETR com 97 máscaras manuais; validação com cirurgiões sem diferença significativa nas medidas. Dice e DOI não encontrados.

**Outros, só por snippet [SNIPPET]:**
- Diagnostics 2023: nnU-Net em RM multicêntrica para úmero, escápula e manguito, com verificação de erro de segmentação (DOI não confirmado).
- Acta Radiol 2024: Dice 0,920 em validação externa de 20 RMs; diferença de volume muscular 4,58%.
- RM pediátrica (paralisia do plexo braquial), n = 24 ombros: Dice do deltóide 82,4%; infraespinal 82,0%; supraespinal 71,0%; subescapular 82,8%.
- Sci Rep 2021 (supraespinal em RM, rede convolucional + Otsu): correlação com ocupação ratio rho = -0,75.
- TotalSegmentator em validação de 2026 (resumo, câncer de mama): infraespinal e supraespinal com Dice ~0,98. Não sei se o deltóide está na lista de classes; a verificar.
- Nenhum código público de deltóide encontrado na busca.

## 3. Radiômica do deltóide e do manguito

- Única publicação revisada com radiômica do deltóide: **Lee 2025** (seção 1). Features não nomeadas, sem validação de desfecho.
- Snippet de resumo estudantil (Henry Ford, 26 TC): volume médio ~293 cm³; ultrassom vs. TC r = 0,52. Não verificado.
- Radiology AI 2023: segmentação 3D dos quatro manguitos com fração de gordura separada do volume (rho 0,53 com Goutallier) [SNIPPET].

## 4. Limiares de HU para músculo e gordura

**Amini B, Boyle SP, Boutin RD, Lenchik L. 2019. J Gerontol A Biol Sci Med Sci 74(10):1671-1678. DOI 10.1093/gerona/glz034 [LIDO]**
- Revisão sistemática de 388 estudos de TC (330 de massa muscular; 125 de mioesteatose).
- Músculo: faixa de -49 a 200 HU; mais comum -29 a 150 HU. IMAT: mais comum -190 a -30 HU (outros: -200 a -1 HU). Tecido de baixa densidade: 0-34 HU e 0-30 HU.
- Conclusão: "considerável variação" entre métodos; pede consenso para TC.

**Outros limiares [SNIPPET]:**
- Corte por sexo em L3: cerca de 34 HU (mulheres) e 38 HU (homens) (PMC10841085).
- Tórax: 37,42 HU (homens) e 33,17 HU (mulheres) (PMC8572237).
- Um estudo aponta que não há limiar validado para músculo individual; valores de corpo inteiro são usados por empréstimo (PMC7359407).

**Nota:** não encontrei limiar de HU publicado para deltóide. Os limiares acima são de corte transversal em L3, T12 ou tórax, não de ombro.

## 5. Fração de gordura por RM (Dixon) no ombro

- **Bogner 2025 [LIDO]:** Dixon não foi viável por artefato metálico em RTSA. Usou T2 com redução de artefato e fração de gordura areal.
- **Wiater 2015 [LIDO]:** fração de gordura por limiar adaptativo em T1, não Dixon.
- **Volume e gordura Dixon em voluntários saudáveis (20-60 anos), manguito e deltóide [SNIPPET]:** sem DOI; deltóide com menor fração de gordura no braço dominante.
- **Dixon no supraespinal [SNIPPET]:** fração de gordura correlacionou negativamente com flexão, abdução e força; reprodutibilidade melhor que Goutallier.
- Fórmula padrão (confirmado em snippet): fração de gordura = sinal de gordura / (sinal de gordura + sinal de água).

## 6. Lacunas e próximos passos

1. Pedir ao usuário o DOI ou PDF do Rescigno 2026 para confirmar definição, cortes e se o DFDI usa TC e a fatia no tubérculo maior superior.
2. Se o DOI do Knazek 2026, Allen 2026 ou O'Dwyer 2025 existir, enviar que eu busco de novo.
3. Abrir o texto da metanálise PMC12490665 e o artigo MDPI 13(5):1273 (bloqueados nesta sessão).
4. Verificar se o TotalSegmentator tem classe de deltóide (ferramenta com código público, testável em TC de ombro).
5. Nenhum modelo público de deltóide foi encontrado: a segmentação automática teria de ser treinada do zero ou adaptada.
