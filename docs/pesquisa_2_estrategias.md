# Estratégias práticas para segmentar o deltoide em TC

Pesquisa feita em novembro de 2026. Objetivo: segmentar o deltoide em TC sem contraste (1,25 mm), no corte axial da grande tuberosidade superior, para o cálculo do DFDI (Rescigno et al., 2026, [Eur J Orthop Surg Traumatol 36:424](https://doi.org/10.1007/s00590-026-05018-z)).

**Legenda:** "Verificado" = conferido em fonte acessível. "Só snippet" = número obtido de resumo de busca, sem acesso ao texto completo (os sites MDPI retornaram HTTP 403). "Não verificado" = não consegui confirmar.

## 1. Pontos-chave

- O protocolo do DFDI usa **um único corte**. Isso muda a estratégia: ferramentas interativas em 2D no corte-alvo costumam ser mais baratas e mais rápidas do que treinar um modelo 3D.
- Não encontrei nenhum modelo público de deltoide em TC com Dice confirmado no texto completo. Há um resultado de 2024 com Dice 0,93 (só snippet), descrito abaixo.
- Não verifiquei se o deltoide está entre as classes do TotalSegmentator. Antes de qualquer decisão, vale checar a lista de classes no repositório oficial.

## 2. Ajuste fino de redes (nnU-Net ou TotalSegmentator)

**Quantos casos?**
- Não há número mínimo oficial. A documentação do nnU-Net diz que a quantidade depende da tarefa ([fonte: nnU-Net, arXiv 1809.10486](https://arxiv.org/pdf/1809.10486); [resumo da documentação](https://gitee.com/RitchieAlpha/nnUNet)). Verificado.
- Uma página de terceiros sugere 20 casos como mínimo e 50+ para bom desempenho. É heurística, não fonte primária. Não verificado.
- Estudo com MedSAM3 e LoRA (pré-print, sem revisão por pares, [arXiv 2608.18731](https://arxiv.org/pdf/2608.18731)): com 10 casos, nnU-Net caiu para Dice 0,39 em pâncreas (TC). Só snippet; um resumo secundário trouxe o mesmo número.
- No TotalSegmentator, o rótulo foi refinado em rodadas de 5, 20 e 100 pacientes ([arXiv 2208.05868](https://arxiv.org/pdf/2208.05868)). Verificado.

**2D ou 3D?**
- No nnU-Net, a configuração 2D pode vencer a 3D em dados pequenos. Isso foi visto em RM cardíaca, não em tarefa de poucos casos ([arXiv 2408.06358](https://arxiv.org/pdf/2408.06358)). Só snippet.
- Para o seu caso, treinar 2D sobre um corte por paciente (ou alguns cortes próximos) é o mais realista. Não encontrei estudo que valide isso para deltoide.

**Transferência a partir do TotalSegmentator:** há estudos que mostram ganho em poucos dados ([VISTA3D, arXiv 2406.05285](https://arxiv.org/pdf/2406.05285)), mas nenhum deles descreve o receituário para incluir uma estrutura nova. Não verificado para deltoide.

**Custo prático no Mac (Apple Silicon):** o nnU-Net é feito para CUDA. Treinar nele num Mac é lento ou impraticável. Não verifiquei o suporte atual a MPS. Se for treinar, o caminho realista é um servidor com GPU. Não verificado.

## 3. Ferramentas interativas no 3D Slicer

**nnInteractive (extensão SlicerNNInteractive).**
- Aceita pontos, caixas, rabiscos e laço. Roda inferência em servidor separado. ([GitHub](https://github.com/coendevente/SlicerNNInteractive); [arXiv 2504.07991](https://arxiv.org/abs/2504.07991)). Verificado nos títulos e resumos; o README atual diz que a extensão é instalada pelo Extension Manager.
- Não encontrei comparação publicada entre nnInteractive e outras ferramentas em músculo. Não verificado.
- **Aplicação direta:** no corte do DFDI, marcar o contorno com laço ou pontos e corrigir manualmente. É o caminho de menor custo para o seu protocolo.

**SegmentWithSAM (SAM e SAM 2).**
- Instala pelo Extension Manager. Propaga máscaras entre cortes ([arXiv 2408.15224](https://arxiv.org/abs/2408.15224v1); [código](https://github.com/mazurowski-lab/SlicerSegmentWithSAM)). Verificado.
- Não encontrei avaliação em músculo. Não verificado.

**MedSAM2 no Slicer.**
- Exige um servidor de backend com GPU. Não é uma instalação simples. Só snippet, com fonte secundária (espelho em Gitee). Não verificado.

**MONAI Label com DeepEdit.**
- Aprendizado ativo: o servidor escolhe os casos mais informativos para rotular primeiro ([arXiv 2203.12362](https://arxiv.org/abs/2203.12362v1); [DeepEdit, arXiv 2305.10655](https://arxiv.org/abs/2305.10655)). Verificado nos resumos.
- Exige servidor e mais infraestrutura do que você precisa para um único corte. Vale como etapa futura, se o estudo crescer.

**TotalSegmentator como ponto de partida.** Use para ossos (úmero, escápula, clavícula) e, se o deltoide estiver nas classes, como máscara inicial. A correção manual continua necessária.

## 4. Métodos clássicos e semiautomáticos

**Faixa de HU.**
- Para músculo esquelético em TC, a faixa mais usada é de -29 a 150 HU ([revisão, PMC8005347](https://pmc.ncbi.nlm.nih.gov/articles/PMC8005347)). Só snippet para a revisão específica.
- Variante: -30 a 150 HU. Para gordura entre músculos (IMAT), usa-se cerca de -190 a -30 HU. Só snippet.
- Limite: a densidade média com faixas estreitas varia entre protocolos de TC. Quantidade (área) é mais robusta que densidade. Só snippet.
- Como o DFDI depende de HU e área, use a faixa apenas para pré-segmentar. A borda final deve ser traçada à mão.

**Âncoras ósseas.** Usar máscaras de úmero e escápula para definir a região de busca reduz o trabalho de correção. Não encontrei estudo que quantifique esse ganho para deltoide. Não verificado.

**Borda subcutânea e fáscia.** O limite externo do deltoide pode vir de uma máscara de gordura subcutânea (faixa de HU de gordura). Não encontrei método publicado com esse nome. Não verificado.

**Atlas e registro.** Possível, mas exige atlas de deltoide já validado. Não encontrei atlas público para TC de ombro. Não verificado.

## 5. Estudos recentes com deltoide e manguito em TC

| Estudo | Método | Resultado | Situação |
|---|---|---|---|
| [JCM 2024, doi:10.3390/jcm13051273](https://doi.org/10.3390/jcm13051273) | Modelo de deltoide em TC | Dice 0,93 ± 0,03 em 20 pacientes adicionais | Só snippet. Não verificado no texto completo (HTTP 403). Detalhes de treino não verificados. |
| [Algorithms 2026, doi:10.3390/a18070432](https://doi.org/10.3390/a18070432) | Framework ML automatizado, deltoide em TC | Validação com cirurgiões: sem diferença significativa com as máscaras corrigidas | Só snippet. Dice não obtido. |
| [Eur Radiol 2020, PMC7755645](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7755645/) | CNN do tipo U-Net, manguito em TC, 103 pacientes | Dice 88 ± 9% (CNN) vs 89 ± 6% (humanos) | Só snippet. Foco em manguito, não deltoide. |
| [PMC12338071 (2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12338071/) | 3D, manguito em TC longitudinal | Dice não obtido | Não verificado (redirecionamento não seguido). |
| Radiology 2023 (RM) | Dois estágios, quatro músculos do manguito | Dice 0,92 ± 0,14 em 30 exames | Só snippet. É RM. |

Conclusão: o único número de deltoide em TC é de 2024, e não consegui ler o artigo. Trate-o como indicação, não como referência.

## 6. Ressonância com Dixon

- Estudo de 2023 (*Br J Radiol*, 26 pacientes com TC e RM): a quantificação de gordura no manguito por histograma de TC teve concordância excelente com Dixon (CCI 0,93 a 0,96). Só snippet. Link do artigo não obtido.
- Concordância entre Goutallier em TC e em RM é apenas moderada. Só snippet.
- Fração de gordura por Dixon tem reprodutibilidade melhor que o grau de Goutallier. Só snippet.
- **Limitação:** não encontrei correlação direta entre fração de gordura por Dixon e o DFDI. Só use RM se você já tiver exames pareados.

## 7. Recomendação ranqueada (Mac com Apple Silicon, usuário único)

1. **Primeiro: semiautomático no corte-alvo com nnInteractive no 3D Slicer.** Use máscaras ósseas do TotalSegmentator como âncora, aplique a faixa de HU para pré-segmentar e corrija à mão. Não exige treino. Valide em 10 a 20 casos contra o seu próprio traçado (Dice e diferença de área média). Esse é o teste que define se o método serve.
2. **Segundo: ajuste fino 2D de nnU-Net** somente se a validação do passo 1 não for consistente e você tiver dezenas de cortes rotulados. Treine num servidor com GPU, não no Mac. Compare com o passo 1 antes de adotar.
3. **Terceiro: MONAI Label com aprendizado ativo** se o estudo crescer para centenas de casos. Antes disso, o custo de infraestrutura não compensa.

Em paralelo: confirme na documentação do TotalSegmentator se o deltoide já está entre as classes. Se estiver, o passo 1 começa de uma máscara inicial e não do zero.

## 8. Lacunas

- Texto completo dos artigos de 2024 e 2026 (bloqueio HTTP 403 na MDPI).
- Lista oficial de classes do TotalSegmentator para deltoide.
- Suporte atual de nnU-Net e nnInteractive a Apple Silicon (MPS). Não verificado.
- Comparação publicada entre ferramentas interativas em músculo.
- Correlação entre DFDI e fração de gordura por Dixon.

Decisões clínicas sobre o que conta como deltoide viável ficam com o cirurgião. Este documento só descreve métodos de medição.
